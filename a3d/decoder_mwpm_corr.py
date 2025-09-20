
# FILE: a3d/decoder_mwpm_corr.py
from __future__ import annotations

from .correlation_model import CorrelationParams, correlation_delta
from .decoder_greedy import DecodeResult
from .decoder_mwpm import MWPMDecoder
from .graph import DecodingGraph
from .stats import effective_cost_from_edge


def _build_adjacency(graph: DecodingGraph):
    adj = {i: set() for i in range(len(graph.nodes))}
    for e in graph.edges:
        adj[e.u].add(e.v); adj[e.v].add(e.u)
    return adj

def _motif_score(graph: DecodingGraph, edge_index: int, adj) -> float:
    """Compute a local motif-based adjustment:
    - Encourage time-space sequences (time followed by space) around shared nodes.
    - Mildly discourage boundary chains of length >2.
    Returns a signed delta to be added to base cost (negative => cheaper).
    """
    e = graph.edges[edge_index]
    u, v = e.u, e.v
    typ = e.etype
    score = 0.0
    # time-space encouragement
    if typ in ("time","space"):
        for w in adj[u] | adj[v]:
            if w == u or w == v:
                continue
            # look for a neighbor edge type different than current one
            for j, ej in enumerate(graph.edges):
                if (ej.u==u and ej.v==w) or (ej.u==v and ej.v==w):
                    if ej.etype != typ and ej.etype in ("time","space"):
                        score -= 0.05  # encourage mixed motifs
                        break
    # boundary discouragement for long chains
    if typ == "boundary":
        score += 0.03
    return score

class CorrelationMWPMDecoder:
    """Correlation-aware MWPM: adjusts edge costs using local motif statistics, then runs MWPM."""
    def __init__(self, alpha: float = 1.0):
        self.base = MWPMDecoder()
        self.alpha = float(alpha)

    def decode(self, graph: DecodingGraph, syndromes) -> DecodeResult:
        adj = _build_adjacency(graph)
        costs = [effective_cost_from_edge(e) for e in graph.edges]
        # Load correlation params if attached
        params = getattr(self, "_corr_params", None)
        if isinstance(params, CorrelationParams):
            deltas = [self.alpha * (correlation_delta(graph, i, params)) for i in range(len(graph.edges))]
        else:
            deltas = [self.alpha * _motif_score(graph, i, adj) for i in range(len(graph.edges))]
        # Apply costs in-place
        for e, base, d in zip(graph.edges, costs, deltas):
            new_c = max(1e-6, base + d)
            object.__setattr__(e, "weight", float(new_c))
        # Run MWPM
        return self.base.decode(graph, syndromes)
