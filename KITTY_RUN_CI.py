#!/usr/bin/env python3
"""
KITTY_RUN_CI.py — one‑click local CI for Aegis
Double‑click me (Windows/Mac) or run `python KITTY_RUN_CI.py`.
Runs: ruff (lint), pytest (tests+coverage), build wheel.
All steps are optional; missing tools are skipped with a clear message.
"""

import os
import pathlib
import platform
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent

def run(cmd, name):
    print(f"\n=== {name} ===")
    print(" ", " ".join(cmd))
    try:
        p = subprocess.run(cmd, cwd=ROOT, check=False)
        print(f"--> exit code: {p.returncode}")
        return p.returncode
    except FileNotFoundError:
        print(f"[skip] {cmd[0]} not found")
        return 0

def main():
    py = sys.executable or "python3"
    codes = []
    # Ruff
    codes.append(run([py, "-m", "ruff", "check", "."], "Lint (ruff)"))
    # Pytest + coverage (best effort)
    codes.append(run([py, "-m", "pytest", "-q"], "Tests (pytest)"))
    # Build wheel
    codes.append(run([py, "-m", "pip", "install", "-U", "build"], "Ensure build is available"))
    codes.append(run([py, "-m", "build", "."], "Build (wheel + sdist)"))
    # Summary
    worst = max(codes) if codes else 0
    print("\n=== SUMMARY ===")
    print("Ruff:", codes[0] if codes else "n/a")
    print("Pytest:", codes[1] if len(codes)>1 else "n/a")
    print("Build:", codes[-1] if codes else "n/a")
    if worst != 0:
        print("Some steps failed (see logs above).")
    else:
        print("All runnable steps succeeded.")
    # Keep window open for double-click on Windows
    if platform.system() == "Windows" and not sys.stdout.isatty():
        os.system("pause")

if __name__ == "__main__":
    main()
