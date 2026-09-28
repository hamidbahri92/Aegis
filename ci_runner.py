from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
STRICT_PATHS = [
    "a3d/decoder_mwpm.py",
    "a3d/decoder_mwpm_pm.py",
    "a3d/config.py",
    "aegis_qec",
    "bench/cli.py",
    "gui/app.py",
    "scripts/run_gui.py",
    "tests/test_cli.py",
    "tests/test_mwpm_sparse_blossom.py",
    "tests/test_public_namespace.py",
    "tests/test_decode_from_dem_optional.py",
]


def _run(cmd: list[str], name: str) -> int:
    print(f"\n=== {name} ===")
    print(" ", " ".join(cmd))
    try:
        process = subprocess.run(cmd, cwd=str(ROOT), check=False)
    except FileNotFoundError:
        print(f"Required command not found: {cmd[0]}")
        return 127
    print(f"--> exit code: {process.returncode}")
    return process.returncode


def main() -> int:
    python = sys.executable or "python3"
    checks = [
        _run(
            [python, "-m", "ruff", "check", "--select", "F,B", "."],
            "Repository defect lint",
        ),
        _run(
            [python, "-m", "ruff", "check", *STRICT_PATHS],
            "Strict Aegis QEC release-surface lint",
        ),
        _run([python, "-m", "pytest", "-q"], "Test suite"),
        _run([python, "-m", "build", "."], "Build wheel and source distribution"),
    ]

    print("\n=== Aegis QEC local CI summary ===")
    labels = ["defect lint", "strict lint", "tests", "package build"]
    for label, code in zip(labels, checks):
        print(f"{label}: {'PASS' if code == 0 else f'FAIL ({code})'}")

    return max(checks) if checks else 0


if __name__ == "__main__":
    raise SystemExit(main())
