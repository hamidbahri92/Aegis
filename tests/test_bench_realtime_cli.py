
import pathlib
import subprocess
import sys


def test_bench_realtime_cli(tmp_path):
    root = pathlib.Path(__file__).parents[1]
    out = tmp_path/"rt.csv"
    code = subprocess.run([sys.executable, "-m", "bench.cli", "realtime", "--steps", "20", "--out", str(out)], cwd=str(root), check=False).returncode
    assert code == 0 and out.exists()
