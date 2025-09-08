# FILE: a3d/layouts.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class CodeLayout(ABC):
    """Abstract code layout. Implementors provide stabilizer coordinates and neighbor logic."""

    def __init__(self, distance: int):
        self.d = int(distance)
        if self.d <= 0:
            raise ValueError("distance must be positive")

    @abstractmethod
    def stabilizer_coords(self) -> Dict[str, List[Tuple[int, int]]]:
        """Return {'X': [(i,j)...], 'Z': [(i,j)...]} in layout coordinates."""
        raise NotImplementedError

    @abstractmethod
    def data_qubits(self) -> List[Tuple[int, int]]:
        """Return positions of data qubits used by noise/syndrome generation."""
        raise NotImplementedError

    def neighbors(
        self, sector: str, coord: Tuple[int, int], diagonal: bool = True
    ) -> List[Tuple[int, int]]:
        """Neighbor rule used by decoding graph. Default: diagonal for rotated, manhattan otherwise."""
        i, j = coord
        stabs = set(self.stabilizer_coords()[sector])
        if diagonal:
            cands = [(i + 1, j + 1), (i + 1, j - 1)]
        else:
            cands = [(i + 1, j), (i, j + 1)]
        return [nb for nb in cands if nb in stabs]
