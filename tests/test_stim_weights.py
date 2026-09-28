
# FILE: tests/test_stim_weights.py
from a3d.stim_adapter import graph_from_dem_text


def test_stim_weights_from_probabilities():
    dem = "error(0.2) D0 D1\n"
    g = graph_from_dem_text(dem)
    # weight should reflect negative log-odds of 0.2 (>0)
    assert any(e.weight > 0 for e in g.edges)
