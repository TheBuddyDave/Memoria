"""Simple runner that collects all evaluation data files.

This imports the dynamic file-listing implemented in
`evaluations.src.data_test_generation.data_files` and prints a summary.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so `evaluations` can be imported
# when this file is executed as a script. The repo root is three parents up
# from this file: repo_root/evaluations/src/data_test_generation/main.py
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from evaluations.src.data_test_generation import data_files


def get_all_data_files() -> list[str]:
	"""Return a list of repo-relative path strings for all data files."""
	# Use the helper so callers can refresh by calling list_data_files()
	return data_files.list_data_files()


if __name__ == "__main__":
	files = get_all_data_files()
	print(f"Found {len(files)} files under: {data_files.DATA_DIR}")
	for p in files:
		print(p)
