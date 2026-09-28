from __future__ import annotations

from a3d.decoder_mwpm import MWPMDecoder
from a3d.graph import DecodingGraph, Edge


def test_mwpm_backend_is_sparse_blossom():
    assert MWPMDecoder.backend == "pymatching-sparse-blossom"


def test_mwpm_returns_path_edges_between_defects():
    graph = DecodingGraph(
        nodes=[0, 1, 2],
        edges=[
            Edge(0, 1, 2.0, "space"),
            Edge(1, 2, 2.0, "space"),
        ],
        node_meta={
            0: ("X", None, 0, "stab"),
            1: ("X", None, 0, "stab"),
            2: ("X", None, 0, "stab"),
        },
    )
    result = MWPMDecoder().decode(graph, [1, 0, 1])
    assert result.corrections == graph.edges
    assert result.matched_to_boundary == []


def test_mwpm_maps_virtual_boundary_back_to_aegis_edge():
    boundary = 2
    graph = DecodingGraph(
        nodes=[0, 1, boundary],
        edges=[
            Edge(0, 1, 5.0, "space"),
            Edge(0, boundary, 1.0, "boundary"),
        ],
        node_meta={
            0: ("X", None, 0, "stab"),
            1: ("X", None, 0, "stab"),
            boundary: ("X", None, 0, "boundary-H-W"),
        },
    )
    result = MWPMDecoder().decode(graph, [1, 0])
    assert result.corrections == [graph.edges[1]]
    assert result.matched_to_boundary == [0]


def test_batch_reuses_sparse_blossom_graph_and_preserves_results():
    graph = DecodingGraph(
        nodes=[0, 1, 2],
        edges=[
            Edge(0, 1, 2.0, "space"),
            Edge(1, 2, 2.0, "space"),
        ],
        node_meta={
            0: ("X", None, 0, "stab"),
            1: ("X", None, 0, "stab"),
            2: ("X", None, 0, "stab"),
        },
    )
    decoder = MWPMDecoder()
    results = decoder.decode_batch(graph, [[1, 0, 1], [0, 0, 0]])
    assert results[0].corrections == graph.edges
    assert results[1].corrections == []
