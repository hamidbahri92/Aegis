
import json
import pathlib
import subprocess
import sys


def test_latency_file_created(tmp_path):
    root = pathlib.Path(__file__).parents[1]
    out_csv = tmp_path/"sweep.csv"
    lat_csv = tmp_path/"lat.csv"
    code = subprocess.run([sys.executable, "-m", "bench.cli", "sweep", "--decoder", "mwpm", "--p", "0.02", "0.06", "--trials", "5", "--out", str(out_csv), "--latency-out", str(lat_csv)], cwd=str(root), check=False).returncode
    assert code == 0 and out_csv.exists() and lat_csv.exists()

def test_tuner_writes_json(tmp_path):
    root = pathlib.Path(__file__).parents[1]
    out = tmp_path/"corr.json"
    code = subprocess.run([sys.executable, "-m", "scripts.tune_correlations", "--trials", "3", "--out", str(out)], cwd=str(root), check=False).returncode
    assert code == 0 and out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "neighbor_bonus" in data
