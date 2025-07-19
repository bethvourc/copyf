# Copy Files

A Python tool for generating file lists for LLM ingestion. This tool scans a directory tree, filters files based on `.gitignore` patterns and built-in exclusions, and outputs a list of relevant source files for use with large language models.

## Features

- Recursively scans directory trees
- Respects `.gitignore` patterns
- Applies built-in exclusion patterns
- Generates clean file lists for LLM ingestion
- Command-line interface for easy integration

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Setup

1. Clone this repository:

   ```bash
   git clone <repository-url>
   cd copyf
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -U pip setuptools
   pip install -r requirements.txt
   ```

4. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Usage

### Basic Usage

```bash
# Generate a file list from the current directory
python main.py --root . --out copy_files.txt

# Specify a different root directory
python main.py --root /path/to/project --out files.txt

# Enable verbose output
python main.py --root . --out copy_files.txt --verbose
```

### Command Line Options

- `--root`: Root directory to scan (default: current directory)
- `--out`: Output file path (default: copy_files.txt)
- `--verbose`: Enable verbose output
- `--config`: Path to custom configuration file (optional)

## Configuration

### Built-in Exclusions

The tool includes default exclusion patterns for common files and directories that are typically not relevant for LLM ingestion:

- Environment files (`.env`, `.env.local`)
- Node.js dependencies (`node_modules/`)
- Python cache files (`__pycache__/`, `*.pyc`)
- Build artifacts (`build/`, `dist/`)
- IDE files (`.vscode/`, `.idea/`)

### Custom Configuration

You can customize exclusion patterns by modifying the configuration file or creating a custom one.

## Development

### Project Structure

```
copyf/
├── copy_files/          # Main package
│   ├── __init__.py
│   ├── config.py        # Configuration and default patterns
│   ├── gitignore_parser.py  # .gitignore parsing
│   ├── scanner.py       # File scanning logic
│   ├── filter.py        # File filtering logic
│   ├── writer.py        # Output generation
│   └── exceptions.py    # Custom exceptions
├── tests/               # Test suite
├── main.py              # CLI entry point
├── setup.py             # Package setup
├── requirements.txt     # Dependencies
└── README.md           # This file
```

### Running Tests

```bash
pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Examples

### Example Output

The tool generates a simple text file with one file path per line:

```
src/main.py
src/utils/helpers.py
src/config/settings.py
tests/test_main.py
README.md
```

This format is ideal for ingestion by large language models for code analysis and generation tasks.
