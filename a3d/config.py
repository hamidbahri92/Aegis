# FILE: a3d/config.py
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class AegisConfig:
    """Global configuration for Aegis decoders and graph building.

    Fields are intentionally simple types for JSON-serializability.
    """
    # Code geometry / windowing
    distance: int = 5
    rounds: int = 6

    # Decoder selection
    # one of: "greedy", "osd", "mwpm", "mwpm2" (pipelined), "mwpm_corr" (correlation-aware), "uf"|"unionfind"|"uf_e"
    decoder_type: str = "osd"

    # Physical error model (simple iid knobs used for synthetic weights)
    p_data: float = 0.02
    p_meas: float = 0.03
    p_leak: float = 0.0
    time_weight_scale: float = 1.0

    # Decision thresholds (used by some heuristics)
    uf_confidence_threshold: float = 3.0
    avg_cost_threshold: float = 5.0

    # Optional reweighter for edge costs prior to decoding
    # "none" | "transformer"
    reweighter_type: str = "none"  # 'none' | 'bp' | 'transformer' | 'transformer_sota'  # or 'transformer' or 'bp'
    # Path to a .pt file for the transformer (optional)
    reweighter_weights: str = ""

    # Optional path for correlation parameters (JSON)
    correlation_params: str = ""
    log_events: bool = False
    log_path: str = "logs/decoding_events.csv"

    # Certificates & profiling
    run_certificate: bool = True
    certificate_mode: str = "osd"  # 'osd' or 'none'
    profile: bool = False
    profile_path: str = "logs/profile.csv"
    prefer_pymatching: bool = False

    # ---- Persistence helpers -------------------------------------------------
    def save_to_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=2)

    @classmethod
    def load_from_file(cls, path: str) -> "AegisConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    # ---- Validation ----------------------------------------------------------
    def validate(self) -> None:
        if not (isinstance(self.distance, int) and self.distance >= 3):
            raise ValueError("distance must be an integer >= 3")
        if not (isinstance(self.rounds, int) and self.rounds >= 2):
            raise ValueError("rounds must be an integer >= 2")
        if self.decoder_type not in ("greedy","osd","mwpm","mwpm2","uf","unionfind","uf_e"):
            raise ValueError("decoder_type must be one of {'greedy','osd','mwpm','mwpm2','uf'}")
        for name in ("p_data","p_meas","p_leak","time_weight_scale","uf_confidence_threshold","avg_cost_threshold"):
            v = float(getattr(self, name))
            if not (0.0 <= v < 1e6):
                raise ValueError(f"{name} out of bounds: {v}")
        if self.reweighter_type not in ("none","transformer","bp"):
            raise ValueError("reweighter_type must be 'none' or 'transformer'")

