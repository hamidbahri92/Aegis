# FILE: a3d/sweep.py
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from .graph import DecodingGraphBuilder, RotatedSurfaceLayout
from .metrics import build_graphs_for_p, run_trial_with_graphs


def sweep_physical_p(
    distances: List[int], rounds: int, p_values: List[float], trials: int, seed: int
) -> List[Dict[str, Any]]:
    """
    Deterministic sweep over distances × p × trials.
    Reuses a single builder/layout per (distance, rounds) and prebuilt graphs per p.
    """
    rows: List[Dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for d in distances:
        layout = RotatedSurfaceLayout(d)
        builder = DecodingGraphBuilder(layout, rounds, diagonal_adjacency=True)
        for p in p_values:
            gX, gZ = build_graphs_for_p(builder, float(p))
            seeds = rng.integers(0, 2**31 - 1, size=trials, endpoint=False)
            for s in seeds:
                rows.append(
                    run_trial_with_graphs(
                        builder, layout, gX, gZ, float(p), int(s), crossmodal=False
                    )
                )
    return rows
