# Copyfiles

A standalone Python script that generates a `copyfiles.txt` file containing your project's source files and their contents. Perfect for sharing code context with LLMs or creating project snapshots.

## Features

- **Standalone script**: Drop `copyfiles.py` into any project and run
- **Smart filtering**: Respects `.gitignore` and excludes common build artifacts
- **Configurable**: Add custom ignore patterns via config file
- **Content inclusion**: Includes file contents (not just paths) for complete context
- **CLI interface**: Flexible command-line options for different workflows

## Installation

1. **Install the required dependency**:

   ```bash
   pip install pathspec
   ```

2. **Download the script**:

   ```bash
   # Option 1: Download directly
   curl -O https://raw.githubusercontent.com/your-repo/copyfiles/main/copyfiles.py

   # Option 2: Copy from another project
   cp /path/to/copyfiles.py .
   ```

3. **Place in your project root**:
   ```
   your-project/
   ├── copyfiles.py          # ← Place here
   ├── .gitignore
   ├── src/
   └── ...
   ```

## Quick Start

Generate a `copyfiles.txt` with default settings:

```bash
python copyfiles.py
```

This will:

- Scan your current directory
- Respect `.gitignore` patterns
- Exclude common build artifacts (`.env`, `node_modules/`, `__pycache__/`, etc.)
- Create `copyfiles.txt` with file paths and contents

## Usage

### Basic Usage

```bash
# Use current directory as root
python copyfiles.py

# Specify a different project root
python copyfiles.py --root /path/to/project

# Custom output file
python copyfiles.py --out my-project-files.txt
```

### Advanced Options

```bash
# Verbose output to see what's happening
python copyfiles.py --verbose

# Limit file size (default: 100KB)
python copyfiles.py --max-bytes 50000

# Use custom ignore patterns
python copyfiles.py --config .copyfiles-ignore

# Combine options
python copyfiles.py --root ./src --out context.txt --verbose --max-bytes 200000
```

### Command Line Options

| Option            | Description                                  | Default                 |
| ----------------- | -------------------------------------------- | ----------------------- |
| `--root`          | Project root directory                       | `.` (current directory) |
| `--out`           | Output file path                             | `copyfiles.txt`         |
| `--config`        | Path to file with additional ignore patterns | None                    |
| `--max-bytes`     | Maximum bytes per file to include            | `100000` (100KB)        |
| `--verbose`, `-v` | Verbose output                               | False                   |

## Configuration

### Default Exclusions

The script automatically excludes these patterns:

```python
DEFAULT_PATTERNS = [
    ".env",           # Environment files
    "node_modules/",  # Node.js dependencies
    "__pycache__/",   # Python cache
    "copyfiles.py",   # The script itself
]
```

### Custom Ignore Patterns

Create a `.copyfiles-ignore` file (or any name) with additional patterns:

```bash
# .copyfiles-ignore
*.log
dist/
build/
*.pyc
.DS_Store
```

Then use it:

```bash
python copyfiles.py --config .copyfiles-ignore
```

### .gitignore Integration

The script automatically reads and respects your project's `.gitignore` file. No additional configuration needed!

## Examples

### Example 1: Basic Project Context

```bash
# Generate context for a Python project
python copyfiles.py --verbose
```

Output:

```
[copyfiles] Scanning /path/to/project …
[copyfiles] 45 files found, 23 after filtering.
[copyfiles] Writing to /path/to/project/copyfiles.txt …
[copyfiles] Done. 23 files processed, 15678 bytes written.
```

### Example 2: Frontend Project

```bash
# Focus on source files only
python copyfiles.py --root ./src --out frontend-context.txt --verbose
```

### Example 3: Large Project with Custom Limits

```bash
# Handle large files with custom limits
python copyfiles.py --max-bytes 50000 --config .copyfiles-ignore
```

### Example 4: Multiple Configurations

```bash
# Different configs for different use cases
python copyfiles.py --config .copyfiles-dev.txt --out dev-context.txt
python copyfiles.py --config .copyfiles-prod.txt --out prod-context.txt
```

## Output Format

The generated `copyfiles.txt` contains:

```
# path/to/file.py
<file contents>

# another/file.js
<file contents>

# [truncated]
```

Each file is preceded by a header comment with the relative path, followed by the file contents.

## Use Cases

- **LLM Context**: Share complete project context with AI assistants
- **Code Reviews**: Generate project snapshots for review
- **Documentation**: Create comprehensive project documentation
- **Backup**: Quick project backup with full content
- **Onboarding**: Share project structure with new team members

## Troubleshooting

### Common Issues

**"Error: 'pathspec' library is required"**

```bash
pip install pathspec
```

**"No .gitignore found"**

- The script works without `.gitignore` but won't exclude gitignored files
- Create a `.gitignore` file in your project root

**"File too large"**

- Use `--max-bytes` to limit file size
- Large binary files are automatically skipped

**"Permission denied"**

- Ensure you have read permissions for the project directory
- Check file permissions on individual files

### Verbose Mode

Use `--verbose` to see detailed information about what the script is doing:

```bash
python copyfiles.py --verbose
```

This will show:

- Number of files found vs. filtered
- Which files are being skipped and why
- Progress during file writing

## Contributing

This is a standalone script designed to be simple and portable. To modify:

1. Edit the `DEFAULT_PATTERNS` list at the top of `copyfiles.py`
2. Add new functionality to the existing functions
3. Test with `--verbose` to ensure changes work as expected

## License

This script is provided as-is for educational and practical use. Feel free to modify and distribute as needed.
