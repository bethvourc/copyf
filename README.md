# copyfiles-cli

**copyfiles-cli** is a tiny CLI that scans a project, respects `.gitignore`-style rules, and produces a single **`copyfiles.txt`** with:

- an indented **project tree**, and
- each kept **file’s contents** (wrapped in language-tagged code fences).

Perfect for pasting clean, complete context into LLMs or sharing a compact code snapshot.

---

## Installation

```bash
pip install copyfiles-cli
# CLI command is `copyfiles`
```

> Requires **Python 3.8+**

---

## Quick Start

```bash
# From your project root
copyfiles

# Writes ./copyfiles.txt (tree + file contents)
```

---

## Options (short & sweet)

| Flag              |         Default | What it does                                               |
| ----------------- | --------------: | ---------------------------------------------------------- |
| `--root PATH`     |             `.` | Directory to scan.                                         |
| `--out FILE`      | `copyfiles.txt` | Output file path.                                          |
| `--config FILE`   |               – | Extra ignore patterns (one per line, `.gitignore` syntax). |
| `--max-bytes N`   |        `100000` | Truncate each file after N bytes.                          |
| `--skip-large KB` |               – | Skip files larger than **KB** kilobytes entirely.          |
| `-v, --verbose`   |             off | Show scanning/filtering progress.                          |
| `--no-color`      |             off | Disable colored output (or set `NO_COLOR=1`).              |
| `-V, --version`   |               – | Print version and exit.                                    |
| `-h, --help`      |               – | Show full help.                                            |

---

## Examples

```bash
# Minimal: create copyfiles.txt from current directory
copyfiles

# Different output name + lower per-file limit
copyfiles --out project.txt --max-bytes 50_000

# Skip very large binaries/logs and be chatty
copyfiles --skip-large 200 -v

# Use extra ignore rules
copyfiles --config .cfignore
```

---

## Notes

- Honors your repo’s `.gitignore` plus any patterns you add via `--config`.
- Binary files are skipped automatically.
- The output is plain Markdown so you can paste it directly into ChatGPT/Gemini/Copilot.
