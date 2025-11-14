"""Dynamic listing of files under ``evaluations/data/``.

This module exposes:
- ``DATA_DIR``: a Path to the ``evaluations/data`` directory
- ``list_data_files()``: function that returns a list of repo-root-relative
 , forward-slash-normalized path strings for all files under the data dir
- ``DATA_FILES``: the list generated at import time by calling
  ``list_data_files()``

The implementation uses the location of this file to locate the
``evaluations/data`` directory, so it will work regardless of the current
working directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import List


# The layout is: repo_root/evaluations/src/data_test_generation/data_files.py
# so parents[2] is the `evaluations` directory and parents[3] is the repo root.
_THIS_FILE = Path(__file__).resolve()
_EVALUATIONS_DIR = _THIS_FILE.parents[2]
DATA_DIR = _EVALUATIONS_DIR / "data"


def list_data_files() -> List[str]:
    """Return a sorted list of all files under ``evaluations/data/``.

    Paths are returned relative to the repository root and use forward
    slashes ("/") for portability. If the data directory does not exist,
    an empty list is returned.
    """
    repo_root = _THIS_FILE.parents[3]
    if not DATA_DIR.exists():
        return []

    result: List[str] = []
    for p in sorted(DATA_DIR.rglob("*")):
        if p.is_file():
            rel = p.relative_to(repo_root)
            # Normalize to forward slashes for consistency across platforms
            result.append(str(rel).replace("\\", "/"))

    return result


# Populate at import time for convenience. Callers can also call
# ``list_data_files()`` directly if they want to refresh later.
DATA_FILES: List[str] = list_data_files()

__all__ = ["DATA_DIR", "DATA_FILES", "list_data_files"]
