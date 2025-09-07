# FILE: a3d/decoder_ml.py
from __future__ import annotations
from typing import List
import numpy as np

try:
    import torch
    TORCH_OK = True
except Exception:
    TORCH_OK = False

from .graph import HyperDecodingGraph, Edge
from .decoder_greedy import DecodeResult


def decode_with_gnn(graph: HyperDecodingGraph, logits, threshold: float = 0.5) -> DecodeResult:
    """
    Convert (edge) logits → probabilities and greedily select non-overlapping edges
    with prob > threshold. Heuristic early stop to avoid scanning entire set.
    """
    if not TORCH_OK or logits is None or len(graph.edges) == 0:
        return DecodeResult(corrections=[], log_likelihood=0.0, matched_to_boundary=[], avg_cost=0.0)

    if isinstance(logits, np.ndarray):
        probs = 1.0 / (1.0 + np.exp(-logits))
    else:
        with torch.no_grad():
            probs = torch.sigmoid(logits).cpu().numpy()

    edge_scores = [(float(probs[i]), i, graph.edges[i]) for i in range(len(graph.edges))]
    edge_scores.sort(reverse=True)

    selected_edges: List[Edge] = []
    matched_nodes = set()
    total_cost = 0.0

    limit = max(1, len(graph.edges) // 4)  # heuristic cap

    for prob, idx, edge in edge_scores:
        if prob <= threshold:
            break
        if edge.u in matched_nodes or edge.v in matched_nodes:
            continue
        selected_edges.append(edge)
        matched_nodes.add(edge.u)
        matched_nodes.add(edge.v)
        total_cost += -np.log(max(prob, 1e-10))
        if len(selected_edges) >= limit:
            break

    avg_cost = total_cost / max(1, len(selected_edges))
    return DecodeResult(selected_edges, total_cost, [], avg_cost)
