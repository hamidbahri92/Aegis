# FILE: a3d/decoder_bposd.py
from __future__ import annotations
from typing import List, Set, Tuple
from .graph import DecodingGraph, Edge
from .decoder_greedy import GreedyMatchingDecoder, DecodeResult


def _edge_key(e: Edge) -> Tuple[int, int, str]:
    a, b = (e.u, e.v) if e.u <= e.v else (e.v, e.u)
    return (a, b, e.etype)


class OSDDecoder:
    """
    (Naming note) This is a Greedy+OSD-style fallback, not full BP+OSD.
    Order-1 OSD fallback:
      1) Run greedy to get a baseline.
      2) Build a **local candidate pool** of low-cost edges incident to current defects.
      3) For each of top-K candidates, force-inclusion and re-solve; return best cost.
    """
    def __init__(self, primary_decoder: GreedyMatchingDecoder, osd_order: int = 1, k_candidates: int = 32):
        if osd_order < 0:
            raise ValueError("OSD order must be non-negative")
        self.primary_decoder = primary_decoder
        self.osd_order = int(osd_order)
        self.k_candidates = int(max(1, k_candidates))

    def decode(self, graph: DecodingGraph, syndromes: List[int]) -> DecodeResult:
        base = self.primary_decoder.decode(graph, syndromes)
        if self.osd_order == 0:
            return base

        syn = syndromes
        if len(syn) < len(graph.nodes):
            syn = syn + [0] * (len(graph.nodes) - len(syn))
        defects: Set[int] = {i for i, s in enumerate(syn) if (s % 2) == 1}

        used = {_edge_key(e) for e in base.corrections}

        def eff_cost(e: Edge) -> float:
            return self.primary_decoder._effective_cost(e)

        cands = []
        for e in graph.edges:
            if _edge_key(e) in used:
                continue
            if e.u in defects or e.v in defects:
                cands.append((eff_cost(e), e))
        cands.sort(key=lambda z: z[0])
        cands = [e for _, e in cands[: self.k_candidates]]

        solutions: List[DecodeResult] = [base]

        def is_boundary(nid: int) -> bool:
            return graph.node_meta.get(nid, ("", None, 0, ""))[3].startswith("boundary")

        for i in range(min(self.osd_order, len(cands))):
            e = cands[i]
            new_syn = list(syn)
            if not is_boundary(e.u):
                new_syn[e.u] ^= 1
            if not is_boundary(e.v):
                new_syn[e.v] ^= 1

            sub = self.primary_decoder.decode(graph, new_syn)
            total_cost = eff_cost(e) + sub.log_likelihood
            total_corr = [e] + sub.corrections
            avg_cost = total_cost / max(1, len(total_corr))
            solutions.append(DecodeResult(total_corr, total_cost, sub.matched_to_boundary, avg_cost))

        return min(solutions, key=lambda r: r.log_likelihood)
