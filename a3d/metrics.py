# FILE: a3d/metrics.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np

from .decoder_bposd import OSDDecoder
from .decoder_greedy import GreedyMatchingDecoder
from .graph import DecodingGraph, DecodingGraphBuilder, Edge, RotatedSurfaceLayout
from .noise_physical import generate_pauli_errors, syndromes_from_pauli_errors


def _pad_syndrome(s: List[int], graph: DecodingGraph) -> List[int]:
    if len(s) < len(graph.nodes):
        return s + [0] * (len(graph.nodes) - len(s))
    return s


def _apply_corrections_to_syndrome(
    graph: DecodingGraph, syndromes: List[int], chosen_edges: List[Edge]
) -> List[int]:
    s = _pad_syndrome(syndromes[:], graph)
    for e in chosen_edges:
        u_role = graph.node_meta[e.u][3]
        v_role = graph.node_meta[e.v][3]
        if u_role == "stab":
            s[e.u] ^= 1
        if v_role == "stab":
            s[e.v] ^= 1
    return s


class _DSU:
    def __init__(self):
        self.p: Dict[int, int] = {}
        self.r: Dict[int, int] = {}

    def add(self, x: int) -> None:
        if x not in self.p:
            self.p[x] = x
            self.r[x] = 0

    def find(self, x: int) -> int:
        px = self.p.setdefault(x, x)
        if px != x:
            self.p[x] = self.find(px)
        return self.p[x]

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        if self.r[ra] == self.r[rb]:
            self.r[ra] += 1


def _exact_homology_failure(
    graph: DecodingGraph, chosen_edges: List[Edge]
) -> Tuple[bool, bool]:
    """
    Exact spatial homology via side-aware boundaries:
      - Build per-time components using only SPACE and BOUNDARY edges from corrections.
      - A horizontal logical exists in time slice t iff a component contains both Left & Right boundaries.
      - A vertical logical exists in time slice t iff a component contains both Top & Bottom boundaries.
    Time-like edges are ignored (measurement errors only).
    """
    meta = graph.node_meta

    dsu_per_t: Dict[int, _DSU] = {}
    nodes_seen_per_t: Dict[int, List[int]] = {}

    def ensure_t(t: int) -> _DSU:
        if t not in dsu_per_t:
            dsu_per_t[t] = _DSU()
            nodes_seen_per_t[t] = []
        return dsu_per_t[t]

    for e in chosen_edges:
        if e.etype not in ("space", "boundary"):
            continue
        t_u = meta[e.u][2]
        t_v = meta[e.v][2]
        if t_u != t_v:
            continue
        dsu = ensure_t(t_u)
        dsu.add(e.u)
        dsu.add(e.v)
        nodes_seen_per_t[t_u].append(e.u)
        nodes_seen_per_t[t_u].append(e.v)
        dsu.union(e.u, e.v)

    horiz_fail = False
    vert_fail = False

    for t, dsu in dsu_per_t.items():
        hmask: Dict[int, int] = {}
        vmask: Dict[int, int] = {}

        for n in set(nodes_seen_per_t[t]):
            root = dsu.find(n)
            role = meta[n][3]
            if role.startswith("boundary-H-"):
                bit = 1 if role.endswith("-E") else 0  # E→bit1, W→bit0
                hmask[root] = hmask.get(root, 0) | (1 << bit)
            elif role.startswith("boundary-V-"):
                bit = 1 if role.endswith("-S") else 0  # S→bit1, N→bit0
                vmask[root] = vmask.get(root, 0) | (1 << bit)

        if any(mask == 0b11 for mask in hmask.values()):
            horiz_fail = True
        if any(mask == 0b11 for mask in vmask.values()):
            vert_fail = True

        if horiz_fail or vert_fail:
            break

    return horiz_fail, vert_fail


def apply_correction_and_check_logical(
    layout: RotatedSurfaceLayout,
    rounds: int,
    graph_X: DecodingGraph,
    graph_Z: DecodingGraph,
    syndromes_X: List[int],
    syndromes_Z: List[int],
    chosen_edges_X: List[Edge],
    chosen_edges_Z: List[Edge],
) -> bool:
    post_X = _apply_corrections_to_syndrome(graph_X, syndromes_X, chosen_edges_X)
    post_Z = _apply_corrections_to_syndrome(graph_Z, syndromes_Z, chosen_edges_Z)
    annihilated = (sum(post_X) == 0) and (sum(post_Z) == 0)
    if not annihilated:
        return False

    hz_fail_X, vt_fail_X = _exact_homology_failure(graph_X, chosen_edges_X)
    hz_fail_Z, vt_fail_Z = _exact_homology_failure(graph_Z, chosen_edges_Z)
    any_fail = hz_fail_X or vt_fail_X or hz_fail_Z or vt_fail_Z
    return not any_fail


def _logodds(p: float) -> float:
    p = min(max(float(p), 1e-12), 1.0 - 1e-12)
    return -np.log(p / (1.0 - p))


def build_graphs_for_p(
    builder: DecodingGraphBuilder, p: float
) -> Tuple[DecodingGraph, DecodingGraph]:
    """Construct and return (gX, gZ) once for a given p."""
    order_X = builder.node_order("X")
    order_Z = builder.node_order("Z")
    T = builder.T

    w_space_X = {(coord, t): _logodds(p) for (coord, t) in order_X}
    w_time_X = {(coord, t): _logodds(p) for (coord, t) in order_X if t < T - 1}
    p_erase_X = {(coord, t): 0.0 for (coord, t) in order_X if t < T - 1}

    w_space_Z = {(coord, t): _logodds(p) for (coord, t) in order_Z}
    w_time_Z = {(coord, t): _logodds(p) for (coord, t) in order_Z if t < T - 1}
    p_erase_Z = {(coord, t): 0.0 for (coord, t) in order_Z if t < T - 1}

    gX = builder.build("X", w_space_X, w_time_X, p_erase_X)
    gZ = builder.build("Z", w_space_Z, w_time_Z, p_erase_Z)
    return gX, gZ


def run_trial_with_graphs(
    builder: DecodingGraphBuilder,
    layout: RotatedSurfaceLayout,
    gX: DecodingGraph,
    gZ: DecodingGraph,
    p: float,
    seed: int,
    crossmodal: bool = False,
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    errors = generate_pauli_errors(layout, builder.T, p, rng)
    syndX, syndZ = syndromes_from_pauli_errors(
        layout, builder.T, errors, p_meas=p, rng=rng
    )

    uf = GreedyMatchingDecoder()
    osd = OSDDecoder(uf, osd_order=1, k_candidates=32)

    resX = osd.decode(gX, syndX)
    resZ = osd.decode(gZ, syndZ)

    success = apply_correction_and_check_logical(
        layout, builder.T, gX, gZ, syndX, syndZ, resX.corrections, resZ.corrections
    )
    return {
        "distance": layout.d,
        "rounds": builder.T,
        "p": p,
        "seed": seed,
        "success": int(success),
        "avg_costX": resX.avg_cost,
        "avg_costZ": resZ.avg_cost,
    }


def run_trial(
    distance: int, rounds: int, p: float, seed: int, crossmodal: bool
) -> Dict[str, Any]:
    layout = RotatedSurfaceLayout(distance)
    builder = DecodingGraphBuilder(layout, rounds, diagonal_adjacency=True)
    gX, gZ = build_graphs_for_p(builder, p)
    return run_trial_with_graphs(
        builder, layout, gX, gZ, p, seed, crossmodal=crossmodal
    )
