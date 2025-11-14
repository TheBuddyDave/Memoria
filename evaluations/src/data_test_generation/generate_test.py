"""Stubs for testing LLM generation from an input file.

This module provides small helper functions that:
- verify the input path exists
- read the file contents
- build a prompt with a TODO placeholder for the middle prompting
- send the prompt to an LLM endpoint (TODO: implement actual call)

The functions below are intentionally minimal; the network/LLM call
is left as a TODO with examples of two approaches used elsewhere in the
repo (subprocess + ollama, or OpenAI-compatible client).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import json
import subprocess
from subprocess import CompletedProcess
import re
import hashlib
from typing import Dict, Any

# Determine repo root for writing tests relative to the repository
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[3]
_TESTS_ROOT = _REPO_ROOT / "evaluations" / "tests"


def verify_path(path: str | Path) -> Path:
	"""Verify the given path exists and return a Path object.

	Raises FileNotFoundError if the path does not exist.
	"""
	p = Path(path)
	if not p.exists():
		raise FileNotFoundError(f"Input file not found: {p}")
	return p


def read_input_file(path: str | Path, *, as_text: bool = True) -> str:
	"""Read and return file contents
	"""
	p = verify_path(path)
	if as_text:
		return p.read_text(encoding="utf-8")
	# fallback: return raw bytes decoded as utf-8
	return p.read_bytes().decode("utf-8")


def build_prompt(file_contents: str, instruction: Optional[str] = None) -> str:
	"""Construct and return a prompt string for the LLM.

	`instruction` is an optional short text inserted between the file
	contents and the final call-to-action
	"""
	prompt = "Read the following file contents and follow the instruction.\n\n"
	prompt += "File contents:\n" + file_contents + "\n\n"
	if instruction:
		prompt += "Instruction:\n" + instruction + "\n\n"
	prompt += "Final answer:"
 
    # TODO: Add more complex prompt engineering per prompt chaining procedures
    # Eg. everything under: https://docs.google.com/document/d/1e6vY6C0uPapvVouDKvOnlaN781MRldfVO5M8HlnM0aU/edit?tab=t.0
	return prompt


def send_to_llm(prompt: str, *, model: str = "llama3.2", method: str = "ollama") -> str:
	"""Send prompt to an LLM and return the textual response.

	TODO: implement the actual call. Two example approaches used elsewhere
	in this repo are shown below as comments. Choose one and implement.

	Examples (commented):
	- Ollama via subprocess (see `evaluations/src/generation/generate_one.py`):

		import subprocess
		result = subprocess.run(
			["ollama", "run", "llama3.2"],
			input=prompt.encode(),
			capture_output=True,
		)
		return result.stdout.decode().strip()

	For now this uses the local `ollama` CLI via subprocess to run the
	specified model. If `ollama` is not available in PATH or the model
	fails, a RuntimeError is raised with stderr attached.
	"""
	# Build the base command. We mirror the pattern used elsewhere in the
	# repository: `ollama run <model>` and stream the prompt via stdin.
 
    # TODO: Need Michael to test this function with ollama installed
	cmd = ["ollama", "run", model]

	try:
		proc: CompletedProcess = subprocess.run(
			cmd,
			input=prompt.encode("utf-8"),
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			check=False,
			timeout=120,
		)
	except FileNotFoundError as exc:
		raise RuntimeError("`ollama` executable not found. Install ollama or adjust PATH.") from exc
	except subprocess.TimeoutExpired as exc:
		raise RuntimeError("LLM call timed out") from exc

	stdout = proc.stdout.decode("utf-8", errors="replace").strip()
	stderr = proc.stderr.decode("utf-8", errors="replace").strip()

	if proc.returncode != 0:
		raise RuntimeError(f"LLM call failed (code={proc.returncode}): {stderr}")

	return stdout


def process_file(path: str | Path, instruction: Optional[str] = None) -> str:
	"""High-level helper: verify -> read -> build prompt -> send to LLM.

	This function returns the LLM response as a string. Network/LLM calls
	are intentionally left unimplemented in this stub.
	"""
	p = verify_path(path)
	contents = read_input_file(p)
	prompt = build_prompt(contents, instruction=instruction)
	response = send_to_llm(prompt)
	return response


def process_llm_response(response_text: str) -> Dict[str, Any]:
	"""Attempt to parse the LLM output into a JSON-like dict.

	Strategy (heuristic):
	1. Try json.loads on the entire response.
	2. If that fails, try to extract the first JSON object or array found
	   in the text using a simple regexp for balanced braces/brackets.
	3. If still failing, return a dict containing the raw text under
	   the key 'raw_output'.

	This is intentionally permissive since LLM outputs vary. You can
	replace with a stricter parser later.
	"""
	# 1) try to parse entire response
	try:
		return json.loads(response_text)
	except Exception:
		pass

	# 2) look for a JSON block: try braces then brackets
	# Note: simple regex; not a full parser. Grab first {...} or [...] block.
	brace_match = re.search(r"\{[\s\S]*\}", response_text)
	if brace_match:
		candidate = brace_match.group(0)
		try:
			return json.loads(candidate)
		except Exception:
			pass

	bracket_match = re.search(r"\[[\s\S]*\]", response_text)
	if bracket_match:
		candidate = bracket_match.group(0)
		try:
			return json.loads(candidate)
		except Exception:
			pass

	# 3) fallback: wrap raw text
	return {"raw_output": response_text}


def _sanitize_name(s: str) -> str:
	"""Make a filesystem-safe, short name from the input string."""
	# Replace path separators and whitespace, remove problematic chars
	s = re.sub(r"[\\/]+", "-", s)
	s = re.sub(r"\s+", "_", s)
	s = re.sub(r"[^A-Za-z0-9_.-]", "", s)
	return s[:128]


def make_parametric_test_name(input_path: str | Path, instruction: Optional[str] = None) -> str:
	"""Generate a parametric test name from the input file and instruction.

	Format: <input-stem>__<short-hash-of-instruction-or-empty>
	Example: BiotechCropsAllTables2024__a1b2c3d4.json
	"""
	p = Path(input_path)
	stem = _sanitize_name(p.stem)
	if instruction:
		h = hashlib.sha1(instruction.encode("utf-8")).hexdigest()[:8]
		return f"{stem}__{h}"
	return stem


def write_test_output(output: Dict[str, Any], data_folder_name: str, test_name: str) -> Path:
	"""Write the output dict as pretty JSON to
	evaluations/tests/<data_folder_name>/<test_name>.json and return the Path.

	Creates directories if needed.
	"""
	target_dir = _TESTS_ROOT / _sanitize_name(data_folder_name)
	target_dir.mkdir(parents=True, exist_ok=True)

	fname = f"{_sanitize_name(test_name)}.json"
	out_path = target_dir / fname
	with out_path.open("w", encoding="utf-8") as f:
		json.dump(output, f, indent=2, ensure_ascii=False)
	return out_path


def run_and_save_test(input_path: str | Path, *, instruction: Optional[str] = None,
					  data_folder_name: Optional[str] = None, test_name: Optional[str] = None) -> Path:
	"""High-level helper to run the generate flow and save the processed output.

	- input_path: path to the source data file (used to generate a test name if none provided)
	- instruction: optional prompt instruction
	- data_folder_name: name of subfolder under `evaluations/tests/` to store the test
	  (defaults to the input file's parent folder name)
	- test_name: override the generated test name

	Returns the path to the written test JSON.
	"""
	p = verify_path(input_path)
	resp = process_file(p, instruction=instruction)
	processed = process_llm_response(resp)

	if data_folder_name is None:
		data_folder_name = p.parent.name or "unnamed_data"

	if test_name is None:
		test_name = make_parametric_test_name(p, instruction=instruction)

	out_path = write_test_output(processed, data_folder_name, test_name)
	return out_path


if __name__ == "__main__":
	# Minimal CLI so you can run this file directly while implementing the TODOs.
	import argparse

	parser = argparse.ArgumentParser(description="Send a file to an LLM (stub).")
	parser.add_argument("file", help="Path to input file")
	parser.add_argument("--instruction", help="Optional instruction to include in the prompt")
	args = parser.parse_args()

	try:
		out = process_file(args.file, instruction=args.instruction)
		print(out)
	except Exception as exc:
		print(f"Error: {exc}")

