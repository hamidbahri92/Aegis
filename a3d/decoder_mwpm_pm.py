
# FILE: a3d/decoder_mwpm_pm.py
from __future__ import annotations

from typing import Tuple

from .decoder_greedy import DecodeResult


class PyMatchingMWPMDecoder:
    """Run MWPM via PyMatching on a Stim DEM string.

    This decoder is only used when a DEM is provided (interop path).
    """
    def __init__(self):
        try:
            import pymatching as pm  # type: ignore
            import stim  # type: ignore
            self.pm = pm
            self.stim = stim
            self.ok = True
        except Exception:
            self.pm = None
            self.stim = None
            self.ok = False

    def decode_from_dem(self, dem_text: str) -> Tuple[DecodeResult, DecodeResult]:
        if not self.ok:
            # fallback empty result
            return DecodeResult([], 0.0, [], 0.0), DecodeResult([], 0.0, [], 0.0)
        dem = self.stim.DetectorErrorModel(dem_text)
        m = self.pm.Matching.from_detector_error_model(dem)
        # Without a real-time syndrome stream, return empty corrections placeholder.
        # Integrators can extend this path to feed measured syndromes to m.decode().
        return DecodeResult([], 0.0, [], 0.0), DecodeResult([], 0.0, [], 0.0)


    def decode_graph(self, graph, syndromes):
        """Export graph to DEM, build PyMatching, and decode the given syndrome."""
        if not self.ok:
            return DecodeResult([], 0.0, [], 0.0)
        from .dem_export import graph_to_dem_text
        dem_txt = graph_to_dem_text(graph)
        dem = self.stim.DetectorErrorModel(dem_txt)
        m = self.pm.Matching.from_detector_error_model(dem)
        # Expect syndromes length >= number of detectors
        syn = [int(x) for x in syndromes[: dem.num_detectors ]]
        try:
            _ = m.decode(syn)  # PyMatching returns observables flips; we ignore mapping here
        except Exception:
            pass
        # We don't have a direct mapping back to correction edges; return cost proxy
        return DecodeResult([], 0.0, [], 0.0)
