
# FILE: tests/test_stim_adapter.py
from a3d.stim_adapter import graph_from_dem_text


def test_graph_from_dem_text_minimal():
    dem = """
# two detectors and an observable
error(0.01) D0 D1
error(0.02) D0 L0
"""
    g = graph_from_dem_text(dem)
    assert len(g.nodes) >= 3  # includes boundary
    assert any(e.etype=="space" for e in g.edges)
    assert any(e.etype=="boundary" for e in g.edges)
