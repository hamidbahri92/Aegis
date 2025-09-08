# FILE: a3d/runtime.py
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np

from .config import AegisConfig
from .decoder_bposd import OSDDecoder
from .decoder_greedy import DecodeResult, GreedyMatchingDecoder
from .decoder_mwpm import MWPMDecoder
from .graph import DecodingGraph, DecodingGraphBuilder, RotatedSurfaceLayout

logger = logging.getLogger("a3d.runtime")


def _logodds(p: float) -> float:
    p = min(max(float(p), 1.0e-12), 1.0 - 1.0e-12)
    return -float(np.log(p / (1.0 - p)))


class DecoderRuntime:
    """Core runtime: build graphs, decode with chosen algorithm, optional ML rescore."""

    def __init__(self, cfg: AegisConfig, layout: RotatedSurfaceLayout):
        self.cfg = cfg
        self.layout = layout
        self.builder = DecodingGraphBuilder(layout, cfg.rounds, diagonal_adjacency=True)
        self.uf = GreedyMatchingDecoder()
        self.bposd = OSDDecoder(self.uf, osd_order=1, k_candidates=32)
        self.mwpm = MWPMDecoder()
        self._ml = None  # optional

        self.cfg.validate()

    def _validate_inputs(self, syndromes_X: List[int], syndromes_Z: List[int]) -> None:
        nX = len(self.builder.node_order("X"))
        nZ = len(self.builder.node_order("Z"))
        if len(syndromes_X) != nX:
            raise ValueError(f"Expected {nX} X-syndromes, got {len(syndromes_X)}")
        if len(syndromes_Z) != nZ:
            raise ValueError(f"Expected {nZ} Z-syndromes, got {len(syndromes_Z)}")

    def _weight_dicts_from_cfg(self, sector: str) -> Tuple[
        Dict[Tuple[Tuple[int, int], int], float],
        Dict[Tuple[Tuple[int, int], int], float],
        Dict[Tuple[Tuple[int, int], int], float],
    ]:
        order = self.builder.node_order(sector)
        T = self.cfg.rounds
        w_space = {(coord, t): _logodds(self.cfg.p_data) for (coord, t) in order}
        w_time = {
            (coord, t): _logodds(self.cfg.p_meas) * self.cfg.time_weight_scale
            for (coord, t) in order
            if t < T - 1
        }
        p_erase = {
            (coord, t): min(max(self.cfg.p_leak, 0.0), 0.99)
            for (coord, t) in order
            if t < T - 1
        }
        return w_space, w_time, p_erase

    def _decode_with_choice(
        self, graph: DecodingGraph, syn: List[int], axis: str
    ) -> DecodeResult:
        dtype = self.cfg.decoder_type
        if dtype == "greedy":
            res = self.uf.decode(graph, syn)
            if res.avg_cost > self.cfg.uf_confidence_threshold:
                logger.warning(
                    "UF %s avg_cost=%.3f > threshold=%.3f; OSD fallback",
                    axis,
                    res.avg_cost,
                    self.cfg.uf_confidence_threshold,
                )
                res = self.bposd.decode(graph, syn)
            return res
        elif dtype == "osd":
            return self.bposd.decode(graph, syn)
        elif dtype == "mwpm":
            return self.mwpm.decode(graph, syn)
        else:
            return self.bposd.decode(graph, syn)

    def decode_window(
        self,
        w_space_X: Dict[Tuple[Tuple[int, int], int], float],
        w_time_X: Dict[Tuple[Tuple[int, int], int], float],
        p_erase_X: Dict[Tuple[Tuple[int, int], int], float],
        w_space_Z: Dict[Tuple[Tuple[int, int], int], float],
        w_time_Z: Dict[Tuple[Tuple[int, int], int], float],
        p_erase_Z: Dict[Tuple[Tuple[int, int], int], float],
        syndromes_X: List[int],
        syndromes_Z: List[int],
    ) -> Tuple[DecodeResult, DecodeResult]:
        self._validate_inputs(syndromes_X, syndromes_Z)
        graph_X = self.builder.build("X", w_space_X, w_time_X, p_erase_X)
        graph_Z = self.builder.build("Z", w_space_Z, w_time_Z, p_erase_Z)

        resX = self._decode_with_choice(graph_X, syndromes_X, axis="X")
        resZ = self._decode_with_choice(graph_Z, syndromes_Z, axis="Z")

        if getattr(self, "_ml", None) is not None:
            try:
                from .decoder_ml import decode_with_gnn

                logitsX = self._ml_logits(graph_X)
                logitsZ = self._ml_logits(graph_Z)
                mresX = decode_with_gnn(graph_X, logitsX, threshold=0.6)
                mresZ = decode_with_gnn(graph_Z, logitsZ, threshold=0.6)
                if mresX.log_likelihood < resX.log_likelihood and mresX.avg_cost > 0:
                    resX = mresX
                if mresZ.log_likelihood < resZ.log_likelihood and mresZ.avg_cost > 0:
                    resZ = mresZ
            except Exception:
                logger.exception("ML fallback failed")

        return resX, resZ

    def decode_from_syndromes_calibrated(
        self,
        syndromes_X: List[int],
        syndromes_Z: List[int],
    ) -> Tuple[DecodeResult, DecodeResult]:
        w_space_X, w_time_X, p_erase_X = self._weight_dicts_from_cfg("X")
        w_space_Z, w_time_Z, p_erase_Z = self._weight_dicts_from_cfg("Z")
        return self.decode_window(
            w_space_X,
            w_time_X,
            p_erase_X,
            w_space_Z,
            w_time_Z,
            p_erase_Z,
            syndromes_X,
            syndromes_Z,
        )

    def decode_from_syndromes_uniform(
        self,
        syndromes_X: List[int],
        syndromes_Z: List[int],
        weight_space: float = 1.0,
        weight_time: float = 1.0,
        perase_time: float = 0.0,
    ) -> Tuple[DecodeResult, DecodeResult]:
        order_X = self.builder.node_order("X")
        order_Z = self.builder.node_order("Z")
        T = self.cfg.rounds

        w_space_X = {(coord, t): float(weight_space) for (coord, t) in order_X}
        w_time_X = {
            (coord, t): float(weight_time) for (coord, t) in order_X if t < T - 1
        }
        p_erase_X = {
            (coord, t): float(perase_time) for (coord, t) in order_X if t < T - 1
        }

        w_space_Z = {(coord, t): float(weight_space) for (coord, t) in order_Z}
        w_time_Z = {
            (coord, t): float(weight_time) for (coord, t) in order_Z if t < T - 1
        }
        p_erase_Z = {
            (coord, t): float(perase_time) for (coord, t) in order_Z if t < T - 1
        }

        return self.decode_window(
            w_space_X,
            w_time_X,
            p_erase_X,
            w_space_Z,
            w_time_Z,
            p_erase_Z,
            syndromes_X,
            syndromes_Z,
        )

    def attach_ml_model(self, model, logits_fn) -> None:
        self._ml = model
        self._ml_logits = logits_fn
