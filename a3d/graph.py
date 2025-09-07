# FILE: a3d/graph.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from .layouts import CodeLayout


@dataclass(frozen=True)
class Edge:
    u: int
    v: int
    weight: float
    etype: str  # "space" | "time" | "boundary"
    p_erase: float = 0.0


@dataclass(frozen=True)
class HyperEdge:
    nodes: List[int]
    weight: float
    edge_type: str  # "measurement" | "crosstalk" | "leakage"
    p_erase: float = 0.0


@dataclass
class DecodingGraph:
    nodes: List[int]
    edges: List[Edge]
    # nid -> (sector, coord, t, role)
    # role: "stab" | "boundary-H-W" | "boundary-H-E" | "boundary-V-N" | "boundary-V-S"
    node_meta: Dict[int, Tuple[str, Optional[Tuple[int, int]], int, str]]


@dataclass
class HyperDecodingGraph:
    nodes: List[int]
    edges: List[Edge]
    hyperedges: List[HyperEdge]
    node_meta: Dict[int, Tuple[str, Optional[Tuple[int, int]], int, str]]
    # NOTE: hyperedges are currently experimental; core decoders do not depend on them.


class RotatedSurfaceLayout(CodeLayout):
    """
    Rotated surface-code toy layout: checkerboard stabilizers, implicit data-qubit grid.
    Single data-qubit errors typically connect **diagonal** like-type checks.
    """
    def __init__(self, distance: int):
        super().__init__(distance)
        self._build_stabs()

    def _build_stabs(self) -> None:
        self._stabs: Dict[str, List[Tuple[int, int]]] = {"X": [], "Z": []}
        for i in range(self.d):
            for j in range(self.d):
                if (i + j) % 2 == 0:
                    self._stabs["X"].append((i, j))
                else:
                    self._stabs["Z"].append((i, j))

    def stabilizer_coords(self) -> Dict[str, List[Tuple[int, int]]]:
        return self._stabs

    def data_qubits(self) -> List[Tuple[int, int]]:
        """Toy model: data qubits co-located on the same grid."""
        return [(i, j) for i in range(self.d) for j in range(self.d)]

    # neighbors() inherited from CodeLayout is correct for rotated layout (diagonal by default)


class DecodingGraphBuilder:
    """
    Build time-like and space-like edges for a given sector.
    Uses layout.neighbors() when available; falls back to internal rule.
    Adds per-time virtual boundary nodes (Left/Right & Top/Bottom) to allow defect→boundary matches
    and enable **exact homology** checks post-decoding.
    """
    def __init__(self, layout: CodeLayout, rounds: int, diagonal_adjacency: bool = True):
        self.layout = layout
        self.T = int(rounds)
        self.diagonal_adjacency = bool(diagonal_adjacency)

    def node_order(self, sector: str) -> List[Tuple[Tuple[int, int], int]]:
        stabs = self.layout.stabilizer_coords()[sector]
        order: List[Tuple[Tuple[int, int], int]] = []
        for t in range(self.T):
            for coord in stabs:
                order.append((coord, t))
        return order

    def _neighbors(self, sector: str, coord: Tuple[int, int]) -> List[Tuple[int, int]]:
        if hasattr(self.layout, "neighbors"):
            return self.layout.neighbors(sector, coord, diagonal=self.diagonal_adjacency)  # type: ignore
        i, j = coord
        stabs = set(self.layout.stabilizer_coords()[sector])
        if self.diagonal_adjacency:
            cands = [(i+1, j+1), (i+1, j-1)]
        else:
            cands = [(i+1, j), (i, j+1)]
        return [nb for nb in cands if nb in stabs]

    def build(
        self,
        sector: str,
        w_space: Dict[Tuple[Tuple[int, int], int], float],      # keys: (coord, t)
        w_time: Dict[Tuple[Tuple[int, int], int], float],       # keys: (coord, t) with t in [0..T-2]
        p_erase_time: Dict[Tuple[Tuple[int, int], int], float], # keys: (coord, t) with t in [0..T-2]
    ) -> DecodingGraph:
        stabs = self.layout.stabilizer_coords()[sector]

        # Map (coord, t) -> node id for stabilizers
        nid_of: Dict[Tuple[Tuple[int, int], int], int] = {}
        nodes: List[int] = []
        node_meta: Dict[int, Tuple[str, Optional[Tuple[int, int]], int, str]] = {}
        nid = 0
        for t in range(self.T):
            for coord in stabs:
                nid_of[(coord, t)] = nid
                node_meta[nid] = (sector, coord, t, "stab")
                nodes.append(nid)
                nid += 1

        # Per-time boundary nodes for this sector: H: West/East, V: North/South
        bnd_HW: Dict[int, int] = {}
        bnd_HE: Dict[int, int] = {}
        bnd_VN: Dict[int, int] = {}
        bnd_VS: Dict[int, int] = {}
        for t in range(self.T):
            bHW = nid
            node_meta[bHW] = (sector, None, t, "boundary-H-W")
            nodes.append(bHW)
            nid += 1
            bHE = nid
            node_meta[bHE] = (sector, None, t, "boundary-H-E")
            nodes.append(bHE)
            nid += 1
            bVN = nid
            node_meta[bVN] = (sector, None, t, "boundary-V-N")
            nodes.append(bVN)
            nid += 1
            bVS = nid
            node_meta[bVS] = (sector, None, t, "boundary-V-S")
            nodes.append(bVS)
            nid += 1
            bnd_HW[t] = bHW
            bnd_HE[t] = bHE
            bnd_VN[t] = bVN
            bnd_VS[t] = bVS

        edges: List[Edge] = []

        # Time-like edges
        for t in range(self.T - 1):
            for coord in stabs:
                key = (coord, t)
                u = nid_of[(coord, t)]
                v = nid_of[(coord, t + 1)]
                wt = float(w_time.get(key, 1.0))
                pe = float(p_erase_time.get(key, 0.0))
                edges.append(Edge(u, v, wt, "time", pe))

        # Space-like edges + boundaries
        d = self.layout.d
        for t in range(self.T):
            for coord in stabs:
                u = nid_of[(coord, t)]
                # neighbors (space)
                for nb in self._neighbors(sector, coord):
                    v = nid_of[(nb, t)]
                    wt = 0.5 * (
                        float(w_space.get((coord, t), 1.0)) +
                        float(w_space.get((nb, t), 1.0))
                    )
                    edges.append(Edge(u, v, wt, "space", 0.0))

                # boundary edges for perimeter checks (side-aware)
                i, j = coord
                if j == 0:
                    wtH = float(w_space.get((coord, t), 1.0))
                    edges.append(Edge(u, bnd_HW[t], wtH, "boundary", 0.0))
                if j == d - 1:
                    wtH = float(w_space.get((coord, t), 1.0))
                    edges.append(Edge(u, bnd_HE[t], wtH, "boundary", 0.0))
                if i == 0:
                    wtV = float(w_space.get((coord, t), 1.0))
                    edges.append(Edge(u, bnd_VN[t], wtV, "boundary", 0.0))
                if i == d - 1:
                    wtV = float(w_space.get((coord, t), 1.0))
                    edges.append(Edge(u, bnd_VS[t], wtV, "boundary", 0.0))

        return DecodingGraph(nodes=nodes, edges=edges, node_meta=node_meta)
