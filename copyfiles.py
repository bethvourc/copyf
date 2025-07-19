"""
Copyfiles - A standalone script to copy project files with content.

This script scans a directory tree, filters out ignored files based on .gitignore
and default patterns, and generates a copyfiles.txt file containing file paths
and their contents for easy project sharing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

# External dependency
try:
    import pathspec  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write("Error: 'pathspec' library is required. Install via 'pip install pathspec'.\n")
    sys.exit(1)

# Default patterns to ignore when copying files
DEFAULT_PATTERNS: List[str] = [
    ".env",
    "node_modules/",
    "__pycache__/",
    "copyfiles.py",
]


def load_gitignore(root: Path) -> "pathspec.PathSpec":
    """Compile the project's ``.gitignore`` into a :class:`pathspec.PathSpec`.

    Parameters
    ----------
    root
        Absolute or relative path to the project root (directory containing
        the ``.gitignore`` file).

    Returns
    -------
    pathspec.PathSpec
        A compiled spec ready to match file paths. If no ``.gitignore`` is
        present, an **empty** spec is returned so callers can still invoke
        :py:meth:`~pathspec.PathSpec.match_file` safely.
    """

    gitignore_path = root / ".gitignore"

    # If the file doesn't exist, return an empty spec so filtering logic can
    # proceed without special-casing.
    if not gitignore_path.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])

    # Read patterns, stripping trailing newlines for robustness.
    with gitignore_path.open("r", encoding="utf-8") as fh:
        patterns = [line.rstrip("\n") for line in fh]

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def scan_files(root: Path) -> List[Path]:
    """Recursively collect **all** files under *root*.

    Parameters
    ----------
    root
        Directory whose contents should be enumerated.

    Returns
    -------
    List[pathlib.Path]
        Absolute ``Path`` objects for every file discovered. Directories are
        excluded. The list is sorted for deterministic output.
    """
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"scan_files: provided root '{root}' is not a directory")

    # ``Path.rglob('*')`` traverses recursively. Filter to files only.
    files = [p for p in root.rglob("*") if p.is_file()]

    # Sort so that results are deterministic (useful for tests & diffing).
    return sorted(files)


def main() -> None:
    """Orchestrate the file-copy workflow (scanner → filter → writer).

    This is still a placeholder; subsequent implementation steps will flesh out
    the full pipeline and CLI interface.
    """
    pass


if __name__ == "__main__":
    main()
