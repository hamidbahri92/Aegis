# FILE: a3d/research_validation.py
from __future__ import annotations

import time
from typing import Dict

from .config import AegisConfig
from .graph import RotatedSurfaceLayout
from .runtime import DecoderRuntime


def trial_error_rate(distance: int=3, rounds: int=3, decoder: str="mwpm", p: float=0.05, trials: int=100) -> Dict[str, float]:
    """Run a minimal Monte‑Carlo with synthetic iid flips to estimate a rough logical error rate.
    This is deliberately light-weight (no external simulators) and meant for smoke‑tests / demos.
    Returns a dict with rates and timing. """
    cfg = AegisConfig(distance=distance, rounds=rounds, decoder_type=decoder)
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    import random
    random.seed(1234)
    nX = len(rt.builder.node_order("X"))
    nZ = len(rt.builder.node_order("Z"))
    badX = badZ = 0
    t0 = time.time()
    for _ in range(int(trials)):
        sX = [1 if random.random()<p else 0 for _ in range(nX)]
        sZ = [1 if random.random()<p else 0 for _ in range(nZ)]
        resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ, weight_space=1.0, weight_time=1.0, perase_time=0.0)
        # simple criterion: if average cost is zero but non-empty syndromes, count as bad (toy)
        if sum(sX)>0 and resX.avg_cost<=0: badX += 1
        if sum(sZ)>0 and resZ.avg_cost<=0: badZ += 1
    dt = time.time()-t0
    return {"rate_X": badX/max(1,trials), "rate_Z": badZ/max(1,trials), "sec": dt}
