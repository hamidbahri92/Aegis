
from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout


def test_decode_from_dem_text_runs():
    cfg = AegisConfig(distance=3, rounds=3, decoder_type="mwpm")
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    dem = "error(0.01) D0 D1\n"
    resX, resZ = rt.decode_from_dem_text(dem)
    assert hasattr(resX, "avg_cost") and hasattr(resZ, "avg_cost")
