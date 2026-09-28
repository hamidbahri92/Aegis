
# FILE: a3d/decoder_mwpm_pipeline.py
from __future__ import annotations

from typing import Dict, List

from .decoder_greedy import DecodeResult
from .decoder_mwpm import MWPMDecoder
from .graph import DecodingGraph, Edge
from .stats import effective_cost_from_edge


def _local_correlation_boost(graph: DecodingGraph, matched: List[Edge]) -> Dict[int, float]:
    """Return per-edge adjustments based on proximity to already-matched edges.
    Heuristic: reduce cost slightly for edges that share a node with matched ones (encourage consistent pairing).
    """
    adj = {i: 0.0 for i in range(len(graph.edges))}
    touched = set()
    for e in matched:
        touched.add(e.u); touched.add(e.v)
    for i, e in enumerate(graph.edges):
        if e.u in touched or e.v in touched:
            adj[i] -= 0.15  # lower cost (i.e., more likely) near touched nodes
    return adj

class PipelinedMWPMDecoder:
    """Two-stage MWPM: run MWPM, reweight locally by correlation, run MWPM again."""
    def __init__(self):
        self.base = MWPMDecoder()

    def decode(self, graph: DecodingGraph, syndromes) -> DecodeResult:
        # Pass 1
        r1 = self.base.decode(graph, syndromes)
        # Compute adjustments
        adj = _local_correlation_boost(graph, r1.corrections)
        # Apply adjusted costs (in-place)
        new_edges = []
        for i, e in enumerate(graph.edges):
            base = effective_cost_from_edge(e)
            new_c = max(1e-6, base + adj[i])
            object.__setattr__(e, "weight", float(new_c))
            new_edges.append(e)
        # Pass 2
        r2 = self.base.decode(graph, syndromes)
        # Choose the better (lower log_likelihood; break ties by avg_cost)
        if (r2.log_likelihood < r1.log_likelihood) or (r2.log_likelihood == r1.log_likelihood and r2.avg_cost <= r1.avg_cost):
            return r2
        return r1
