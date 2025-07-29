"""
Core logic for copyfiles package.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Any, Iterable, cast

from . import __version__

# Optional deps
try:
    import pathspec  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write("Error: install 'pathspec' → pip install pathspec\n")
    sys.exit(1)

try:
    from colorama import Fore, Style  # type: ignore
    from colorama import init as colorama_init

    colorama_init()
    COLORAMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    COLORAMA_AVAILABLE = False

# Exceptions
class CopyfilesError(Exception): ...
class InvalidRootError(CopyfilesError): ...
class ConfigFileError(CopyfilesError): ...
class OutputError(CopyfilesError): ...
class FileReadError(CopyfilesError): ...

# Defaults
DEFAULT_PATTERNS: list[str] = [
    ".env",
    "node_modules/",
    "__pycache__",
    "copyfiles.py",
    ".git/",
    ".gitignore",
]
DEFAULT_SPEC = pathspec.PathSpec.from_lines("gitwildmatch", DEFAULT_PATTERNS)

_LANG_MAP: dict[str, str] = {
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


# Ignore helpers
def load_gitignore(root: Path) -> pathspec.PathSpec:
    gp = root / ".gitignore"
    if not gp.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    with gp.open(encoding="utf-8") as fh:
        return pathspec.PathSpec.from_lines("gitwildmatch", fh)


def load_extra_patterns(config_path: Path) -> pathspec.PathSpec:
    if not config_path.exists():
        raise ConfigFileError(f"Config file '{config_path}' does not exist")
    if not config_path.is_file():
        raise ConfigFileError(f"'{config_path}' is not a file")
    with config_path.open(encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)

# File-scanning
def scan_files(root: Path) -> list[Path]:
    root = root.resolve()
    if not root.exists():
        raise InvalidRootError(f"Root directory '{root}' does not exist")
    if not root.is_dir():
        raise InvalidRootError(f"Root path '{root}' is not a directory")
    return sorted(p for p in root.rglob("*") if p.is_file())


def filter_files(
    paths: list[Path],
    root: Path,
    extra_spec: pathspec.PathSpec | None = None,
    skip_large_kb: int | None = None,
) -> list[Path]:
    git_spec = load_gitignore(root)
    kept: list[Path] = []
    for p in paths:
        rel = p.relative_to(root).as_posix()
        if git_spec.match_file(rel) or DEFAULT_SPEC.match_file(rel):
            continue
        if extra_spec and extra_spec.match_file(rel):
            continue
        if skip_large_kb is not None and p.stat().st_size > skip_large_kb * 1024:
            continue
        kept.append(p)
    return kept

# Project-tree renderer
def build_project_tree(paths: Iterable[Path], root: Path) -> str:  # noqa: C901
    """
    Return an ASCII tree similar to the Unix **tree** utility.
    """
    tree: dict[str, Any] = {}

    def _ensure_dir(rel: Path) -> dict[str, Any]:
        cur: dict[str, Any] = tree
        for part in rel.parts:
            cur = cast(dict[str, Any], cur.setdefault(part, {}))
        return cur

    rel_files: list[Path] = []
    for p in paths:
        rel = p.relative_to(root)
        rel_files.append(rel)
        for parent in rel.parents:
            if parent == Path("."):
                break
            _ensure_dir(parent)

    for f in rel_files:  # mark file leaves
        cur: dict[str, Any] = tree
        for part in f.parts[:-1]:
            cur = cast(dict[str, Any], cur[part])
        cur[f.parts[-1]] = None  # mark leaf

    lines: list[str] = ["Project tree\n"]

    def _walk(node: dict[str, Any] | None, prefix: str = "") -> None:
        if node is None:
            return
        items = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0]))
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
def write_file_list(  # noqa: C901
    paths: list[Path],
    out_path: Path,
    root: Path,
    max_bytes: int = 100_000,
    verbose: bool = False,
    skip_large_kb: int | None = None,
) -> None:
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    skipped: list[str] = []
    truncated_files: list[str] = []
    skipped_for_size: list[str] = []
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

    toc = ["## Table of Contents\n", "- [Project Tree](#project-tree)"]
    sections: list[tuple[str, str, Path]] = []

    for p in sorted(paths):
        rel = p.relative_to(root).as_posix()
        anchor = rel.translate(str.maketrans("", "", "./ -"))
        toc.append(f"- [{rel}](#{anchor})")
        sections.append((rel, anchor, p))
    toc.append("- [Summary](#summary)\n")

    with out_path.open("w", encoding="utf-8", newline="\n") as out_fh:
        out_fh.write(header)
        out_fh.write("\n".join(toc) + "\n\n")
        out_fh.write("## Project Tree\n\n")
        out_fh.write(build_project_tree(paths, root) + "\n")
        out_fh.write("## Files\n\n")

        for rel, anchor, p in sections:
            if skip_large_kb is not None and p.stat().st_size > skip_large_kb * 1024:
                skipped_for_size.append(rel)
                continue

            out_fh.write(f'### {rel}\n<a id="{anchor}"></a>\n')
            try:
                raw = p.read_bytes()[: max_bytes + 1]
            except (OSError, PermissionError, FileNotFoundError):
                skipped.append(rel)
                continue

            if _is_binary(raw):
                skipped.append(rel)
                continue

            text = raw.decode("utf-8", errors="replace")
            if len(raw) > max_bytes:
                text = text[:max_bytes]
                truncated_files.append(rel)

            lang = _lang_from_ext(p)
            fence = f"```{lang}" if lang else "```"
            out_fh.write(f"{fence}\n{text}")
            if rel in truncated_files:
                out_fh.write("\n# [truncated]")
            out_fh.write("\n```\n\n")
            bytes_written += len(text)

        # Summary
        out_fh.write("## Summary\n\n")
        out_fh.write(f"- **Total files kept:** {len(paths) - len(skipped_for_size)}\n")
        out_fh.write(f"- **Total bytes written:** {bytes_written}\n")
        if skipped_for_size:
            out_fh.write(
                f"- **Files skipped for size:** {len(skipped_for_size)} (> {skip_large_kb} KB)\n"
            )
            for s in skipped_for_size:
                out_fh.write(f"    - {s}\n")
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
            f"{len(paths) - len(skipped_for_size)} files processed, {bytes_written} bytes written. "
            f"{len(skipped)} skipped, {len(truncated_files)} truncated, {len(skipped_for_size)} skipped for size."
        )
        if COLORAMA_AVAILABLE:
            print(Fore.GREEN + msg + Style.RESET_ALL)
        else:
            print(msg)
