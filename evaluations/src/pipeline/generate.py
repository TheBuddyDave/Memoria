import json, subprocess, os

eval_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATAREF = os.path.join(eval_root, "data_ref", "student_scores.csv")
# PROMPT = ""
UI_PATH = os.path.join(eval_root, "idk", "ui.json")
PROMPT_PATH = os.path.join(eval_root, "idk", "prompt.txt")
N_INPUTS = 5

with open(DATAREF, "r") as f:
    csv_data = f.read()
prompt = (
    "You are an individual seeking advice about some data you have.\n"
    f"Here is the dataset:\n\n{csv_data}\n\n"
    "What are some questions you could ask, contextual hints you can give, or statements or observations you can make"
    "about this data which sequentially build upon each other?\n"
    f"List {N_INPUTS} of them (\"**Input 1** ... **Input 2**\", etc.).  Make sure:\n"
    "- Each later item must logically build on earlier ones.\n"
    "- You may make up any logical context.\n"
    "- The recipient will not have access to the data, so make sure to provide it as well.  "
        "Give a small subset of the data at first, then progressively inform the recipient with more and more additional data.  "
        "There is no need to re-iterate data points already given.\n"
    "- Statements and observations do not need to elicit an answer; it suffices to provoke thought.\n"
    "- Include AT LEAST observation and AT LEAST one question.\n"
    "- Explanations or extra text are not needed.\n"
)
with open(PROMPT_PATH, "w") as f:
    f.write(prompt)

result = subprocess.run(
    ["ollama", "run", "llama3.2"],
    input=prompt.encode(),
    capture_output=True,
)
answer = result.stdout.decode().strip()

parts = [p.strip() for p in answer.split("**Input") if p.strip()]
if parts and not parts[0][0].isdigit():
    parts = parts[1:]

ui = {}
for i,p in enumerate(parts[:N_INPUTS]):
    p_clean = p.lstrip("0123456789*:. -").strip()
    # p_qn_clean = p_clean.split("\n")[0]
    ui[i] = p_clean

with open(UI_PATH, "w") as f:
    f.write(json.dumps(ui, indent=4, ensure_ascii=False) + "\n")


print(f"{answer}")
