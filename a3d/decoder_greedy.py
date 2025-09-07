from __future__ import annotations
from dataclasses import dataclass
from typing import List, Set, Tuple
import heapq

from .graph import DecodingGraph, Edge


@dataclass
class DecodeResult:
    corrections: List[Edge]
    log_likelihood: float
    matched_to_boundary: List[int]
    avg_cost: float


class GreedyMatchingDecoder:
    @staticmethod
    def _defects(syndromes: List[int]) -> Set[int]:
        return {i for i, s in enumerate(syndromes) if (s % 2) == 1}

    @staticmethod
    def _effective_cost(edge: Edge) -> float:
        pe = float(edge.p_erase)
        if pe >= 1.0:
            return 0.0
        pe = min(max(pe, 0.0), 0.999999)
        return edge.weight * (1.0 - pe)

    @staticmethod
    def _is_boundary_node(graph: DecodingGraph, nid: int) -> bool:
        role = graph.node_meta.get(nid, ("", None, 0, ""))[3]
        return role.startswith("boundary")

    def decode(self, graph: DecodingGraph, syndromes: List[int]) -> DecodeResult:
        if len(syndromes) < len(graph.nodes):
            syndromes = syndromes + [0] * (len(graph.nodes) - len(syndromes))
        elif len(syndromes) != len(graph.nodes):
            raise ValueError("Syndrome length mismatch with nodes")

        defects = self._defects(syndromes)
        if not defects:
            return DecodeResult([], 0.0, [], 0.0)

        edge_heap: List[Tuple[float, int, Edge]] = [
            (self._effective_cost(e), idx, e) for idx, e in enumerate(graph.edges)
        ]
        heapq.heapify(edge_heap)

        matched: Set[int] = set()
        chosen: List[Edge] = []
        to_boundary: List[int] = []
        total_cost = 0.0

        while edge_heap and (len(matched) < len(defects)):
            cost, _idx, edge = heapq.heappop(edge_heap)
            u, v = edge.u, edge.v
            u_is_b = self._is_boundary_node(graph, u)
            v_is_b = self._is_boundary_node(graph, v)

            if not u_is_b and not v_is_b:
                if (u in defects and v in defects) and (u not in matched) and (v not in matched):
                    chosen.append(edge)
                    matched.add(u); matched.add(v)
                    total_cost += cost
            else:
                s = v if u_is_b else u
                if (s in defects) and (s not in matched):
                    chosen.append(edge)
                    matched.add(s)
                    to_boundary.append(s)
                    total_cost += cost

        pair_count = max(1, len(chosen))
        avg_cost = total_cost / pair_count

        return DecodeResult(
            corrections=chosen,
            log_likelihood=total_cost,
            matched_to_boundary=to_boundary,
            avg_cost=avg_cost,
        )
