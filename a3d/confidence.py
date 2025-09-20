
# FILE: a3d/confidence.py
from __future__ import annotations

import math


def confidence_from_cost(avg_cost: float, edges: int) -> float:
    """Map average edge cost to a [0,1] confidence.
    Lower avg_cost and more edges (consistent corrections) -> higher confidence.
    """
    avg_cost = float(max(1e-6, avg_cost))
    # damp by edge count; cap exponent to avoid overflow
    score = -avg_cost / max(1, edges)
    # logistic mapping
    return 1.0 / (1.0 + math.exp(-score))
