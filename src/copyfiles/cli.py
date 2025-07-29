"""
CLI entry-point for the *copyfiles* package.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

from . import __version__
from .core import (
    ConfigFileError,
    InvalidRootError,
    OutputError,
    filter_files,
    load_extra_patterns,
    scan_files,
    write_file_list,
)

# Colour / style helpers
try:
    from colorama import Fore, Style  # type: ignore
    from colorama import init as colorama_init
except ImportError:  # pragma: no cover
    COLORAMA_AVAILABLE = False
else:
    COLORAMA_AVAILABLE = True
    colorama_init()

NO_COLOR_ENV = bool(os.environ.get("NO_COLOR"))
USE_COLOR = COLORAMA_AVAILABLE and not NO_COLOR_ENV


def _c(text: str, colour: str) -> str:
    """Return *text* wrapped in colour codes if colouring is enabled."""
    return f"{colour}{text}{Style.RESET_ALL}" if USE_COLOR else text


CYAN = Fore.CYAN if USE_COLOR else ""
GREEN = Fore.GREEN if USE_COLOR else ""
YELLOW = Fore.YELLOW if USE_COLOR else ""
RED = Fore.RED if USE_COLOR else ""
RESET = Style.RESET_ALL if USE_COLOR else ""

TICK = "✔" if USE_COLOR else "[OK]"
CROSS = "✖" if USE_COLOR else "[ERR]"
ARROW = "➜" if USE_COLOR else "->"

# ─────────────────────────────────────────────────────────────
# Banner / examples for --help
# ─────────────────────────────────────────────────────────────
def _make_banner() -> str:
    """Return a coloured ASCII banner spelling COPYFILES."""
    try:
        from pyfiglet import Figlet  # type: ignore

        fig = Figlet(font="standard")
        banner = fig.renderText("COPYFILES").rstrip("\n")
    except Exception:  # noqa: BLE001
        banner = (
            r"""
   ____  ___   ____   ____   __    ______  ______  _____  _____
  / ___|/ _ \ / ___| / ___|  \ \  / / __ \|  ____|/ ____|/ ____|
 | |   | | | | |     \___ \   \ \/ / |  | | |__  | (___ | (___
 | |___| |_| | |___   ___) |   \  /| |__| |  __|  \___ \ \___ \
  \____|\___/ \____| |____/     \/  \____/|_|     |____/ |____/
""".rstrip(
                "\n"
            )
        )
    return _c(banner, CYAN)


BANNER = _make_banner()
EXAMPLES = f"""
Examples:
  {ARROW} copyfiles                          {YELLOW}# minimal run – creates copyfiles.txt{RESET}
  {ARROW} copyfiles --out project.txt --max-bytes 50_000
  {ARROW} copyfiles --skip-large 100 -v
  {ARROW} copyfiles --root ../myproj --config .cfignore
"""

# ─────────────────────────────────────────────────────────────
# Pretty help formatter
# ─────────────────────────────────────────────────────────────
class PrettyHelpFormatter(argparse.RawTextHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):  # noqa: D401
        prefix = _c("Usage: ", YELLOW) if prefix is None else prefix
        return super().add_usage(usage, actions, groups, prefix)

    def start_section(self, heading):  # noqa: D401
        super().start_section(_c(heading.capitalize(), CYAN))

    def format_help(self) -> str:  # noqa: D401
        return f"{BANNER}\n\n" + super().format_help() + EXAMPLES


# ─────────────────────────────────────────────────────────────
# Logging helpers
# ─────────────────────────────────────────────────────────────
def _out(stream, symbol: str, colour: str, msg: str) -> None:
    print(f"{_c(symbol, colour)} {msg}", file=stream)


info: Callable[[str], None] = lambda m: _out(sys.stdout, "ℹ", CYAN, m)  # noqa: E731
success: Callable[[str], None] = lambda m: _out(sys.stdout, TICK, GREEN, m)  # noqa: E731
warn: Callable[[str], None] = lambda m: _out(sys.stderr, "!", YELLOW, m)  # noqa: E731


def fatal(msg: str) -> None:
    """Print *msg* in red then exit(1)."""
    _out(sys.stderr, CROSS, RED, msg)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="copyfiles",
        description="Generate a copyfiles.txt containing project tree + file contents.",
        formatter_class=PrettyHelpFormatter,
        add_help=True,
    )

    p.add_argument("--root", type=Path, default=Path("."), help="Project root dir")
    p.add_argument("--out", type=Path, default=Path("copyfiles.txt"), help="Output file")
    p.add_argument("--config", type=Path, help="Extra ignore patterns file")
    p.add_argument(
        "--max-bytes",
        type=int,
        default=100_000,
        help="Truncate individual files after N bytes (default 100 000)",
    )
    p.add_argument(
        "--skip-large",
        type=int,
        metavar="KB",
        help="Skip files larger than KB kilobytes before truncation",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    p.add_argument("--no-color", action="store_true", help="Disable coloured output")
    p.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"copyfiles {__version__}",
        help="Show version and exit",
    )
    ns = p.parse_args()

    if ns.no_color:  # turn colours off globally
        global USE_COLOR, CYAN, GREEN, YELLOW, RED, RESET, TICK, CROSS, ARROW  # noqa: PLW0603
        USE_COLOR = False
        CYAN = GREEN = YELLOW = RED = RESET = ""
        TICK, CROSS, ARROW = "[OK]", "[ERR]", "->"

    return ns


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main() -> None:  # noqa: C901 – CLI plumbing is naturally long
    try:
        ns = _parse_args()
        root = ns.root.resolve()
        out_path = ns.out.resolve()

        # extra ignore patterns ------------------------------------------------
        extra_spec = None
        if ns.config:
            try:
                extra_spec = load_extra_patterns(ns.config.resolve())
                if ns.verbose:
                    info(f"Loaded extra patterns from {ns.config}")
            except ConfigFileError as exc:
                fatal(str(exc))

        if ns.verbose:
            info(f"Scanning {root} …")

        try:
            all_files = scan_files(root)
        except InvalidRootError as exc:
            fatal(str(exc))

        kept_files = filter_files(
            all_files,
            root,
            extra_spec,
            skip_large_kb=ns.skip_large,
        )
        if ns.verbose:
            success(f"{len(all_files)} files found, {len(kept_files)} kept after filtering")

        # write ----------------------------------------------------------------
        try:
            write_file_list(
                kept_files,
                out_path=out_path,
                root=root,
                max_bytes=ns.max_bytes,
                verbose=ns.verbose,
                skip_large_kb=ns.skip_large,
            )
            success(f"Output written to {out_path}")
        except OutputError as exc:
            fatal(str(exc))

    except KeyboardInterrupt:
        warn("Cancelled by user")
        sys.exit(1)
    except Exception as exc:  # pragma: no cover
        fatal(f"Unexpected error: {exc}")


if __name__ == "__main__":  # pragma: no cover
    main()
