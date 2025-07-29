"""Smoke-tests for the copyfiles CLI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # project root
SRC_DIR = ROOT / "src"
FIXTURES = Path(__file__).parent / "data" / "simple_proj"


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke `python -m copyfiles.cli …` with PYTHONPATH pointing at src/."""
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{SRC_DIR}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return subprocess.run(
        [sys.executable, "-m", "copyfiles.cli", *args],
        cwd=cwd or ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_flag() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_version_flag() -> None:
    result = _run_cli("--version")
    assert result.returncode == 0
    assert "copyfiles" in (result.stdout + result.stderr)


def test_generate_output_file(tmp_path: Path) -> None:
    out_file = tmp_path / "copyfiles.txt"
    result = _run_cli("--root", str(FIXTURES), "--out", str(out_file))
    assert result.returncode == 0
    assert out_file.exists()
    txt = out_file.read_text()
    assert "app.py" in txt and "ignored.log" not in txt
