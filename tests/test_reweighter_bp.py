
# FILE: tests/test_reweighter_bp.py
from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout


def test_bp_reweighter_runs():
    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm")
    cfg.reweighter_type = "bp"
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    sX = [0]*len(rt.builder.node_order("X"))
    sZ = [0]*len(rt.builder.node_order("Z"))
    resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
    assert resX.avg_cost >= 0 and resZ.avg_cost >= 0
