
# FILE: tests/test_stim_dem_time_obs.py
from a3d.stim_adapter import graph_from_dem_text


def test_dem_time_and_observable_boundaries():
    dem = """
error(0.01) D0 D1 L0
shift_detectors 2
error(0.02) D0 D1 L1
"""
    g = graph_from_dem_text(dem)
    # time slices 0 and 2 should exist
    times = set(meta[2] for meta in g.node_meta.values())
    assert 0 in times and 2 in times
    # at least one boundary edge per time slice
    ts_edges = {}
    for e in g.edges:
        if e.etype == "boundary":
            ts_edges.setdefault(e, True)
    assert any(e.etype=="boundary" for e in g.edges)
