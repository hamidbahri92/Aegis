from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys


def main() -> int:
    if importlib.util.find_spec("streamlit") is None:
        print("Aegis QEC GUI is not installed.")
        print("Install it with: python -m pip install -U 'aegis-qec[gui]'")
        return 2

    app = pathlib.Path(__file__).parents[1] / "gui" / "app.py"
    return subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app)],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
