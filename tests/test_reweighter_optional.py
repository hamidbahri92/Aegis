
# FILE: tests/test_reweighter_optional.py
from a3d.config import AegisConfig
from a3d.graph import RotatedSurfaceLayout
from a3d.runtime import DecoderRuntime


def test_transformer_reweighter_optional():
    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm")
    cfg.reweighter_type = "transformer"  # will be a no-op if torch absent
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    sX = [0]*len(rt.builder.node_order("X"))
    sZ = [0]*len(rt.builder.node_order("Z"))
    resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
    assert resX.avg_cost >= 0.0 and resZ.avg_cost >= 0.0
