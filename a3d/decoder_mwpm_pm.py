from __future__ import annotations

from typing import Sequence

import numpy as np
import pymatching

from .decoder_mwpm import MWPMDecoder


class PyMatchingMWPMDecoder(MWPMDecoder):
    """Compatibility wrapper for PyMatching-backed graph and DEM decoding.

    The ordinary MWPMDecoder already uses PyMatching sparse blossom. This
    class remains for callers that imported the historical adapter directly.
    """

    def decode_graph(self, graph, syndromes):
        return self.decode(graph, syndromes)

    @staticmethod
    def matching_from_dem(dem_text: str) -> pymatching.Matching:
        try:
            import stim
        except ImportError as exc:  # pragma: no cover - optional extra
            raise RuntimeError(
                "Stim DEM support requires the optional dependency: "
                "pip install 'aegis-qec[full]'"
            ) from exc
        dem = stim.DetectorErrorModel(dem_text)
        return pymatching.Matching.from_detector_error_model(dem)

    def decode_dem(self, dem_text: str, syndrome: Sequence[int]) -> np.ndarray:
        """Decode explicit DEM detection events and return fault/observable flips."""
        matching = self.matching_from_dem(dem_text)
        shot = np.asarray([int(v) & 1 for v in syndrome], dtype=np.uint8)
        if len(shot) != matching.num_detectors:
            raise ValueError(
                f"Expected {matching.num_detectors} DEM detector bits, got {len(shot)}"
            )
        return matching.decode(shot)

    def decode_from_dem(
        self, dem_text: str, syndrome: Sequence[int] | None = None
    ):
        if syndrome is None:
            raise ValueError(
                "A detector error model does not contain an observed syndrome. "
                "Pass the detection-event bits as syndrome=..."
            )
        return self.decode_dem(dem_text, syndrome)
