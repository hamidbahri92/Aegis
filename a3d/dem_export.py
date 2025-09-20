
# FILE: a3d/dem_export.py
from __future__ import annotations

from typing import List

from .graph import DecodingGraph


def graph_to_dem_text(graph: DecodingGraph) -> str:
    """Approximate conversion of our DecodingGraph to a Stim DEM text.

    - Each 'space' or 'time' edge (u,v) -> error(p) D{u} D{v}
    - Each 'boundary' edge (u,bnd) -> error(p) D{u} L0
    We do not encode rounds explicitly (no shift_detectors). This path is intended
    for **fast MWPM** via PyMatching on static graphs.
    """
    lines: List[str] = []
    def p_from_weight(w: float) -> float:
        # invert log-odds-ish weight into prob (rough; for performance path only)
        import math
        w = max(1e-9, float(w))
        # if w is -log p -> p ~ exp(-w); if w is log-odds -> sigmoid(-w)
        p1 = min(0.49, math.exp(-w))
        p2 = 1.0 / (1.0 + math.exp(w))
        return max(1e-6, min(0.49, max(p1, p2)))
    for e in graph.edges:
        p = p_from_weight(e.weight)
        if e.etype in ("space","time"):
            lines.append(f"error({p:.6f}) D{e.u} D{e.v}")
        elif e.etype == "boundary":
            # Single observable L0 to absorb boundaries
            u = e.u
            lines.append(f"error({p:.6f}) D{u} L0")
    return "\n".join(lines) + "\n"
