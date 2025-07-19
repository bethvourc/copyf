"""
Copyfiles – A standalone script to copy project files *with* content.

The script scans a directory tree, filters out ignored files based on .gitignore,
user-provided config patterns, and sensible defaults, then writes a single
`copyfiles.txt` that contains:

1. A “Project tree” overview, showing the kept files/directories.
2. Each kept file’s contents, enclosed in a language-tagged code fence.

This is handy for piping an entire project into an LLM context.
"""

from __future__ import annotations

import argparse
import sys
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# ──────────────────────────────────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────────────────────────────────
class CopyfilesError(Exception): ...
class InvalidRootError(CopyfilesError): ...
class ConfigFileError(CopyfilesError): ...
class OutputError(CopyfilesError): ...
class FileReadError(CopyfilesError): ...

# ──────────────────────────────────────────────────────────────────────────
# Third-party dependency (pathspec)
# ──────────────────────────────────────────────────────────────────────────
try:
    import pathspec  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "Error: 'pathspec' library is required. Install via 'pip install pathspec'.\n"
    )
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────────────
# Defaults & helpers
# ──────────────────────────────────────────────────────────────────────────
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
    """Return a language hint for fenced code blocks, defaulting to ''."""
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


# ──────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ──────────────────────────────────────────────────────────────────────────
def build_project_tree(paths: Iterable[Path], root: Path) -> str:
    """Create a 'tree'-style text representation from *paths*."""
    parts: List[str] = ["Project tree\n"]
    rel_paths = [p.relative_to(root) for p in paths]
    # Collect every directory that contains a kept file so the tree looks complete
    dir_set = {rp.parent for rp in rel_paths if rp.parent != Path(".")}
    all_paths = sorted(chain(dir_set, rel_paths), key=lambda p: (p.parts, p.name))
    for ap in all_paths:
        depth = len(ap.parts) - 1
        indent = "│   " * depth + ("├── " if depth else "")
        parts.append(f"{indent}{ap.name}/" if ap.is_dir() else f"{indent}{ap.name}")
    parts.append("")  # blank line after tree
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
            # 1) Project tree
            out_fh.write(build_project_tree(paths, root))
            # 2) File contents
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


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="copyfiles",
        description="Generate a copyfiles.txt containing project tree + file contents.",
    )
    p.add_argument("--root", type=Path, default=Path("."), help="Project root dir")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("copyfiles.txt"),
        help="Output file (default: copyfiles.txt)",
    )
    p.add_argument(
        "--config",
        type=Path,
        help="Path to a file with extra ignore patterns (one per line)",
    )
    p.add_argument(
        "--max-bytes",
        type=int,
        default=100_000,
        help="Maximum bytes per file to include (default 100k)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return p.parse_args()


def main() -> None:
    try:
        ns = _parse_args()
        root = ns.root.resolve()
        out_path = ns.out.resolve()

        extra_spec = None
        if ns.config:
            try:
                extra_spec = load_extra_patterns(ns.config.resolve())
                if ns.verbose:
                    print(f"[copyfiles] Loaded extra patterns from {ns.config}")
            except ConfigFileError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

        if ns.verbose:
            print(f"[copyfiles] Scanning {root} …")

        try:
            all_files = scan_files(root)
        except InvalidRootError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        kept_files = filter_files(all_files, root, extra_spec)
        if ns.verbose:
            print(
                f"[copyfiles] {len(all_files)} files found, "
                f"{len(kept_files)} kept after filtering."
            )

        try:
            write_file_list(
                kept_files,
                out_path=out_path,
                root=root,
                max_bytes=ns.max_bytes,
                verbose=ns.verbose,
            )
        except OutputError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
