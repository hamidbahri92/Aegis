# FILE: a3d/stats.py
from __future__ import annotations

import math

from .graph import Edge


def logodds_from_p(p: float) -> float:
    """Return -log(p/(1-p)) with guards; larger -> rarer error."""
    p = float(p)
    p = max(min(p, 1.0 - 1e-12), 1e-12)
    return -math.log(p / (1.0 - p))

def p_from_logodds(w: float) -> float:
    """Inverse of logodds_from_p."""
    # w = -log(p/(1-p)) => p = 1/(1+e^w)
    return 1.0 / (1.0 + math.exp(w))

def combine_error_with_erasure(p_err: float, p_erase: float) -> float:
    """Assume erasure makes an error 'active' with probability p_erase.
    Combine as: p_comb = 1 - (1 - p_err)*(1 - p_erase)."""
    p_err = max(min(float(p_err), 1.0 - 1e-12), 1e-12)
    p_erase = max(min(float(p_erase), 1.0 - 1e-12), 0.0)
    return 1.0 - (1.0 - p_err) * (1.0 - p_erase)

def effective_cost_from_edge(edge: Edge) -> float:
    """Turn an Edge(weight=log-odds, p_erase) into a **negative log-odds** cost
    after fusing erasures probabilistically.
    weight stores w = -log(p/(1-p)). Recover p, fuse with p_erase, return -log(p/(1-p))."""
    p = p_from_logodds(float(edge.weight))
    p_comb = combine_error_with_erasure(p, float(edge.p_erase))
    # Convert back to log-odds
    p_comb = max(min(p_comb, 1.0 - 1e-12), 1e-12)
    return -math.log(p_comb / (1.0 - p_comb))
