
import pathlib
import subprocess
import sys


def test_bench_cli_sweep_tmp(tmp_path):
    root = pathlib.Path(__file__).parents[1]
    out = tmp_path / "sweep.csv"
    code = subprocess.run([sys.executable, "-m", "bench.cli", "sweep", "--decoder", "mwpm", "--p", "0.02", "0.06", "--trials", "5", "--out", str(out)], cwd=str(root), check=False).returncode
    assert code == 0 and out.exists()
