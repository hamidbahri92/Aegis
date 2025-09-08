# FILE: a3d/config.py
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class AegisConfig:
    # code geometry / windowing
    distance: int = 5
    rounds: int = 6

    # decoder thresholds
    uf_confidence_threshold: float = 3.0
    avg_cost_threshold: float = 5.0

    # noise & weighting
    p_data: float = 1.0e-3  # data (space) error rate
    p_meas: float = 1.0e-3  # measurement (time) error rate
    p_leak: float = 0.0  # reserved for future erase edges
    time_weight_scale: float = 1.0  # multiply time-edge log-odds by this

    # decoder selection: "greedy", "osd", "mwpm"
    decoder_type: str = "osd"

    def save_to_file(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)

    @classmethod
    def load_from_file(cls, path: str) -> "AegisConfig":
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def validate(self) -> None:
        if not (isinstance(self.distance, int) and self.distance >= 3):
            raise ValueError("distance must be an integer >= 3")
        if not (isinstance(self.rounds, int) and self.rounds >= 2):
            raise ValueError("rounds must be an integer >= 2")
        # Pragmatic guardrails (can be relaxed if needed)
        for name, val in (
            ("uf_confidence_threshold", self.uf_confidence_threshold),
            ("avg_cost_threshold", self.avg_cost_threshold),
            ("p_data", self.p_data),
            ("p_meas", self.p_meas),
            ("p_leak", self.p_leak),
            ("time_weight_scale", self.time_weight_scale),
        ):
            if not (0.0 <= float(val) < 1.0e6):
                raise ValueError(f"{name} out of bounds")
        if self.decoder_type not in ("greedy", "osd", "mwpm"):
            raise ValueError("decoder_type must be one of {'greedy','osd','mwpm'}")
