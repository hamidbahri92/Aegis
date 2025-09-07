# FILE: tests/test_pipeline_integration.py
import numpy as np
from a3d.graph import RotatedSurfaceLayout
from a3d.runtime import DecoderRuntime
from a3d.config import AegisConfig
from a3d.noise_physical import generate_pauli_errors, syndromes_from_pauli_errors


def test_end_to_end_uniform_runtime():
    cfg = AegisConfig(distance=3, rounds=4)
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)

    rng = np.random.default_rng(123)
    errs = generate_pauli_errors(lay, cfg.rounds, 1e-3, rng)
    sX, sZ = syndromes_from_pauli_errors(lay, cfg.rounds, errs)

    resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
    assert resX.log_likelihood >= 0.0
    assert resZ.log_likelihood >= 0.0
