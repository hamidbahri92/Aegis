# FILE: ci_runner.py
from __future__ import annotations

import pathlib
import platform
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent

def _run(cmd, name):
    print(f"=== {name} ===")
    print(" ", " ".join(cmd))
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), check=False)
        print(f"--> exit code: {p.returncode}")
        return p.returncode
    except FileNotFoundError:
        print(f"[skip] {cmd[0]} not found")
        return 0

def main():
    py = sys.executable or "python3"
    codes = []
    codes.append(_run([py, "-m", "ruff", "check", "."], "Lint (ruff)"))
    codes.append(_run([py, "-m", "pytest", "-q"], "Tests (pytest)"))
    codes.append(_run([py, "-m", "pip", "install", "-U", "build"], "Ensure build is available"))
    codes.append(_run([py, "-m", "build", "."], "Build (wheel + sdist)"))
    worst = max(codes) if codes else 0
    print("SUMMARY:", codes)
    if platform.system()=="Windows" and not sys.stdout.isatty():
        import os; os.system("pause")
    return worst

if __name__ == "__main__":
    raise SystemExit(main())
