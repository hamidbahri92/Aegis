
# FILE: tests/test_train_transformer_optional.py
import pathlib
import subprocess
import sys


def test_training_script_smoke():
    # run the training script as a module; skip gracefully if torch is missing
    code = subprocess.run([sys.executable, "-m", "scripts.train_transformer"], cwd=str(pathlib.Path(__file__).parents[1]), check=False).returncode
    assert code == 0
