# FILE: tests/test_homology_exact.py
from a3d.graph import DecodingGraphBuilder, RotatedSurfaceLayout
from a3d.metrics import _correction_spans_opposite_boundaries


def _find_node_ids_by_role(graph, prefix):
    return [
        nid
        for nid, (_s, _c, _t, role) in graph.node_meta.items()
        if role.startswith(prefix)
    ]


def _first_space_edge_between(graph, u, v):
    for e in graph.edges:
        if e.etype == "space" and ((e.u == u and e.v == v) or (e.u == v and e.v == u)):
            return e
    return None


def _first_boundary_edge_from(graph, u, boundary_prefix):
    for e in graph.edges:
        if e.etype == "boundary":
            if graph.node_meta[e.u][3].startswith(boundary_prefix) and e.v == u:
                return e
            if graph.node_meta[e.v][3].startswith(boundary_prefix) and e.u == u:
                return e
    return None


def test_correction_chain_detects_horizontal_boundary_span():
    d = 3
    T = 1
    lay = RotatedSurfaceLayout(d)
    b = DecodingGraphBuilder(lay, T)

    orderX = b.node_order("X")
    gX = b.build(
        "X",
        {(c, t): 1.0 for (c, t) in orderX},
        {(c, t): 1.0 for (c, t) in orderX if t < T - 1},
        {(c, t): 0.0 for (c, t) in orderX if t < T - 1},
    )

    # Pick three X stabilizers forming a diagonal chain across columns: (0,0)->(1,1)->(2,2)
    # Then connect endpoints to Left and Right boundaries respectively.
    # This yields a correction component touching both H-W and H-E in the same time slice.
    stab_nodes = [
        nid
        for nid, (sec, coord, t, role) in gX.node_meta.items()
        if role == "stab" and t == 0 and coord in [(0, 0), (1, 1), (2, 2)]
    ]
    stab_nodes.sort(key=lambda n: gX.node_meta[n][1])

    e01 = _first_space_edge_between(gX, stab_nodes[0], stab_nodes[1])
    e12 = _first_space_edge_between(gX, stab_nodes[1], stab_nodes[2])
    assert e01 is not None and e12 is not None

    # boundary edges
    eL = _first_boundary_edge_from(gX, stab_nodes[0], "boundary-H-W")
    eR = _first_boundary_edge_from(gX, stab_nodes[2], "boundary-H-E")
    assert eL is not None and eR is not None

    horiz_span, vert_span = _correction_spans_opposite_boundaries(
        gX, [e01, e12, eL, eR]
    )
    assert horiz_span is True
    assert vert_span is False


def test_correction_chain_single_boundary_is_not_a_span():
    d = 3
    T = 1
    lay = RotatedSurfaceLayout(d)
    b = DecodingGraphBuilder(lay, T)

    orderX = b.node_order("X")
    gX = b.build(
        "X",
        {(c, t): 1.0 for (c, t) in orderX},
        {(c, t): 1.0 for (c, t) in orderX if t < T - 1},
        {(c, t): 0.0 for (c, t) in orderX if t < T - 1},
    )

    # Connect a single stabilizer to only the left boundary; should not create a span.
    single = [
        nid
        for nid, (sec, coord, t, role) in gX.node_meta.items()
        if role == "stab" and t == 0 and gX.node_meta[nid][1] == (0, 0)
    ][0]
    eL = _first_boundary_edge_from(gX, single, "boundary-H-W")
    assert eL is not None

    horiz_span, vert_span = _correction_spans_opposite_boundaries(gX, [eL])
    assert not horiz_span and not vert_span
