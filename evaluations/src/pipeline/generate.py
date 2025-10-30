import os, subprocess, json
import random
from typing import List, Dict, Optional, Callable

from typing import Optional

def read_seed(seed_text: Optional[str] = None, seed_file: Optional[str] = None) -> str:
    """Read and combine seed content from a text string and/or file."""
    parts = []

    if seed_file is not None:
        try:
            with open(seed_file, "r") as f:
                parts.append(f.read().strip())
        except FileNotFoundError:
            raise FileNotFoundError(f"Seed file not found: {seed_file}")

    if seed_text is not None:
        parts.append(seed_text.strip())

    if not parts:
        raise ValueError("Need at least one of seed_text or seed_file")

    return "\n\n".join(parts)


def prompt_user(seed: str, prev_turns: List[Dict[str, str]], verbose=False) -> str:
    """Ask the model to act as the USER and produce the next user message."""
    parts = []
    parts.append("You are a USER seeking help from an agent.")
    parts.append("Base data:")
    parts.append(seed.strip())
    if prev_turns:
        parts.append("\nConversation so far (oldest to newest):")
        for i, t in enumerate(prev_turns, 1):
            role = t["role"]
            text = t["text"].strip()
            parts.append(f"[{i}] {role.upper()}: {text}")
    parts.append(
        "\nAct as the USER. Produce exactly ONE user message that logically continues the conversation, "
        "refers to existing info when helpful, and can be answered by an agent."
        "\nUSER:"
    )
    prompt = "\n".join(parts)
    if verbose: print(f"=====\n{prompt}\n=====\n\n")
    return prompt


def prompt_agent(seed: str, prev_turns: List[Dict[str, str]], user_msg: str, verbose=False) -> str:
    """Ask the model to act as the AGENT and respond to the just-produced user_msg."""
    parts = []
    parts.append("You are an agent providing help to a user.")
    parts.append("Base data:")
    parts.append(seed.strip())
    if prev_turns:
        parts.append("\nConversation so far (oldest to newest):")
        for i, t in enumerate(prev_turns, 1):
            role = t["role"]
            text = t["text"].strip()
            parts.append(f"[{i}] {role.upper()}: {text}")
    # include the new user message we just got
    parts.append(f"[{len(prev_turns)+1}] USER: {user_msg.strip()}")
    parts.append(
        "\nAct as the AGENT. Produce exactly ONE helpful, specific reply to the user."
        "\nAGENT:"
    )
    prompt = "\n".join(parts)
    if verbose: print(f"=====\n{prompt}\n=====\n\n")
    return prompt

def build_phase2_context(
    history: List[Dict[str, str]],
    bwor: int,
    min_tail: int = 2,
) -> List[Dict[str, str]]:
    """
    history: list of dicts {"role": "user"|"agent", "text": "..."}
    Always include the last `min_tail` turns (if available),
    then, if we still need more (bwor > min_tail), sample from older ones.
    """
    n = len(history)
    if n == 0: return []

    tail_start = max(0, n - min_tail)
    ua_tail = history[tail_start:]

    n_ua_samples = bwor - len(ua_tail)
    if n_ua_samples <= 0: return ua_tail

    # sample from anything before tail
    n_ua_samples = min(n_ua_samples, tail_start)
    idxs = sorted(random.sample(range(tail_start), n_ua_samples))
    ua_sampled = [history[i] for i in idxs]

    return ua_sampled + ua_tail


def run_procedural_generation(
    seed_text: Optional[str] = None,
    seed_file: Optional[str] = None,
    bwor: int = 4,            # PHASE 1 size and also phase-2 bootstrap width
    total_pairs: int = 8,    # number of (user, agent) pairs to produce TOTAL
    call_llm: Optional[Callable[[str], str]] = None,
):
    """
    Phase 1:
        generate exactly `bwor` pairs.
        For pair j, both user and agent see ALL previous turns (full context).
    Phase 2:
        generate 1 pair at a time until `total_pairs` reached:
        - build bootstrapped context (last 2 + sample older up to `bwor`)
        - prompt user
        - prompt agent with that same context + user
    """
    assert call_llm is not None, "Need LLM caller"
    seed = read_seed(seed_text, seed_file)

    history: List[Dict[str, str]] = []

    # PHASE 1: full-context pairs
    pairs = 0
    while pairs < bwor:
        # user turn
        u_prompt = prompt_user(seed, history, True)
        u_text = call_llm(u_prompt).strip()
        history.append({"role": "user", "text": u_text})

        # agent turn (sees full history + this user), dont double user input so [:-1]
        a_prompt = prompt_agent(seed, history[:-1], u_text)
        a_text = call_llm(a_prompt).strip()
        history.append({"role": "agent", "text": a_text})

        pairs += 1

    # PHASE 2: one bootstrapped pair at a time
    while pairs < total_pairs:
        ctx = build_phase2_context(history, bwor=bwor, min_tail=2)

        # user
        u_prompt = prompt_user(seed, ctx)
        u_text = call_llm(u_prompt).strip()
        history.append({"role": "user", "text": u_text})

        # agent (use same ctx + this user)
        agent_ctx = ctx + [{"role": "user", "text": u_text}]
        a_prompt = prompt_agent(seed, agent_ctx, u_text)
        a_text = call_llm(a_prompt).strip()
        history.append({"role": "agent", "text": a_text})

        pairs += 1

    return history

def ollama_call_model(prompt: str, model: str = "llama3.2") -> str:
    """Run LLM and return generated text."""
    result = subprocess.run(
        ["ollama", "run", "--verbose", model],
        input=prompt.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    out = result.stdout.decode("utf-8")
    # split metadata lines
    lines = out.splitlines()
    text_lines = [ln for ln in lines if not ln.lstrip().startswith(">")]
    return "\n".join(text_lines).strip()

if __name__ == "__main__":
    random.seed(42)

    eval_root = os.path.dirname(os.path.abspath(__file__))
    seed_file = os.path.join(eval_root, "../../data_ref", "student_scores.csv")

    history = run_procedural_generation(
        seed_file=seed_file,
        call_llm=ollama_call_model,
    )

    # pretty print
    for i, turn in enumerate(history, 1):
        print(f"==========\n[{i:02d} {turn['role'].upper()}]: {turn['text']}\n")

    pairs = []
    tmp = []
    for t in history:
        tmp.append(t)
        if len(tmp) == 2:
            pairs.append(tmp)
            tmp = []

    ui_path = os.path.join(eval_root, "idk", "ui.json")
    os.makedirs(os.path.dirname(ui_path), exist_ok=True)
    ui = {
        i: {
            "user": pair[0]["text"],
            "agent": pair[1]["text"],
        }
        for i, pair in enumerate(pairs)
    }
    with open(ui_path, "w", encoding="utf-8") as f:
        json.dump(ui, f, indent=2, ensure_ascii=False)