
# FILE: tests/test_certificates_and_batch.py
from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout


def test_batch_and_certificate():
    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm")
    cfg.run_certificate = True
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    sX = [0]*len(rt.builder.node_order("X"))
    sZ = [0]*len(rt.builder.node_order("Z"))
    out = rt.decode_batch_from_syndromes_uniform([sX, sX], [sZ, sZ])
    assert len(out) == 2
    r0 = out[0][0]
    assert hasattr(r0, "avg_cost")
    # confidence injected
    assert hasattr(r0, "confidence")
