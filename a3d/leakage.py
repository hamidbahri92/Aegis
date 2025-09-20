# FILE: a3d/leakage.py
from __future__ import annotations

from typing import List

from .graph import DecodingGraph, Edge


def apply_leakage_pregrowth(graph: DecodingGraph, leakage_flags: List[int]) -> List[Edge]:
    leaked = {i for i,f in enumerate(leakage_flags[:len(graph.nodes)]) if int(f)==1}
    chosen = []
    if not leaked: return chosen
    for e in graph.edges:
        if e.etype == "boundary" and (e.u in leaked or e.v in leaked):
            chosen.append(e)
    return chosen
