import os, subprocess, json, shutil
import random
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable

@dataclass
class Turn:
    """single conversation turn; user message & agent reply"""
    user: str
    agent: Optional[str] = None

History = List[Turn]

def print_sep(text):
    width = shutil.get_terminal_size((80, 20)).columns
    line = "=" * width
    print(f"{line}\n{text}\n{line}\n")

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


def render_history(history: History) -> str:
    """convert a list of {"role": "...", "text": "..."} into a single history block for prompts"""
    if not history:
        return ""
    lines = ["\nConversation so far (oldest to newest):"]
    for i, t in enumerate(history, 1):
        lines.append(f"[{i}] USER: {t.user.strip()}")
        if t.agent is not None and t.agent.strip():
            lines.append(f"[{i}] AGENT: {t.agent.strip()}")
    return "\n".join(lines)

def prompt_user(seed: str, history_text: str, seed_file=False, verbose=False) -> str:
    """On the very first turn (no history), instruct the USER to send the base data to the agent."""
    first_turn = (not history_text)
    parts = [
        "You are a USER seeking help from an agent.",
        "You will be given base data and the conversation so far (if any).\nBase data:",
        seed.strip(),
    ] if seed_file else [
        "You are a USER seeking help from an agent.",
        "You will be given the conversation so far (if any).",
        seed.strip(),
    ]
    
    if history_text: parts.append(history_text)

    if first_turn:
        parts.append(
            "\nThis is the FIRST user turn. Produce exactly ONE user message that:\n"
            "1) Briefly greets the agent and states what you want them to do, and\n"
            "2) Includes the BASE DATA verbatim so the agent can access it.\n"
            "Do not add any other context blocks besides your single message.\n"
            "USER:"
        ) if seed_file else parts.append(
            "\nThis is the FIRST user turn. Produce exactly ONE user message that:\n"
            "1) Briefly greets the agent and states what you want them to do.\n"
            "Do not add any other context blocks besides your single message.\n"
            "USER:"
        )
    else:
        parts.append(
            "\nAct as the USER. Produce exactly ONE user message that logically continues the conversation, "
            "refers to existing info when helpful, and can be answered by the agent."
            "\nUSER:"
        )

    prompt = "\n".join(parts)
    if verbose:
        print_sep(prompt)
    return prompt

def prompt_agent(seed: str, history_text_with_user: str, verbose=False) -> str:
    parts = [
        "You are an AGENT providing help to a user.",
    ]
    if history_text_with_user:
        parts.append(history_text_with_user)

    parts.append(
        "\nAct as the AGENT. Produce exactly ONE helpful, specific reply to the user. "
        "Do NOT repeat the user's message."
        "\nAGENT:"
    )
    prompt = "\n".join(parts)
    if verbose:
        print_sep(prompt)
    return prompt


def build_phase2_context(
    history: History,
    bwor: int,
    min_tail: int = 2,
    # TODO: min head, for data
) -> History:
    """
    history: list of dicts {"role": "user"|"agent", "text": "..."}
    Always include the last `min_tail` turns (if available),
    then, if we still need more (bwor > min_tail), sample from older ones.
    """
    n = len(history)
    if n == 0: return []

    tail_start = max(0, n - min_tail)
    ua_tail: History = history[tail_start:]

    n_ua_samples = bwor - len(ua_tail)
    if n_ua_samples <= 0: return ua_tail

    # sample from anything before tail
    n_ua_samples = min(n_ua_samples, tail_start)
    idxs = sorted(random.sample(range(tail_start), n_ua_samples))
    ua_sampled: History = [history[i] for i in idxs]

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

    history: History = []

    pairs = 0
    while pairs < bwor:
        base_hist_str = render_history(history)

        # USER turn (gets seed)
        u_prompt = prompt_user(seed, base_hist_str, seed_file, verbose=True)
        u_text = call_llm(u_prompt).strip()
        history.append(Turn(user=u_text))  # pending agent

        # AGENT turn: sees ONLY conversation + the new user message
        hist_with_user = render_history(history)
        a_prompt = prompt_agent("", hist_with_user, verbose=True)
        a_text = call_llm(a_prompt).strip()
        history[-1].agent = a_text

        pairs += 1

    # PHASE 2: one bootstrapped pair at a time (seed still ONLY to USER)
    while pairs < total_pairs:
        ctx: History = build_phase2_context(history, bwor=bwor, min_tail=2)
        base_hist_str = render_history(ctx)

        # USER
        u_prompt = prompt_user(seed, base_hist_str, seed_file, verbose=False)
        u_text = call_llm(u_prompt).strip()
        history.append(Turn(user=u_text))  # pending agent

        # AGENT: same context + newly added user; NO seed
        hist_with_user = render_history(ctx + [Turn(user=u_text)])
        a_prompt = prompt_agent("", hist_with_user, verbose=False)
        a_text = call_llm(a_prompt).strip()
        history[-1].agent = a_text

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

    eval_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # TODO: accept input for these
    # seed_file = os.path.join(eval_root, "data", "student_scores.csv")
    # SEED_TEXT = "You are a teacher with this information about your students."
    seed_file = None
    SEED_TEXT = "You are a student asking an AI tutor for short explanations about technical topics.  Keep each question concise and specific."

    history = run_procedural_generation(
        seed_text=SEED_TEXT,
        seed_file=seed_file,
        bwor=4,
        total_pairs=4,
        call_llm=ollama_call_model,
    )

    # pretty print
    WIDTH = 30
    B = "#"
    for i, turn in enumerate(history, 1):
        title = f" {i:02d} TURN "
        pad = WIDTH - len(title)
        side = max(pad, 0) // 2
        header = B * side + title + B * (pad - side)

        print(B * WIDTH)
        print(header)
        print(B * WIDTH)
        print(f"USER:\n{turn.user}\n")
        print(f"AGENT:\n{turn.agent or ''}\n")

    pairs = []
    tmp = []
    for t in history:
        tmp.append(t)
        if len(tmp) == 2:
            pairs.append(tmp)
            tmp = []

    ui_path = os.path.join(eval_root, "idk", "ui.json")
    os.makedirs(os.path.dirname(ui_path), exist_ok=True)
    ui: Dict[int, Dict[str, str]] = {
        i: {"user": t.user, "agent": t.agent or ""}
        for i, t in enumerate(history)
    }
    with open(ui_path, "w", encoding="utf-8") as f:
        json.dump(ui, f, indent=2, ensure_ascii=False)