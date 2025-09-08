# FILE: tests/test_runtime_mwpm.py
import numpy as np

from a3d.config import AegisConfig
from a3d.graph import RotatedSurfaceLayout
from a3d.noise_physical import generate_pauli_errors, syndromes_from_pauli_errors
from a3d.runtime import DecoderRuntime


def test_mwpm_decoder_smoke():
    cfg = AegisConfig(distance=3, rounds=4, decoder_type="mwpm")
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)

    rng = np.random.default_rng(123)
    errs = generate_pauli_errors(lay, cfg.rounds, 1e-3, rng)
    sX, sZ = syndromes_from_pauli_errors(lay, cfg.rounds, errs)

    resX, resZ = rt.decode_from_syndromes_calibrated(sX, sZ)
    assert resX.log_likelihood >= 0.0
    assert resZ.log_likelihood >= 0.0
