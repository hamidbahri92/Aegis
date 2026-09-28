
from a3d.dem_export import graph_to_dem_text
from a3d.graph import DecodingGraph, Edge


def test_dem_exporter_smoke():
    g = DecodingGraph(nodes=[0,1,2], edges=[Edge(0,1,1.0,"space",0.0), Edge(1,2,1.0,"boundary",0.0)], node_meta={})
    txt = graph_to_dem_text(g)
    assert "error(" in txt and "D0 D1" in txt and "L0" in txt
