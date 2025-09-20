# FILE: scripts/run_gui.py
from __future__ import annotations

import pathlib
import subprocess
import sys


def main():
    app = pathlib.Path(__file__).parents[1]/"gui"/"app.py"
    try:
        return subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], check=False).returncode
    except FileNotFoundError:
        print("Streamlit is not installed. `pip install streamlit` and retry.")
        return 0
if __name__ == "__main__":
    raise SystemExit(main())
