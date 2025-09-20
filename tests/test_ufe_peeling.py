
# FILE: tests/test_ufe_peeling.py
from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout


def test_uf_peeling_runs():
    cfg = AegisConfig(distance=3, rounds=4, decoder_type="uf")
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    sX = [0]*len(rt.builder.node_order("X"))
    sZ = [0]*len(rt.builder.node_order("Z"))
    resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ, perase_time=0.9)  # strong erasures
    assert resX.avg_cost >= 0 and resZ.avg_cost >= 0
