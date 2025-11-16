import os, subprocess, json, shutil
import random
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta, timezone
import time

@dataclass
class Turn:
    """single conversation turn; user message & agent reply"""
    user: str
    agent: Optional[str] = None
    agent_reasoning: Optional[str] = None
    timestamp_user: datetime = None
    timestamp_agent: Optional[datetime] = None

History = List[Turn]

CONTEXT_MSGS_LEN = 10
TOTAL_MSGS_LEN = 20

PR_FACT = 0.4
PR_LONG_JUMP = 0.3
TEMPORAL_REASONING = True

def now_est() -> datetime:
    return datetime.now(tz=timezone(timedelta(hours=-5))).replace(microsecond=0)

def fmt_ts(dt: datetime) -> str:
    """readable ISO-8601 with offset; 2025-10-24T01:23:45-05:00"""
    return dt.isoformat()

def _few_mins_dl() -> timedelta:
    return timedelta(minutes=random.randint(1, 5), seconds=random.randint(0, 59))

def _long_jump_dl() -> timedelta:
    # pick one of: hours, days, weeks, months (approx via 30d)
    choice = random.choice(["hours", "days", "weeks", "months"])
    if choice == "hours":
        return timedelta(hours=random.randint(2, 12), seconds=random.randint(0, 59))
    if choice == "days":
        return timedelta(days=random.randint(1, 6), seconds=random.randint(0, 59))
    if choice == "weeks":
        return timedelta(weeks=random.randint(1, 4), seconds=random.randint(0, 59))
    # months ~ 30d chunks
    return timedelta(days=30 * random.randint(1, 3), seconds=random.randint(0, 59))

def next_user_time(prev_user_time: datetime, temporal_reasoning: bool = False) -> datetime:
    """Advance the 'user' clock. Normally a few minutes. If temporal_reasoning, occasionally jump a longer interval."""
    if not temporal_reasoning:
        return prev_user_time + _few_mins_dl()
    if random.random() < PR_LONG_JUMP:
        return prev_user_time + _long_jump_dl()
    return prev_user_time + _few_mins_dl()

def agent_reply_time(user_time: datetime) -> datetime:
    return user_time + timedelta(seconds=random.randint(1, 59))

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
    """Convert a list of Turns into a single history block for prompts (with timestamps)."""
    if not history:
        return ""
    lines = ["\nConversation so far (oldest to newest):"]
    for i, t in enumerate(history, 1):
        ut = t.timestamp_user or now_est()
        lines.append(f"[{i}] USER @ {fmt_ts(ut)}:\n{t.user.strip()}\n\n")

        if t.agent is not None and t.agent.strip():
            at = t.timestamp_agent or ut
            lines.append(f"[{i}] AGENT @ {fmt_ts(at)}:\n{t.agent.strip()}\n\n")
    return "\n".join(lines)

USER_GUIDE = """
Write ONE user message only.
Hard rules:
- Do NOT reference any kind of material unless it appears verbatim in prior conversation.
- You MAY invent some numeric values if necessary.
"""

def prompt_user(seed: str, history_text: str, seed_file=False, verbose=False, temporal_reasoning=False) -> str:
    first_turn = (not history_text)
    parts = (
        [
            "You are the USER in a dialogue with an AI agent."
            "You will be given base data and the conversation so far (if any).\nBase data:",
            seed.strip(),
            USER_GUIDE
        ]
        if seed_file else
        [
            "You are the USER in a dialogue with an AI agent."
            "You will be given the conversation so far (if any).",
            seed.strip(),
            USER_GUIDE
        ]
    )
    if history_text:
        parts.append(history_text)

    if first_turn:
        parts.append("FIRST TURN: Produce ONE message to start the conversation and set a context.\nUSER:")
    else:
        extra_temporal_note = (
            "\nAlso mention a specific real-time event (e.g., \"Just now, I did X\", but use more varied word choice)."
            if random.random() < PR_FACT else ""
        )
        parts.append(
            "\nNow, act as the USER. Produce exactly ONE user message that logically continues the conversation, "
            "refers to existing info when helpful, and can be answered by the agent."
            f"{extra_temporal_note}\nUSER:"
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
        "\nNow, act as the AGENT. Produce exactly ONE helpful, specific reply to the user. "
        "Do NOT repeat the user's message.  Do not fabricate data."
        "\nAGENT:"
    )
    prompt = "\n".join(parts)
    if verbose:
        print_sep(prompt)
    return prompt


REASONER_VALID = """
Write ≤80 words. One concise paragraph.
Do NOT include phrases like "The agent made this reply because", "This reasoning", or "Based on".
Start immediately with the substantive explanation of how the reply addresses the user's message.
Focus on the key reasoning steps, decisions, or assumptions only.
No preamble, no quotes, no meta-commentary.  Output only the reasoning text.
"""

def prompt_agent_reasoning(history_text_with_user: str, agent_reply: str, verbose=False) -> str:
    parts = [
        REASONER_VALID,
        "\nConversation context (with indices):\n",
        history_text_with_user,
        "\nAgent reply to justify:\n",
        agent_reply,
        "\nReasoning (why this reply fits the user's inputs):"
    ]
    prompt = "\n".join(parts)
    if verbose:
        print_sep(prompt)
    return prompt

def ask_review(kind: str, text: str) -> str:
    """
    Show a generated artifact and ask for action.
    """
    print_sep(f"{kind} — REVIEW")
    print(text.strip(), "\n")
    while True:
        choice = input("[Enter]=accept  (r)egen  (e)dit-prompt  (q)uit > ").strip().lower()
        if choice == "":
            return "accept"
        if choice in {"r", "regen"}:
            return "regen"
        if choice in {"e", "edit"}:
            return "edit"
        if choice in {"q", "quit"}:
            return "quit"
        print("Please choose: Enter / r / e / q")

def gen_with_review(
    label: str,
    build_prompt: Callable[[], str],
    call_llm: Callable[[str], str],
    max_regens: int = 3,
) -> tuple[str, str]:
    """
    Generate text with a user-in-the-loop review cycle.
    Returns (final_text, final_prompt).
    """
    prompt = build_prompt()
    attempts = 0
    while True:
        text = call_llm(prompt).strip()
        action = ask_review(label, text)
        if action == "accept":
            return text, prompt
        if action == "quit":
            raise KeyboardInterrupt(f"Aborted at step: {label}")
        if action == "edit":
            print_sep(f"{label} — EDIT PROMPT")
            print("Current prompt:\n", prompt, "\n")
            print("Enter the new prompt. Finish with an empty line:")
            lines = []
            while True:
                ln = input()
                if ln == "":
                    break
                lines.append(ln)
            prompt = "\n".join(lines).strip() or prompt
            continue
        # if action == 'regen'
        attempts += 1
        continue

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

    return idxs + list(range(tail_start, n)), ua_sampled + ua_tail


def run_procedural_generation(
    seed_text: Optional[str] = None,
    seed_file: Optional[str] = None,
    bwor: int = 4,            # PHASE 1 size and also phase-2 bootstrap width
    total_pairs: int = 8,    # number of (user, agent) pairs to produce TOTAL
    call_llm: Optional[Callable[[str], str]] = None,
    temporal_reasoning: bool = False,
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
    current_user_time = now_est()
    
    overall_start = time.perf_counter()

    # PHASE 1: build with full context
    pairs = 0
    while pairs < bwor:
        iter_start = time.perf_counter()

        base_hist_str = render_history(history)

        # USER
        def build_user_prompt():
            return prompt_user(seed, base_hist_str, seed_file, verbose=True, temporal_reasoning=temporal_reasoning)
        u_text, _u_prompt = gen_with_review("USER", build_user_prompt, call_llm, max_regens=3)
        user_ts = current_user_time
        history.append(Turn(user=u_text, timestamp_user=user_ts))

        # AGENT
        hist_with_user = render_history(history)
        def build_agent_prompt():
            return prompt_agent("", hist_with_user, verbose=False)
        a_text, _a_prompt = gen_with_review("AGENT", build_agent_prompt, call_llm, max_regens=3)
        history[-1].agent = a_text
        history[-1].timestamp_agent = agent_reply_time(user_ts)

        # REASONING
        def build_reason_prompt():
            return prompt_agent_reasoning(hist_with_user, a_text, verbose=False)
        r_text, _r_prompt = gen_with_review("AGENT REASONING", build_reason_prompt, call_llm, max_regens=3)
        history[-1].agent_reasoning = r_text

        current_user_time = next_user_time(user_ts, temporal_reasoning=temporal_reasoning)
        pairs += 1

        iter_elapsed = time.perf_counter() - iter_start
        print(f"phase 1 full context pair {pairs} done in {iter_elapsed:.2f}s")


    # PHASE 2: one bootstrapped pair at a time
    while pairs < total_pairs:
        iter_start = time.perf_counter()

        idxs, ctx = build_phase2_context(history, bwor=bwor, min_tail=2)
        base_hist_str = render_history(ctx)

        # USER
        def build_user_prompt():
            return prompt_user(seed, base_hist_str, seed_file, verbose=False, temporal_reasoning=temporal_reasoning)
        u_text, _u_prompt = gen_with_review("USER", build_user_prompt, call_llm, max_regens=3)
        user_ts = current_user_time
        history.append(Turn(user=u_text, timestamp_user=user_ts))

        # AGENT
        hist_with_user = render_history(ctx + [Turn(user=u_text, timestamp_user=user_ts)])
        def build_agent_prompt():
            return prompt_agent("", hist_with_user, verbose=False)
        a_text, _a_prompt = gen_with_review("AGENT", build_agent_prompt, call_llm, max_regens=3)
        history[-1].agent = a_text
        history[-1].timestamp_agent = agent_reply_time(user_ts)

        # REASONING
        def build_reason_prompt():
            return prompt_agent_reasoning(hist_with_user, a_text, verbose=False)
        r_text, _r_prompt = gen_with_review("AGENT REASONING", build_reason_prompt, call_llm, max_regens=3)
        history[-1].agent_reasoning = r_text

        current_user_time = next_user_time(user_ts, temporal_reasoning=temporal_reasoning)
        pairs += 1

        iter_elapsed = time.perf_counter() - iter_start
        print(f"phase 2 bootstrap context pair {pairs} done in {iter_elapsed:.2f}s; {idxs=}")

    total_elapsed = time.perf_counter() - overall_start
    print(f"total generation time for {pairs} pairs: {total_elapsed:.2f}s")

    return history

def ollama_call_model(prompt: str, model: str = "llama3.1") -> str:
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
    SEED_TEXT =\
        "You are a sales analyst who wants to review and improve sales performance."

    history = run_procedural_generation(
        seed_text=SEED_TEXT,
        seed_file=seed_file,
        bwor=CONTEXT_MSGS_LEN,
        total_pairs=TOTAL_MSGS_LEN,
        call_llm=ollama_call_model,
        temporal_reasoning=TEMPORAL_REASONING,
    )

    # pretty print
    WIDTH = 30
    B = "#"
    if False:
        for i, turn in enumerate(history, 1):
            title = f" {i:02d} TURN "
            pad = WIDTH - len(title)
            side = max(pad, 0) // 2
            header = B * side + title + B * (pad - side)

            print(B * WIDTH)
            print(header)
            print(B * WIDTH)

            def section_header(name: str) -> str:
                t = f" {name}: "
                pad2 = WIDTH - len(t)
                left = pad2 // 2
                right = pad2 - left
                return B * left + t + B * right

            print(section_header("USER"))
            uts = fmt_ts(turn.timestamp_user) if turn.timestamp_user else "NA"
            print(f"[{uts}]\n{turn.user.strip()}\n")

            print(section_header("AGENT"))
            ats = fmt_ts(turn.timestamp_agent) if turn.timestamp_agent else "NA"
            print(f"[{ats}]\n{(turn.agent or '').strip()}\n")
            
            print(section_header("AGENT REASONING"))
            print(f"[{ats}]\n{(turn.agent_reasoning or '').strip()}\n")

    pairs = []
    tmp = []
    for t in history:
        tmp.append(t)
        if len(tmp) == 2:
            pairs.append(tmp)
            tmp = []

    # single ua save
    ua_path = os.path.join(eval_root, "src", "pipeline", "ua.json")
    os.makedirs(os.path.dirname(ua_path), exist_ok=True)
    ua: Dict[int, Dict[str, str]] = {
        i: {
            "user": t.user,
            "agent": t.agent or "",
            "agent_reasoning": t.agent_reasoning or "",
            "timestamp_user": fmt_ts(t.timestamp_user) if t.timestamp_user else "",
            "timestamp_agent": fmt_ts(t.timestamp_agent) if t.timestamp_agent else "",
        }
        for i, t in enumerate(history)
    }
    with open(ua_path, "w", encoding="utf-8") as f:
        json.dump(ua, f, indent=2, ensure_ascii=False)

    # schema save, blank with TODOs
    messages = []
    for t in history:
        messages.append({
            "role": "user",
            "content": t.user,
            "timestamp": fmt_ts(t.timestamp_user) if t.timestamp_user else ""
        })
        messages.append({
            "role": "agent",
            "content": (t.agent or ""),
            "reasoning": (t.agent_reasoning or ""),
            "timestamp": fmt_ts(t.timestamp_agent) if t.timestamp_agent else ""
        })
    
    ts_list = [x for x in (
        [h.timestamp_user for h in history] +
        [h.timestamp_agent for h in history]
    ) if x is not None]
    start_ts = fmt_ts(min(ts_list)) if ts_list else "TODO"
    end_ts = fmt_ts(max(ts_list)) if ts_list else "TODO"

    out_json = [
        {
            "history_id": "TODO",
            "history_type": ["TODO"],
            "haystack_session_ids": ["TODO"],
            "haystack_sessions": [
                {
                    "session_id": "TODO",
                    "dataref": f"{seed_file}",
                    "start_timestamp": start_ts,
                    "end_timestamp": end_ts,
                    "messages": messages
                }
            ],
            "questions": ["TODO"],
        }
    ]

    schema_path = os.path.join(eval_root, "src", "pipeline", "schema.json")
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(out_json, f, indent=2, ensure_ascii=False)