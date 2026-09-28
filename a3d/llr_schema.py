# FILE: a3d/llr_schema.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SoftSyndrome:
    llr_X: List[float]
    llr_Z: List[float]
    p_erase_time: Optional[List[float]] = None
    leakage_flags: Optional[List[int]] = None  # 1 if leaked else 0

def validate_soft(s: SoftSyndrome) -> None:
    assert isinstance(s.llr_X, list) and isinstance(s.llr_Z, list), "LLR arrays must be lists"
    for arr in (s.llr_X, s.llr_Z):
        for v in arr:
            float(v)
    if s.p_erase_time is not None:
        for p in s.p_erase_time:
            assert 0.0 <= float(p) <= 1.0
    if s.leakage_flags is not None:
        for f in s.leakage_flags:
            assert int(f) in (0,1)
