# FILE: tests/test_metrics_logical_success.py
from a3d.graph import RotatedSurfaceLayout, DecodingGraphBuilder
from a3d.metrics import apply_correction_and_check_logical


def test_logical_success_proxy_no_edges_is_success_only_if_no_defects():
    lay = RotatedSurfaceLayout(3)
    b = DecodingGraphBuilder(lay, 3)
    orderX = b.node_order("X")
    orderZ = b.node_order("Z")
    gX = b.build("X",
                 {(c,t):1.0 for (c,t) in orderX},
                 {(c,t):1.0 for (c,t) in orderX if t<2},
                 {(c,t):0.0 for (c,t) in orderX if t<2})
    gZ = b.build("Z",
                 {(c,t):1.0 for (c,t) in orderZ},
                 {(c,t):1.0 for (c,t) in orderZ if t<2},
                 {(c,t):0.0 for (c,t) in orderZ if t<2})

    # no defects
    sX = [0]*len(gX.nodes)
    sZ = [0]*len(gZ.nodes)
    assert apply_correction_and_check_logical(lay, 3, gX, gZ, sX, sZ, [], [])

    # defects present but no corrections -> fail
    sX2 = sX[:]
    if len(sX2)>0:
        sX2[0] = 1
    assert not apply_correction_and_check_logical(lay, 3, gX, gZ, sX2, sZ, [], [])
