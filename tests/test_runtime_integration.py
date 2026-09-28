# FILE: tests/test_runtime_integration.py
from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout


def test_basic_runtime_smoketest():
    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm")
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    sX = [0]*len(rt.builder.node_order("X"))
    sZ = [0]*len(rt.builder.node_order("Z"))
    resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
    assert resX.avg_cost >= 0 and resZ.avg_cost >= 0
