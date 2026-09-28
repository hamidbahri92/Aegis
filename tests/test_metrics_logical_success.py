from a3d.graph import DecodingGraphBuilder, RotatedSurfaceLayout
from a3d.metrics import (
    apply_correction_and_check_logical,
    correction_chain_is_structurally_valid,
)


def _graphs():
    layout = RotatedSurfaceLayout(3)
    builder = DecodingGraphBuilder(layout, 3)
    order_x = builder.node_order("X")
    order_z = builder.node_order("Z")
    graph_x = builder.build(
        "X",
        {(coord, t): 1.0 for coord, t in order_x},
        {(coord, t): 1.0 for coord, t in order_x if t < 2},
        {(coord, t): 0.0 for coord, t in order_x if t < 2},
    )
    graph_z = builder.build(
        "Z",
        {(coord, t): 1.0 for coord, t in order_z},
        {(coord, t): 1.0 for coord, t in order_z if t < 2},
        {(coord, t): 0.0 for coord, t in order_z if t < 2},
    )
    return layout, graph_x, graph_z


def test_structural_validation_accepts_empty_syndrome_and_empty_correction():
    _layout, graph_x, graph_z = _graphs()
    syndrome_x = [0] * len(graph_x.nodes)
    syndrome_z = [0] * len(graph_z.nodes)

    assert correction_chain_is_structurally_valid(
        graph_x,
        graph_z,
        syndrome_x,
        syndrome_z,
        [],
        [],
    )


def test_structural_validation_rejects_unannihilated_defect():
    _layout, graph_x, graph_z = _graphs()
    syndrome_x = [0] * len(graph_x.nodes)
    syndrome_z = [0] * len(graph_z.nodes)
    syndrome_x[0] = 1

    assert not correction_chain_is_structurally_valid(
        graph_x,
        graph_z,
        syndrome_x,
        syndrome_z,
        [],
        [],
    )


def test_historical_logical_named_wrapper_is_only_a_compatibility_alias():
    layout, graph_x, graph_z = _graphs()
    syndrome_x = [0] * len(graph_x.nodes)
    syndrome_z = [0] * len(graph_z.nodes)

    modern = correction_chain_is_structurally_valid(
        graph_x,
        graph_z,
        syndrome_x,
        syndrome_z,
        [],
        [],
    )
    historical = apply_correction_and_check_logical(
        layout,
        3,
        graph_x,
        graph_z,
        syndrome_x,
        syndrome_z,
        [],
        [],
    )

    assert historical == modern
