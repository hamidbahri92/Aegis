from __future__ import annotations

import csv
import json
import math
import platform
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Sequence

import numpy as np


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def wilson_interval(
    failures: int,
    shots: int,
    z: float = 1.959963984540054,
) -> tuple[float, float]:
    """Return a two-sided Wilson score interval for a binomial failure rate."""
    if shots < 1:
        raise ValueError("shots must be positive")
    if failures < 0 or failures > shots:
        raise ValueError("failures must satisfy 0 <= failures <= shots")

    n = float(shots)
    rate = float(failures) / n
    denominator = 1.0 + z * z / n
    centre = (rate + z * z / (2.0 * n)) / denominator
    radius = (
        z
        * math.sqrt(rate * (1.0 - rate) / n + z * z / (4.0 * n * n))
        / denominator
    )
    return max(0.0, centre - radius), min(1.0, centre + radius)


def _validate_distances(distances: Sequence[int]) -> list[int]:
    values = [int(value) for value in distances]
    if not values:
        raise ValueError("at least one code distance is required")
    for value in values:
        if value < 3 or value % 2 == 0:
            raise ValueError("surface-code study distances must be odd integers >= 3")
    return values


def _validate_probabilities(probabilities: Sequence[float]) -> list[float]:
    values = [float(value) for value in probabilities]
    if not values:
        raise ValueError("at least one physical error probability is required")
    for value in values:
        if not 0.0 <= value < 0.5:
            raise ValueError("physical error probabilities must satisfy 0 <= p < 0.5")
    return values


def run_surface_code_study(
    distances: Sequence[int] = (3, 5, 7),
    physical_error_rates: Sequence[float] = (0.001, 0.003, 0.006, 0.01),
    *,
    shots: int = 1000,
    basis: str = "x",
    rounds: int | None = None,
    seed: int = 1234,
) -> dict[str, Any]:
    """Run a reproducible Stim surface-code memory study through Aegis.

    Each study point generates a Stim rotated-memory circuit, derives its detector
    error model, samples detector events and observables, and decodes the exact
    sampled detector shots through Aegis's direct PyMatching DEM bridge.

    When rounds is omitted, each distance uses rounds=distance, keeping temporal
    depth proportional to code distance.
    """

    if shots < 1:
        raise ValueError("shots must be positive")

    basis = str(basis).lower()
    if basis not in {"x", "z"}:
        raise ValueError("basis must be 'x' or 'z'")

    if rounds is not None and int(rounds) < 1:
        raise ValueError("rounds must be positive when provided")

    distances = _validate_distances(distances)
    probabilities = _validate_probabilities(physical_error_rates)

    try:
        import stim
    except ImportError as exc:
        raise RuntimeError(
            "Circuit studies require Stim. Install with: "
            "python -m pip install -U 'aegis-qec[full]'"
        ) from exc

    from a3d.decoder_mwpm_pm import PyMatchingMWPMDecoder

    decoder = PyMatchingMWPMDecoder()
    points: list[dict[str, Any]] = []
    total_started = time.perf_counter()
    point_index = 0

    for distance in distances:
        point_rounds = int(rounds) if rounds is not None else distance

        for physical_error_rate in probabilities:
            point_seed = int(seed) + point_index
            point_index += 1

            circuit = stim.Circuit.generated(
                f"surface_code:rotated_memory_{basis}",
                distance=distance,
                rounds=point_rounds,
                after_clifford_depolarization=physical_error_rate,
                before_measure_flip_probability=physical_error_rate,
                after_reset_flip_probability=physical_error_rate,
            )

            dem = circuit.detector_error_model(decompose_errors=True)

            sample_started = time.perf_counter()
            detector_samples, actual_observables = circuit.compile_detector_sampler(
                seed=point_seed
            ).sample(
                shots=shots,
                separate_observables=True,
            )
            sample_seconds = time.perf_counter() - sample_started

            decode_started = time.perf_counter()
            predictions = decoder.decode_dem_batch(str(dem), detector_samples)
            decode_seconds = time.perf_counter() - decode_started

            failures_by_shot = np.any(predictions != actual_observables, axis=1)
            failures = int(np.sum(failures_by_shot))
            logical_error_rate = float(failures / shots)
            ci_low, ci_high = wilson_interval(failures, shots)

            points.append(
                {
                    "distance": int(distance),
                    "rounds": int(point_rounds),
                    "basis": basis,
                    "physical_error_rate": float(physical_error_rate),
                    "shots": int(shots),
                    "logical_failures": failures,
                    "logical_error_rate": logical_error_rate,
                    "ci95_low": float(ci_low),
                    "ci95_high": float(ci_high),
                    "detectors": int(detector_samples.shape[1]),
                    "observables": int(actual_observables.shape[1]),
                    "detection_events": int(np.sum(detector_samples)),
                    "seed": int(point_seed),
                    "sample_seconds": float(sample_seconds),
                    "decode_seconds": float(decode_seconds),
                    "decode_shots_per_second": float(
                        shots / max(decode_seconds, 1.0e-12)
                    ),
                }
            )

    return {
        "schema_version": 1,
        "study_type": "stim_rotated_surface_code_memory",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "distances": distances,
            "physical_error_rates": probabilities,
            "shots_per_point": int(shots),
            "basis": basis,
            "rounds": int(rounds) if rounds is not None else "distance",
            "base_seed": int(seed),
            "noise_model": {
                "after_clifford_depolarization": "p",
                "before_measure_flip_probability": "p",
                "after_reset_flip_probability": "p",
            },
        },
        "environment": {
            "aegis_qec": _distribution_version("aegis-qec") or "source-checkout",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "stim": _distribution_version("stim"),
            "pymatching": _distribution_version("pymatching"),
            "numpy": _distribution_version("numpy"),
        },
        "points": points,
        "elapsed_seconds": float(time.perf_counter() - total_started),
        "interpretation": (
            "Logical-error rates are measured from Stim-generated rotated surface-code "
            "memory circuits and decoded through Aegis's direct detector-error-model "
            "bridge to PyMatching sparse blossom. A finite grid is evidence for the "
            "specified simulated noise model; it is not, by itself, a hardware threshold "
            "measurement or a universal decoder comparison."
        ),
    }


def write_study_artifacts(
    study: dict[str, Any],
    *,
    json_path: str | None = None,
    csv_path: str | None = None,
    plot_path: str | None = None,
) -> None:
    """Write reproducible study artifacts without modifying the study result."""

    points = list(study.get("points", []))

    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(study, handle, indent=2, sort_keys=True)
            handle.write("\n")

    if csv_path:
        path = Path(csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "distance",
            "rounds",
            "basis",
            "physical_error_rate",
            "shots",
            "logical_failures",
            "logical_error_rate",
            "ci95_low",
            "ci95_high",
            "detectors",
            "observables",
            "detection_events",
            "seed",
            "sample_seconds",
            "decode_seconds",
            "decode_shots_per_second",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for point in points:
                writer.writerow({name: point.get(name) for name in fieldnames})

    if plot_path:
        import matplotlib.pyplot as plt

        path = Path(plot_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(7.0, 4.5))
        distances = sorted({int(point["distance"]) for point in points})

        for distance in distances:
            selected = sorted(
                (point for point in points if int(point["distance"]) == distance),
                key=lambda point: float(point["physical_error_rate"]),
            )
            x = [float(point["physical_error_rate"]) for point in selected]
            y = [float(point["logical_error_rate"]) for point in selected]
            lower = [
                max(0.0, y_value - float(point["ci95_low"]))
                for y_value, point in zip(y, selected, strict=True)
            ]
            upper = [
                max(0.0, float(point["ci95_high"]) - y_value)
                for y_value, point in zip(y, selected, strict=True)
            ]
            ax.errorbar(
                x,
                y,
                yerr=[lower, upper],
                marker="o",
                capsize=4,
                label=f"d={distance}",
            )

        ax.set_xlabel("Physical error probability p")
        ax.set_ylabel("Logical error rate")
        ax.set_title("Aegis QEC circuit-level surface-code study")
        if points and all(
            float(point["physical_error_rate"]) > 0.0 for point in points
        ):
            ax.set_xscale("log")
        ax.set_ylim(bottom=0.0)
        ax.grid(True, alpha=0.25)
        if distances:
            ax.legend(title="Code distance")
        fig.tight_layout()
        fig.savefig(path, dpi=180)
        plt.close(fig)
