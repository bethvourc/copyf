# Implementation Plan

## Project Initialization

- [ ] Step 1: Initialize Python project skeleton
- **Task**: Create base directory structure, initialize git repo, add virtual environment and base files.
- **Description**: Establishes a clean starting point with package layout, dependency management, and version control.
- **Files**:
  - `setup.py`: basic setuptools script
  - `requirements.txt`: empty placeholder
  - `.gitignore`: add defaults for Python (`__pycache__/`, `.venv/`)
  - `README.md`: project title and stub sections
  - `./` (root): create `copy_files/` package directory
- **Step Dependencies**: None
- **User Instructions**: Run `python -m venv .venv` then activate and `pip install -U pip setuptools`.

## Dependencies & Configuration

- [ ] Step 2: Define default exclusion patterns
- **Task**: Add a config module listing built-in ignore patterns (e.g., `.env`, `node_modules/`, `__pycache__/`). Add required libraries to `requirements.txt`.
- **Description**: Centralizes all non-source patterns so they can be customized.
- **Files**:
  - `copy_files/config.py`: new module exporting `DEFAULT_PATTERNS: List[str]`
  - `requirements.txt`: add `pathspec>=0.9.0`
- **Step Dependencies**: Step 1
- **User Instructions**: Review `config.py` to adjust patterns as needed.

## .gitignore Parsing

- [ ] Step 3: Implement .gitignore loader
- **Task**: Create module that reads project’s `.gitignore`, compiles patterns via `pathspec`, and exposes `is_ignored(path: str) -> bool`.
- **Description**: Allows exclusion logic to respect project-specific ignores.
- **Files**:
  - `copy_files/gitignore_parser.py`: functions `load_gitignore(root: Path)` and `is_ignored(path: Path)`
- **Step Dependencies**: Steps 1, 2
- **User Instructions**: Ensure `.gitignore` exists at project root before running.

## File Scanning

- [ ] Step 4: Write recursive file scanner
- **Task**: Implement `scan_files(root: Path) -> List[Path]` that walks the tree and collects all file paths.
- **Description**: Gathers a complete list of candidate files before filtering.
- **Files**:
  - `copy_files/scanner.py`: new module with `scan_files()`
- **Step Dependencies**: Step 1
- **User Instructions**: Run `scan_files()` in REPL to verify it lists all files.

## File Filtering

- [ ] Step 5: Apply ignore and built-in filters
- **Task**: Create `filter_files(paths: List[Path]) -> List[Path]` that removes any path where `is_ignored()` or a default pattern matches.
- **Description**: Narrows the file list to only relevant source/context files.
- **Files**:
  - `copy_files/filter.py`: new module combining gitignore checks and `config.DEFAULT_PATTERNS`
- **Step Dependencies**: Steps 2, 3, 4
- **User Instructions**: Adjust `config.DEFAULT_PATTERNS` if additional exclusions are needed.

## Output Generation

- [ ] Step 6: Generate `copy_files.txt`
- **Task**: Implement `write_file_list(paths: List[Path], out: Path)` and a `main.py` orchestration script to call scan → filter → write.
- **Description**: Produces the flat file list for LLM ingestion.
- **Files**:
  - `copy_files/writer.py`: new module with `write_file_list()`
  - `main.py`: script parsing root and output paths, invoking modules
- **Step Dependencies**: Steps 4, 5
- **User Instructions**: Run `python main.py --root . --out copy_files.txt` to produce output.

## CLI Interface

- [ ] Step 7: Add command-line options
- **Task**: Use `argparse` in `main.py` to expose `--root`, `--out`, `--verbose`, and optional `--config`.
- **Description**: Makes the tool flexible for different projects and workflows.
- **Files**:
  - `main.py`: update to parse and validate CLI args
- **Step Dependencies**: Step 6
- **User Instructions**: Execute `python main.py --help` for usage details.

## Testing Infrastructure

- [ ] Step 8: Setup pytest
- **Task**: Add pytest config and test directory.
- **Description**: Enables unit testing of each module.
- **Files**:
  - `pytest.ini`: pytest settings
  - `tests/__init__.py`: test package
- **Step Dependencies**: Step 1
- **User Instructions**: Run `pytest -q` to confirm test discovery.

## Unit Tests: .gitignore Parser

- [ ] Step 9: Test ignore logic
- **Task**: Write tests in `tests/test_gitignore_parser.py` covering loading patterns and matching sample paths.
- **Description**: Validates that project-specific ignores are honored.
- **Files**:
  - `tests/test_gitignore_parser.py`: test cases with temporary `.gitignore` fixtures
- **Step Dependencies**: Steps 3, 8
- **User Instructions**: Ensure tests pass on default and custom `.gitignore`.

## Unit Tests: Scanner & Filter

- [ ] Step 10: Test scanning & filtering
- **Task**: In `tests/test_scanner_filter.py`, simulate multi-level dirs, .gitignore entries, default patterns, then assert output of `scan_files` and `filter_files`.
- **Description**: Catches edge cases like nested node_modules or env files.
- **Files**:
  - `tests/test_scanner_filter.py`
- **Step Dependencies**: Steps 4, 5, 8
- **User Instructions**: Verify no unexpected files remain after filtering.

## Error Handling

- [ ] Step 11: Implement robust error reporting
- **Task**: Add `copy_files/exceptions.py` for custom exceptions (`MissingGitignore`, `InvalidRoot`, etc.), update modules to raise with clear messages.
- **Description**: Provides user-friendly feedback for misconfiguration or filesystem errors.
- **Files**:
  - `copy_files/exceptions.py`
  - updates to `gitignore_parser.py`, `scanner.py`, `filter.py`, `writer.py`, `main.py`
- **Step Dependencies**: Steps 6, 7, 11
- **User Instructions**: Test by supplying invalid root or removing `.gitignore`.

## Documentation & Examples

- [ ] Step 12: Finalize README
- **Task**: Expand `README.md` with installation, CLI usage, configuration, and examples.
- **Description**: Guides new users through setup, customization, and execution.
- **Files**:
  - `README.md`
- **Step Dependencies**: All previous steps
- **User Instructions**: Review examples and copy command templates for your project.

---

**Summary:**  
We start by scaffolding the project and installing dependencies (`pathspec`), then integrate `.gitignore` parsing and built-in exclusion patterns. Next, we implement file discovery, filtering, and output generation via a CLI tool. We introduce pytest early to cover parser, scanner, and filter logic, and ensure robust error handling with custom exceptions. Finally, we document usage in `README.md`. Each step is self-contained, touches no more than 10 files, and builds logically on prior work, ensuring smooth AI-driven code generation and reliable functionality.
