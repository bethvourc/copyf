"""
Core logic for copyfiles package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional
from itertools import chain 
import sys

try:
    import pathspec  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "Error: 'pathspec' library is required. Install via 'pip install pathspec'.\n"
    )
    sys.exit(1)

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
    "__pycache__/",
    "copyfiles.py",  # exclude the tool itself
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

def build_project_tree(paths: Iterable[Path], root: Path) -> str:
    parts: List[str] = ["Project tree\n"]
    rel_paths = [p.relative_to(root) for p in paths]
    dir_set = {rp.parent for rp in rel_paths if rp.parent != Path(".")}
    all_paths = sorted(chain(dir_set, rel_paths), key=lambda p: (p.parts, p.name))
    for ap in all_paths:
        depth = len(ap.parts) - 1
        indent = "│   " * depth + ("├── " if depth else "")
        parts.append(f"{indent}{ap.name}/" if ap.is_dir() else f"{indent}{ap.name}")
    parts.append("")
    return "\n".join(parts)

def _is_binary(data: bytes) -> bool:
    return b"\0" in data

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
    if verbose:
        print(f"[copyfiles] Writing to {out_path} …")

    try:
        with out_path.open("w", encoding="utf-8", newline="\n") as out_fh:
            out_fh.write(build_project_tree(paths, root))
            for p in sorted(paths):
                rel = p.relative_to(root).as_posix()
                try:
                    raw = p.read_bytes()[: max_bytes + 1]
                except (OSError, PermissionError, FileNotFoundError) as e:
                    if verbose:
                        print(f"[copyfiles] ! Could not read {rel}: {e}")
                    continue
                if _is_binary(raw):
                    if verbose:
                        print(f"[copyfiles] - Skipping binary {rel}")
                    continue
                text = raw.decode("utf-8", errors="replace")
                truncated = len(raw) > max_bytes
                if truncated:
                    text = text[:max_bytes]

                lang = _lang_from_ext(p)
                fence = f"```{lang}" if lang else "```"

                out_fh.write(f"# {rel}\n{fence}\n{text}")
                if truncated:
                    out_fh.write("\n# [truncated]")
                out_fh.write("\n```\n\n")
                bytes_written += len(text)
    except (OSError, PermissionError) as e:
        raise OutputError(f"Could not write to '{out_path}': {e}")

    if verbose:
        print(
            f"[copyfiles] Done → {out_path}. "
            f"{len(paths)} files processed, {bytes_written} bytes written."
        )
