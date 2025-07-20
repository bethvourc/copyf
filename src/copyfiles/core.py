"""
Core logic for copyfiles package.
"""

from __future__ import annotations

import datetime
import sys
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import __version__

# Optional third-party deps
try:
    import pathspec  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "Error: 'pathspec' library is required. Install via 'pip install pathspec'.\n"
    )
    sys.exit(1)

try:
    from colorama import Fore, Style, init as colorama_init  # type: ignore
    colorama_init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Exceptions
class CopyfilesError(Exception): ...
class InvalidRootError(CopyfilesError): ...
class ConfigFileError(CopyfilesError): ...
class OutputError(CopyfilesError): ...
class FileReadError(CopyfilesError): ...

# Defaults & helpers
DEFAULT_PATTERNS: List[str] = [
    ".env",
    "node_modules/",
    "__pycache__",
    "copyfiles.py",   # exclude the tool itself
    ".git/",          # exclude VCS data
    ".gitignore",
]
DEFAULT_SPEC = pathspec.PathSpec.from_lines("gitwildmatch", DEFAULT_PATTERNS)

_LANG_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".css": "css",
    ".scss": "scss",
    ".html": "html",
    ".md": "markdown",
    ".sh": "bash",
    ".rb": "ruby",
    ".go": "go",
}


def _lang_from_ext(path: Path) -> str:
    return _LANG_MAP.get(path.suffix.lower(), "")


# Ignore-file utilities
def load_gitignore(root: Path) -> "pathspec.PathSpec":
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    with gitignore_path.open("r", encoding="utf-8") as fh:
        return pathspec.PathSpec.from_lines("gitwildmatch", fh)


def load_extra_patterns(config_path: Path) -> "pathspec.PathSpec":
    if not config_path.exists():
        raise ConfigFileError(f"Config file '{config_path}' does not exist")
    if not config_path.is_file():
        raise ConfigFileError(f"'{config_path}' is not a file")
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            lines = [
                ln.strip()
                for ln in fh
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigFileError(f"Could not read config file '{config_path}': {e}")
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


# File-scanning helpers
def scan_files(root: Path) -> List[Path]:
    try:
        root = root.resolve()
    except (OSError, RuntimeError) as e:
        raise InvalidRootError(f"Could not resolve root path '{root}': {e}")
    if not root.exists():
        raise InvalidRootError(f"Root directory '{root}' does not exist")
    if not root.is_dir():
        raise InvalidRootError(f"Root path '{root}' is not a directory")
    try:
        return sorted(p for p in root.rglob("*") if p.is_file())
    except (OSError, PermissionError) as e:
        raise InvalidRootError(f"Could not scan directory '{root}': {e}")


def filter_files(
    paths: List[Path],
    root: Path,
    extra_spec: Optional["pathspec.PathSpec"] = None,
) -> List[Path]:
    gitignore_spec = load_gitignore(root)
    kept: List[Path] = []
    for p in paths:
        rel = p.relative_to(root).as_posix()
        if gitignore_spec.match_file(rel):
            continue
        if DEFAULT_SPEC.match_file(rel):
            continue
        if extra_spec and extra_spec.match_file(rel):
            continue
        kept.append(p)
    return kept


# project-tree renderer
def build_project_tree(paths: Iterable[Path], root: Path) -> str:
    """
    Return an ASCII tree (à la the Unix ``tree`` utility).

    • Shows every ancestor directory so the hierarchy is complete.  
    • Directories are listed before files.  
    • Uses proper ``├──``, ``└──``, ``│   `` connectors.  
    • Works purely from the *paths* list – no ``Path.is_dir`` on unknown paths.
    """
    # Build an in-memory nested dict representing the tree
    tree: dict[str, dict | None] = {}

    def _ensure_dir(rel: Path) -> dict:
        cur = tree
        for part in rel.parts:
            cur = cur.setdefault(part, {})  # type: ignore[index]
        return cur

    rel_files: List[Path] = []
    for p in paths:
        rel = p.relative_to(root)
        rel_files.append(rel)
        # add all ancestor directories
        for parent in rel.parents:
            if parent == Path("."):
                break
            _ensure_dir(parent)

    # mark the file nodes
    for f in rel_files:
        cur = tree
        for part in f.parts[:-1]:
            cur = cur[part]  # type: ignore[index]
        cur[f.parts[-1]] = None  # type: ignore[index]

    # Pretty-print 
    lines: List[str] = ["Project tree\n"]

    def _walk(node: dict | None, prefix: str = "") -> None:
        if node is None:
            return
        items = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0]))  # dirs first
        for idx, (name, child) in enumerate(items):
            last = idx == len(items) - 1
            connector = "└── " if last else "├── "
            lines.append(f"{prefix}{connector}{name}{'/' if child is not None else ''}")
            _walk(child, prefix + ("    " if last else "│   "))

    _walk(tree)
    lines.append("")
    return "\n".join(lines)


# Misc helpers
def _is_binary(data: bytes) -> bool:
    return b"\0" in data


# Main writer
def write_file_list(
    paths: List[Path],
    out_path: Path,
    root: Path,
    max_bytes: int = 100_000,
    verbose: bool = False,
) -> None:
    try:
        out_path = out_path.resolve()
    except (OSError, RuntimeError) as e:
        raise OutputError(f"Could not resolve output path '{out_path}': {e}")

    if not out_path.parent.exists():
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise OutputError(f"Could not create directory '{out_path.parent}': {e}")

    bytes_written = 0
    skipped: List[str] = []
    truncated_files: List[str] = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    banner = (
        " _                                 _     _     \n"
        "| | ___  ___ _ __ ___   ___  _ __ | |__ (_)_ __\n"
        "| |/ _ \\| '__/ _` |/ _ \\| '_ \\| '_ \\| | '__|\n"
        "| |  __/| | | (_| | (_) | |_) | | | | | |   \n"
        "|_|\\___|_|  \\__,_|\\___/| .__/|_| |_|_|_|   \n"
        "                       |_|                \n"
    )
    header = f"{banner}\n**copyfiles** v{__version__}  |  {now}\n"

    # Build a table-of-contents + gather metadata
    toc = ["## Table of Contents\n", "- [Project Tree](#project-tree)"]
    file_sections = []
    for p in sorted(paths):
        rel = p.relative_to(root).as_posix()
        anchor = rel.translate(str.maketrans("", "", "./ -"))
        toc.append(f"- [{rel}](#{anchor})")
        file_sections.append((rel, anchor, p))
    toc.append("- [Summary](#summary)\n")

    # Write 
    with out_path.open("w", encoding="utf-8", newline="\n") as out_fh:
        out_fh.write(header)
        out_fh.write("\n".join(toc) + "\n\n")
        out_fh.write("## Project Tree\n\n")
        out_fh.write(build_project_tree(paths, root) + "\n")
        out_fh.write("## Files\n\n")

        for rel, anchor, p in file_sections:
            out_fh.write(f"### {rel}\n<a id=\"{anchor}\"></a>\n")
            try:
                raw = p.read_bytes()[: max_bytes + 1]
            except (OSError, PermissionError, FileNotFoundError) as e:
                skipped.append(rel)
                if verbose:
                    msg = f"[copyfiles] ! Could not read {rel}: {e}"
                    if COLORAMA_AVAILABLE:
                        print(Fore.YELLOW + msg + Style.RESET_ALL)
                    else:
                        print(msg)
                continue

            if _is_binary(raw):
                skipped.append(rel)
                if verbose:
                    msg = f"[copyfiles] - Skipping binary {rel}"
                    if COLORAMA_AVAILABLE:
                        print(Fore.YELLOW + msg + Style.RESET_ALL)
                    else:
                        print(msg)
                continue

            text = raw.decode("utf-8", errors="replace")
            truncated = len(raw) > max_bytes
            if truncated:
                text = text[:max_bytes]
                truncated_files.append(rel)

            lang = _lang_from_ext(p)
            fence = f"```{lang}" if lang else "```"
            out_fh.write(f"{fence}\n{text}")
            if truncated:
                out_fh.write("\n# [truncated]")
            out_fh.write("\n```\n\n")
            bytes_written += len(text)

        # Summary 
        out_fh.write("## Summary\n\n")
        out_fh.write(f"- **Total files kept:** {len(paths)}\n")
        out_fh.write(f"- **Total bytes written:** {bytes_written}\n")
        if skipped:
            out_fh.write(f"- **Files skipped:** {len(skipped)}\n")
            for s in skipped:
                out_fh.write(f"    - {s}\n")
        if truncated_files:
            out_fh.write(f"- **Files truncated:** {len(truncated_files)}\n")
            for t in truncated_files:
                out_fh.write(f"    - {t}\n")

    if verbose:
        msg = (
            f"[copyfiles] Done → {out_path}. "
            f"{len(paths)} files processed, {bytes_written} bytes written. "
            f"{len(skipped)} skipped, {len(truncated_files)} truncated."
        )
        if COLORAMA_AVAILABLE:
            print(Fore.GREEN + msg + Style.RESET_ALL)
        else:
            print(msg)
