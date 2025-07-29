# copyfiles

**copyfiles** is a small but mighty CLI that scans a project directory, filters out junk via `.gitignore`-style rules, and spits out a single **`copyfiles.txt`** containing:

1.  _Project tree_ – an indented outline of kept files and folders.
2.  _File contents_ – each retained file wrapped in a language-tagged code fence.

It’s perfect for piping an entire repo into an LLM prompt or sharing a compact “snapshot” of code with teammates.

---

## Features

| Feature                      | What it does                                                                             |
| ---------------------------- | ---------------------------------------------------------------------------------------- |
| **Smart filtering**          | Honors your project’s `.gitignore`, plus optional extra ignore file (`--config`).        |
| **Size guards & truncation** | Skip very large files (`--skip-large`) or keep only the first _N_ bytes (`--max-bytes`). |
| **Colorful, pretty CLI**     | Rich / Colorama styling with automatic NO_COLOR detection.                               |
| **Zero-config defaults**     | Run `copyfiles` in any repo and get a sane `copyfiles.txt` instantly.                    |

---

## Installation

```bash
# Recommended: inside a virtualenv
pip install copyfiles           # from PyPI
# or, for local development
git clone https://github.com/yourname/copyfiles
cd copyfiles
pip install -e '.[dev]'         # installs package + test/QA deps
```

> **Requires** Python 3.8+

---

## Quick Start

```bash
# From your project root
copyfiles

# Generates ./copyfiles.txt:
# ├── app.py
# ├── module/
# │   └── __init__.py
# └── README.md
```

Open `copyfiles.txt` in any editor or paste it directly into ChatGPT / Gemini – you’ll see an ASCII tree followed by each file’s contents inside code fences.

---

## Advanced CLI Flags

| Flag              | Default         | Purpose                                                            |
| ----------------- | --------------- | ------------------------------------------------------------------ |
| `--root PATH`     | `.`             | Directory to scan.                                                 |
| `--out FILE`      | `copyfiles.txt` | Output file name/path.                                             |
| `--config FILE`   | _none_          | Extra ignore patterns (one per line, same syntax as `.gitignore`). |
| `--max-bytes N`   | `100 000`       | Truncate individual files to the first _N_ bytes.                  |
| `--skip-large KB` | _off_           | Skip files **larger than** _KB_ kilobytes entirely.                |
| `-v / --verbose`  | off             | Show scanning / filtering progress.                                |
| `--no-color`      | off             | Force plain-text output (useful in CI).                            |
| `-V / --version`  | –               | Print version and exit.                                            |
| `--help`          | –               | Full help text with examples.                                      |

---

## Contributing

1. **Fork** & clone the repo.
2. Create a virtualenv and install dev deps:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e '.[dev]'
   ```

3. Run the _entire_ QA suite before submitting a PR:

   ```bash
   pytest          # unit + CLI tests
   tox -p auto     # multi-python matrix + lint
   ruff check src tests  # additional lint if you like
   ```

4. Commit using conventional commits (`feat: …`, `fix: …`, etc.) and open a pull request – GitHub Actions will run the same tox matrix.

### Project Layout

```
src/copyfiles/       # library & CLI
tests/               # unit and CLI tests + fixtures
README.md
pyproject.toml
tox.ini
```

---

## Licence

MIT – see `LICENSE` file for full text.

---

> Made with ☕, 🐍, and a sprinkle of Rich ANSI sparkle.
