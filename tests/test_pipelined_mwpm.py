
# FILE: tests/test_pipelined_mwpm.py
from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout


def test_mwpm2_runs():
    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm2")
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    sX = [0]*len(rt.builder.node_order("X"))
    sZ = [0]*len(rt.builder.node_order("Z"))
    resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
    assert resX.avg_cost >= 0 and resZ.avg_cost >= 0
