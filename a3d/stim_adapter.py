
# FILE: a3d/stim_adapter.py
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

try:
    import stim  # type: ignore
    STIM_OK = True
except Exception:  # pragma: no cover
    STIM_OK = False
    stim = None  # type: ignore

from .graph import DecodingGraph, Edge
from .stats import logodds_from_p


def _parse_error(line: str) -> Tuple[float, List[str]]:
    m = re.match(r"error\(([^)]+)\)\s+(.*)$", line.strip())
    if not m:
        return 0.5, []
    try:
        p = float(m.group(1))
    except Exception:
        p = 0.5
    rest = m.group(2).split()
    return p, rest

def graph_from_dem_text(dem_text: str) -> DecodingGraph:
    """Convert a Stim Detector Error Model (DEM) text into a DecodingGraph.

    Supported:
      - error(p) tokens: D# (detectors), L# (observables)
      - shift_detectors k: increments time slice t by k (>=1).

    We create nodes for each detector id seen at each time t; edges get weights from
    negative log-odds of p. Edges between detectors at the same t are 'space'; edges
    connecting to a boundary-L node are 'boundary'. If a parser sees detectors that
    reference a time slice with no prior declaration for that id, we allocate missing
    nodes up to that id for the current t.
    """
    # First pass: discover time slices and max detector id per slice
    t = 0
    max_d_per_t: Dict[int, int] = {0: -1}
    lines = [ln.strip() for ln in dem_text.splitlines()]
    for line in lines:
        if not line or line.startswith("#"):
            continue
        if line.startswith("shift_detectors"):
            parts = line.split()
            k = int(parts[1]) if len(parts) > 1 else 1
            t += max(1, k)
            if t not in max_d_per_t:
                max_d_per_t[t] = -1
            continue
        if line.startswith("error(") and "D" in line:
            # track largest detector id used at this t
            _, toks = _parse_error(line)
            for tok in toks:
                if tok.startswith("D"):
                    try:
                        did = int(tok[1:])
                        if did > max_d_per_t[t]:
                            max_d_per_t[t] = did
                    except Exception:
                        pass

    # Build nodes and per-time observable boundaries
    nodes: List[int] = []
    node_meta: Dict[int, Tuple[str, Optional[Tuple[int,int]], int, str]] = {}
    nid_of_det: Dict[Tuple[int, int], int] = {}   # (det_id, t) -> nid
    nid_of_obs: Dict[Tuple[int, int], int] = {}   # (L_id, t) -> nid
    nid = 0
    for ts in sorted(max_d_per_t.keys()):
        maxd = max_d_per_t[ts]
        for d in range(maxd + 1):
            nid_of_det[(d, ts)] = nid
            node_meta[nid] = ("X", None, ts, "stab")
            nodes.append(nid); nid += 1
        # create one generic boundary for this slice as well
        nid_of_obs[(-1, ts)] = nid
        node_meta[nid] = ("X", None, ts, "boundary-H-W")
        nodes.append(nid); nid += 1

    # Second pass: create edges
    edges: List[Edge] = []
    t = 0
    for line in lines:
        if not line or line.startswith("#"):
            continue
        if line.startswith("shift_detectors"):
            parts = line.split()
            k = int(parts[1]) if len(parts) > 1 else 1
            t += max(1, k)
            continue
        if line.startswith("error("):
            p, toks = _parse_error(line)
            w = float(logodds_from_p(p))
            dets = [int(tok[1:]) for tok in toks if tok.startswith("D")]
            lobs = [int(tok[1:]) for tok in toks if tok.startswith("L")]
            # ensure detector nodes exist at this t
            for d in dets:
                if (d, t) not in nid_of_det:
                    # allocate missing ids up to d
                    for z in range(max_d_per_t.get(t, -1) + 1, d + 1):
                        nid_of_det[(z, t)] = nid
                        node_meta[nid] = ("X", None, t, "stab")
                        nodes.append(nid); nid += 1
                    max_d_per_t[t] = d
            # connect detectors pairwise in a simple chain (D0-D1, D1-D2, ...)
            for i in range(max(0, len(dets) - 1)):
                u = nid_of_det[(dets[i], t)]
                v = nid_of_det[(dets[i+1], t)]
                etype = "space"  # same t
                edges.append(Edge(u, v, weight=w, etype=etype, p_erase=0.0))
            # connect any detector to per-observable boundary
            for lid in (lobs or [-1]):  # default to generic boundary if L not provided
                if (lid, t) not in nid_of_obs:
                    nid_of_obs[(lid, t)] = nid
                    node_meta[nid] = ("X", None, t, f"boundary-L-{lid}")
                    nodes.append(nid); nid += 1
                bnd = nid_of_obs[(lid, t)]
                for d in dets[:1] or [0]:
                    if (d, t) in nid_of_det:
                        u = nid_of_det[(d, t)]
                        edges.append(Edge(u, bnd, weight=w, etype="boundary", p_erase=0.0))

    return DecodingGraph(nodes=nodes, edges=edges, node_meta=node_meta)

def graph_from_dem_file(path: str) -> DecodingGraph:
    with open(path, "r", encoding="utf-8") as f:
        return graph_from_dem_text(f.read())
