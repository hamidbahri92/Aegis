# FILE: a3d/crossmodal_learner.py
from __future__ import annotations

from typing import List


# Minimal, optional ML hook. Provide a function f(graph)->List[float] of per-edge logits.
# This keeps Torch optional and unblocks end-to-end wiring.
def default_edge_logit_fn(graph) -> List[float]:
    # Neutral logits (0.0) => probability 0.5 per edge (does not change weights)
    return [0.0 for _ in graph.edges]

__all__ = ["default_edge_logit_fn"]
