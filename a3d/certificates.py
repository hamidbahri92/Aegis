
# FILE: a3d/certificates.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .decoder_bposd import GreedyMatchingDecoder, OSDDecoder
from .graph import DecodingGraph, Edge

# Reuse exact homology logic from metrics to avoid duplication
from .metrics import _exact_homology_failure as exact_homology_failure


@dataclass
class CertificateReport:
    ok: bool
    fail_horizontal: bool
    fail_vertical: bool
    improved: bool
    log_likelihood_before: float
    log_likelihood_after: float

def run_homology_certificate(graph: DecodingGraph, corrections: List[Edge]) -> Tuple[bool, bool]:
    failH, failV = exact_homology_failure(graph, corrections)
    return (not (failH or failV), failH or failV)

def osd_polish(graph: DecodingGraph, syndromes: List[int], base_decoder: GreedyMatchingDecoder, base_result) -> Tuple:
    """Run order-1 OSD polish seeded by a Greedy decoder; return the better of base and polished."""
    osd = OSDDecoder(base_decoder, osd_order=1, k_candidates=32)
    res = osd.decode(graph, syndromes)
    if res.log_likelihood < base_result.log_likelihood:
        return res, True
    return base_result, False
