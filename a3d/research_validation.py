from __future__ import annotations

import random
import time
import warnings
from typing import Dict

from .config import AegisConfig
from .graph import RotatedSurfaceLayout
from .runtime import DecoderRuntime


def trial_decoder_smoke_rate(
    distance: int = 3,
    rounds: int = 3,
    decoder: str = "mwpm",
    p: float = 0.05,
    trials: int = 100,
) -> Dict[str, float]:
    """Run the historical synthetic decoder smoke test.

    This helper samples independent detector bits and counts an internal anomaly
    proxy based on non-empty syndromes returning non-positive average correction
    cost. It does not sample a quantum circuit, physical error chain, or logical
    observable and therefore is not a logical-error-rate estimator.
    """
    cfg = AegisConfig(distance=distance, rounds=rounds, decoder_type=decoder)
    layout = RotatedSurfaceLayout(cfg.distance)
    runtime = DecoderRuntime(cfg, layout)

    rng = random.Random(1234)
    n_x = len(runtime.builder.node_order("X"))
    n_z = len(runtime.builder.node_order("Z"))
    bad_x = 0
    bad_z = 0
    started = time.time()

    for _ in range(int(trials)):
        syndrome_x = [1 if rng.random() < p else 0 for _ in range(n_x)]
        syndrome_z = [1 if rng.random() < p else 0 for _ in range(n_z)]
        result_x, result_z = runtime.decode_from_syndromes_uniform(
            syndrome_x,
            syndrome_z,
            weight_space=1.0,
            weight_time=1.0,
            perase_time=0.0,
        )
        if sum(syndrome_x) > 0 and result_x.avg_cost <= 0:
            bad_x += 1
        if sum(syndrome_z) > 0 and result_z.avg_cost <= 0:
            bad_z += 1

    elapsed = time.time() - started
    return {
        "anomaly_rate_X": bad_x / max(1, trials),
        "anomaly_rate_Z": bad_z / max(1, trials),
        "sec": elapsed,
    }


def trial_error_rate(
    distance: int = 3,
    rounds: int = 3,
    decoder: str = "mwpm",
    p: float = 0.05,
    trials: int = 100,
) -> Dict[str, float]:
    """Compatibility wrapper for the historical, misleading function name."""
    warnings.warn(
        "trial_error_rate is a historical smoke-test name, not a logical-error "
        "rate estimator; use trial_decoder_smoke_rate instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    result = trial_decoder_smoke_rate(
        distance=distance,
        rounds=rounds,
        decoder=decoder,
        p=p,
        trials=trials,
    )
    return {
        "rate_X": result["anomaly_rate_X"],
        "rate_Z": result["anomaly_rate_Z"],
        "sec": result["sec"],
    }
