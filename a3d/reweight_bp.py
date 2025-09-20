
# FILE: a3d/reweight_bp.py
from __future__ import annotations

from typing import Dict, List

from .graph import DecodingGraph
from .stats import effective_cost_from_edge


class BeliefPropagationReweighter:
    """Loopy BP (min-sum flavor) on the edge adjacency graph to refine edge costs.

    We construct an "edge graph" where nodes are decoding edges and two nodes connect
    if original edges share a decoding node. Messages flow for K iterations, nudging
    costs to be more self-consistent (favoring coherent local structures).

    This is a principled generalization over ad-hoc motif tweaks and remains Torch-free.
    """

    def __init__(self, iters: int = 5, lam: float = 0.2, damp: float = 0.5):
        self.iters = int(iters)
        self.lam = float(lam)      # influence of neighbor messages
        self.damp = float(damp)    # damping for stability

    def _edge_adjacency(self, g: DecodingGraph) -> List[List[int]]:
        E = len(g.edges)
        adj = [[] for _ in range(E)]
        # index edges by incident nodes
        idx_by_node: Dict[int, List[int]] = {}
        for ei, e in enumerate(g.edges):
            idx_by_node.setdefault(e.u, []).append(ei)
            idx_by_node.setdefault(e.v, []).append(ei)
        for lst in idx_by_node.values():
            for i in range(len(lst)):
                ei = lst[i]
                for j in range(i+1, len(lst)):
                    ej = lst[j]
                    adj[ei].append(ej)
                    adj[ej].append(ei)
        return adj

    def reweight(self, g: DecodingGraph) -> List[float]:
        E = len(g.edges)
        base = [effective_cost_from_edge(e) for e in g.edges]
        if E == 0:
            return base
        adj = self._edge_adjacency(g)
        # initialize messages to zero
        msg = [0.0]*E
        for _ in range(max(1, self.iters)):
            new = [0.0]*E
            for i in range(E):
                # min-sum: push cost down when neighbors are strongly supportive
                neigh = adj[i]
                support = 0.0
                for j in neigh:
                    # consider relative base costs; lower neighbor cost gives support
                    support += max(0.0, (max(base) - base[j])) / (1.0 + len(adj[j]))
                # normalized and scaled
                new[i] = (1.0 - self.damp)*msg[i] + self.damp * (self.lam * support / (1.0 + len(neigh)))
            msg = new
        # apply messages as negative deltas on costs (cheaper if supported)
        out = []
        for i, e in enumerate(g.edges):
            c = max(1e-6, base[i] - msg[i])
            out.append(c)
        return out
