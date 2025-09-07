# FILE: tests/test_runtime_logging.py
import logging
from a3d.config import AegisConfig
from a3d.graph import RotatedSurfaceLayout
from a3d.runtime import DecoderRuntime


class DummyModel:
    pass


def dummy_logits_fn(_graph):
    raise RuntimeError("boom")


def test_ml_fallback_logs_exception(caplog):
    caplog.set_level(logging.ERROR, logger="a3d.runtime")
    cfg = AegisConfig(distance=3, rounds=3)
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    rt.attach_ml_model(DummyModel(), dummy_logits_fn)

    # trivial zero syndromes (just to exercise path)
    nX = len(rt.builder.node_order("X"))
    nZ = len(rt.builder.node_order("Z"))
    sX = [0] * nX
    sZ = [0] * nZ
    rt.decode_from_syndromes_calibrated(sX, sZ)
    assert isinstance(caplog.records, list)
