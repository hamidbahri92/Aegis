# FILE: tests/test_sweep_reuse.py
from a3d.sweep import sweep_physical_p


def test_sweep_prebuilt_graphs_reuse():
    distances = [3]
    rounds = 3
    p_values = [1e-3, 5e-3]
    trials = 3
    rows = sweep_physical_p(distances, rounds, p_values, trials, seed=1)
    assert len(rows) == len(distances) * len(p_values) * trials
    assert all("success" in r and "p" in r for r in rows)
