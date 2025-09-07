from __future__ import annotations
from typing import List, Set
import networkx as nx

from .graph import DecodingGraph, Edge
from .decoder_greedy import DecodeResult


def _effective_cost(edge: Edge) -> float:
    pe = float(edge.p_erase)
    if pe >= 1.0:
        return 0.0
    pe = min(max(pe, 0.0), 0.999999)
    return edge.weight * (1.0 - pe)


def _is_boundary_node(graph: DecodingGraph, nid: int) -> bool:
    meta = graph.node_meta.get(nid)
    if meta and len(meta) >= 4:
        role = meta[3]
        return isinstance(role, str) and role.startswith("boundary")
    return False


class MWPMDecoder:
    """MWPM ??? ???? ???? ????? (???? ???? ???? ???? ?????).
    ????? ?? ?? ???? W - c ????? ?????? ? ?? max_weight_matching ?? maxcardinality=True ??????? ??????.
    """

    def decode(self, graph: DecodingGraph, syndromes: List[int]) -> DecodeResult:
        # ?? ???? ?????? ???? ?????? ???? (?? ???? ??????)
        if len(syndromes) < len(graph.nodes):
            syndromes = syndromes + [0] * (len(graph.nodes) - len(syndromes))
        elif len(syndromes) != len(graph.nodes):
            raise ValueError("Syndrome length mismatch with nodes")

        defects: Set[int] = {i for i, s in enumerate(syndromes) if (s % 2) == 1}
        if not defects:
            return DecodeResult([], 0.0, [], 0.0)

        G = nx.Graph()
        G.add_nodes_from(graph.nodes)

        costs = []
        for e in graph.edges:
            c = _effective_cost(e)
            costs.append(c)
            # ??????? ???? ?? ??? ??? ??? ???????
            G.add_edge(e.u, e.v, __orig=e, cost=c)

        if not costs:
            return DecodeResult([], 0.0, [], 0.0)

        W = max(costs)
        # ????? ????? ???? ??????????
        for u, v, data in G.edges(data=True):
            data["w"] = (W - data["cost"])

        matching = nx.algorithms.matching.max_weight_matching(
            G, maxcardinality=True, weight="w"
        )

        chosen_edges: List[Edge] = []
        total_cost = 0.0
        matched_to_boundary: List[int] = []

        for u, v in matching:
            e = G[u][v]["__orig"]
            # ??? ??????? ?? ????? ?? ??? ?? ????? ?????? ??? ?????
            if (u in defects) or (v in defects):
                chosen_edges.append(e)
                total_cost += _effective_cost(e)
                if _is_boundary_node(graph, u) and (v in defects):
                    matched_to_boundary.append(v)
                elif _is_boundary_node(graph, v) and (u in defects):
                    matched_to_boundary.append(u)

        pair_count = max(1, len(chosen_edges))
        avg_cost = total_cost / pair_count
        return DecodeResult(
            corrections=chosen_edges,
            log_likelihood=total_cost,
            matched_to_boundary=matched_to_boundary,
            avg_cost=avg_cost,
        )
