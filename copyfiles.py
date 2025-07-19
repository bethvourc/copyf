"""
Copyfiles - A standalone script to copy project files with content.

This script scans a directory tree, filters out ignored files based on .gitignore,
user-provided config patterns, and sensible defaults, then generates a
`copyfiles.txt` containing file paths and their contents for easy LLM context
sharing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Custom exceptions for better error handling
class CopyfilesError(Exception):
    """Base exception for copyfiles errors."""
    pass


class InvalidRootError(CopyfilesError):
    """Raised when the provided root directory is invalid."""
    pass


class ConfigFileError(CopyfilesError):
    """Raised when there are issues with config files."""
    pass


class OutputError(CopyfilesError):
    """Raised when there are issues writing output files."""
    pass


class FileReadError(CopyfilesError):
    """Raised when there are issues reading source files."""
    pass

# Third-party dependency=
try:
    import pathspec  # type: ignore
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "Error: 'pathspec' library is required. Install via 'pip install pathspec'.\n"
    )
    sys.exit(1)

# Default ignore patterns (extendable via --config)
DEFAULT_PATTERNS: List[str] = [
    ".env",
    "node_modules/",
    "__pycache__/",
    "copyfiles.py",
]

DEFAULT_SPEC = pathspec.PathSpec.from_lines("gitwildmatch", DEFAULT_PATTERNS)

# .gitignore handling

def load_gitignore(root: Path) -> "pathspec.PathSpec":
    """Compile the project’s ``.gitignore`` into a :class:`pathspec.PathSpec`."""
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])

    with gitignore_path.open("r", encoding="utf-8") as fh:
        patterns = [line.rstrip("\n") for line in fh]

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

# Config file handling

def load_extra_patterns(config_path: Path) -> "pathspec.PathSpec":
    """Read newline-separated patterns from *config_path* and compile spec."""
    if not config_path.exists():
        raise ConfigFileError(f"Config file '{config_path}' does not exist")
    
    if not config_path.is_file():
        raise ConfigFileError(f"'{config_path}' is not a file")

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigFileError(f"Could not read config file '{config_path}': {e}")

    return pathspec.PathSpec.from_lines("gitwildmatch", lines)

# File discovery

def scan_files(root: Path) -> List[Path]:
    """Recursively collect **all** files under *root*."""
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

# File filtering

def filter_files(
    paths: List[Path],
    root: Path,
    extra_spec: Optional["pathspec.PathSpec"] = None,
) -> List[Path]:
    """Filter out files matched by `.gitignore`, DEFAULT_PATTERNS, or *extra_spec*."""
    gitignore_spec = load_gitignore(root)

    kept: List[Path] = []
    for p in paths:
        try:
            rel_path = p.relative_to(root).as_posix()
        except ValueError:
            rel_path = p.as_posix()

        if gitignore_spec.match_file(rel_path):
            continue
        if DEFAULT_SPEC.match_file(rel_path):
            continue
        if extra_spec and extra_spec.match_file(rel_path):
            continue
        kept.append(p)

    return kept

# Output generation

def _is_binary(data: bytes) -> bool:
    return b"\0" in data


def write_file_list(
    paths: List[Path],
    out_path: Path,
    root: Path,
    max_bytes: int = 100_000,
    verbose: bool = False,
) -> None:
    """Write headers and file contents to *out_path*."""

    try:
        out_path = out_path.resolve()
    except (OSError, RuntimeError) as e:
        raise OutputError(f"Could not resolve output path '{out_path}': {e}")

    # Ensure output directory exists
    out_dir = out_path.parent
    if not out_dir.exists():
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise OutputError(f"Could not create output directory '{out_dir}': {e}")

    bytes_written = 0

    if verbose:
        print(f"[copyfiles] Writing to {out_path} …")

    try:
        with out_path.open("w", encoding="utf-8", newline="\n") as out_fh:
            for p in sorted(paths):
                try:
                    rel = p.relative_to(root).as_posix()
                except ValueError:
                    rel = p.as_posix()

                try:
                    raw = p.read_bytes()[: max_bytes + 1]
                except (OSError, PermissionError, FileNotFoundError) as e:
                    if verbose:
                        print(f"[copyfiles] ! Could not read {rel}: {e}")
                    continue
                except Exception as e:
                    if verbose:
                        print(f"[copyfiles] ! Unexpected error reading {rel}: {e}")
                    continue

                if _is_binary(raw):
                    if verbose:
                        print(f"[copyfiles] - Skipping binary file {rel}")
                    continue

                text = raw.decode("utf-8", errors="replace")
                truncated = len(raw) > max_bytes
                if truncated:
                    text = text[:max_bytes]

                out_fh.write(f"# {rel}\n")
                out_fh.write(text)
                if truncated:
                    out_fh.write("\n# [truncated]\n")
                out_fh.write("\n\n")
                bytes_written += len(text)
    except (OSError, PermissionError) as e:
        raise OutputError(f"Could not write to output file '{out_path}': {e}")

    if verbose:
        print(f"[copyfiles] Done. {len(paths)} files processed, {bytes_written} bytes written.")

# CLI entry-point 

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="copyfiles",
        description="Generate a copyfiles.txt containing project files and contents.",
    )
    parser.add_argument("--root", type=Path, default=Path("."), help="Project root directory")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("copyfiles.txt"),
        help="Output file path (default: copyfiles.txt)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to file with additional ignore patterns (one per line)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=100_000,
        help="Maximum bytes per file to include (default: 100k)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def main() -> None:
    """Run scan → filter → write to produce *copyfiles.txt*."""
    try:
        ns = _parse_args()

        root: Path = ns.root.resolve()
        out_path: Path = ns.out.resolve()

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

        kept_files = filter_files(all_files, root, extra_spec=extra_spec)

        if ns.verbose:
            print(f"[copyfiles] {len(all_files)} files found, {len(kept_files)} after filtering.")

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
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
