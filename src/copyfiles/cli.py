"""
CLI entrypoint for copyfiles package.
"""
import argparse
import sys
from pathlib import Path
from .core import (
    load_extra_patterns,
    scan_files,
    filter_files,
    write_file_list,
    InvalidRootError,
    ConfigFileError,
    OutputError,
)

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