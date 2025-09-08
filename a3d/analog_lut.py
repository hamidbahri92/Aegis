# FILE: a3d/analog_lut.py
from __future__ import annotations

from typing import Any, Dict

import numpy as np


class GKPLUTBuilder:
    """
    Minimal LUT builder stub (for export demo):
    Builds a monotone grid x and two synthetic arrays Lq, Lp.
    """

    def __init__(self, x_min: float = -3.5, x_max: float = 3.5, n: int = 1024):
        self.x_min = float(x_min)
        self.x_max = float(x_max)
        self.n = int(n)

    def build_lut(self) -> Dict[str, Any]:
        x = np.linspace(self.x_min, self.x_max, self.n, dtype=np.float64)
        Lq = -np.abs(x)  # toy shape
        Lp = -(x**2) * 0.1
        return {"x": x, "Lq": Lq, "Lp": Lp}
