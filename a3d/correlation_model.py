
# FILE: a3d/correlation_model.py
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .graph import DecodingGraph


@dataclass
class CorrelationParams:
    neighbor_bonus: float = 0.1
    boundary_penalty: float = 0.05
    time_space_bonus: float = 0.05

    @classmethod
    def from_json(cls, path: str) -> "CorrelationParams":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return cls(**d)

    def to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

def correlation_delta(graph: DecodingGraph, edge_index: int, p: CorrelationParams) -> float:
    e = graph.edges[edge_index]
    # Simple, interpretable potentials
    delta = 0.0
    if e.etype == "boundary":
        delta += p.boundary_penalty
    # Encourage time-space alternation around nodes
    # (Scan a small neighborhood to check if mixed types exist.)
    u, v = e.u, e.v
    has_mixed = False
    for j, ej in enumerate(graph.edges):
        if j == edge_index: continue
        if ej.u in (u, v) or ej.v in (u, v):
            if ej.etype != e.etype and ej.etype in ("time","space") and e.etype in ("time","space"):
                has_mixed = True; break
    if has_mixed:
        delta -= p.time_space_bonus
    # Neighbor bonus is applied upstream in MWPM corr decoder; keep function small
    return float(delta)
