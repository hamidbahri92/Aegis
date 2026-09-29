
# FILE: tests/test_stim_adapter_full.py
from a3d.stim_adapter import graph_from_dem_text_approximate


def test_approximate_dem_shift_grouping_and_edges():
    dem = """
# legacy group 0
error(0.01) D0 D1
error(0.02) D1 L0
shift_detectors 1
# next legacy group
error(0.01) D0 D1
"""
    g = graph_from_dem_text_approximate(dem)
    # Expect nodes for D0,D1 at t0 and t1 plus boundaries
    ts = [meta[2] for _, meta in g.node_meta.items()]
    assert 0 in ts and 1 in ts
    # Expect at least one boundary edge and one space edge
    assert any(e.etype=="boundary" for e in g.edges)
    assert any(e.etype=="space" for e in g.edges)
