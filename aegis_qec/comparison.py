from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .decoder_plugins import custom_decoder_registry
from .research import wilson_interval


def _require_stim():
    try:
        import stim
    except ImportError as exc:
        raise RuntimeError(
            "Exact-shot comparison requires Stim. Install with: "
            "python -m pip install -U 'aegis-qec[full]'"
        ) from exc
    return stim


def _build_comparison_circuit(
    *,
    circuit_path: str | None,
    distance: int,
    physical_error_rate: float,
    basis: str,
    rounds: int | None,
):
    stim = _require_stim()
    if circuit_path:
        return stim.Circuit.from_file(circuit_path)

    basis = str(basis).lower()
    if basis not in {"x", "z"}:
        raise ValueError("basis must be 'x' or 'z'")
    distance = int(distance)
    if distance < 3 or distance % 2 == 0:
        raise ValueError("distance must be an odd integer >= 3")
    p = float(physical_error_rate)
    if not 0.0 <= p < 0.5:
        raise ValueError("physical_error_rate must satisfy 0 <= p < 0.5")
    point_rounds = distance if rounds is None else int(rounds)
    if point_rounds < 1:
        raise ValueError("rounds must be positive")

    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis}",
        distance=distance,
        rounds=point_rounds,
        after_clifford_depolarization=p,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )


def compare_decoders_exact_shots(
    *,
    decoders: Sequence[str] = (
        "aegis-pymatching",
        "aegis-pymatching-correlated",
    ),
    shots: int = 10_000,
    seed: int = 1234,
    circuit_path: str | None = None,
    distance: int = 5,
    physical_error_rate: float = 0.006,
    basis: str = "x",
    rounds: int | None = None,
    include_external_plugins: bool = True,
) -> dict[str, Any]:
    """Compare custom decoders on the exact same bit-packed detector shots."""

    if shots < 1:
        raise ValueError("shots must be positive")
    if not decoders:
        raise ValueError("at least one decoder is required")

    circuit = _build_comparison_circuit(
        circuit_path=circuit_path,
        distance=distance,
        physical_error_rate=physical_error_rate,
        basis=basis,
        rounds=rounds,
    )
    dem = circuit.detector_error_model(decompose_errors=True)
    circuit_text = str(circuit)
    dem_text = str(dem)

    detector_data, actual_observables = circuit.compile_detector_sampler(
        seed=int(seed)
    ).sample(
        shots=int(shots),
        separate_observables=True,
        bit_packed=True,
    )

    registry = custom_decoder_registry(
        include_external=include_external_plugins
    )
    unknown = [name for name in decoders if name not in registry]
    if unknown:
        raise ValueError(
            "Unknown exact-shot decoder(s): "
            + ", ".join(unknown)
            + ". Available: "
            + ", ".join(sorted(registry))
        )

    predictions: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    for name in decoders:
        compiled = registry[name].compile_decoder_for_dem(dem=dem)
        started = time.perf_counter()
        predicted = compiled.decode_shots_bit_packed(
            bit_packed_detection_event_data=detector_data
        )
        seconds = time.perf_counter() - started
        if predicted.shape != actual_observables.shape:
            raise ValueError(
                f"Decoder {name!r} returned shape {predicted.shape}, expected "
                f"{actual_observables.shape}."
            )
        predicted = np.asarray(predicted, dtype=np.uint8)
        predictions[name] = predicted

        failures = np.any(
            np.bitwise_xor(predicted, actual_observables) != 0,
            axis=1,
        )
        failure_count = int(np.sum(failures))
        error_rate = float(failure_count / shots)
        ci_low, ci_high = wilson_interval(failure_count, shots)
        rows.append(
            {
                "decoder": name,
                "shots": int(shots),
                "errors": failure_count,
                "logical_error_rate": error_rate,
                "ci95_low": float(ci_low),
                "ci95_high": float(ci_high),
                "decode_seconds": float(seconds),
                "decode_shots_per_second": float(
                    shots / max(seconds, 1.0e-12)
                ),
            }
        )

    disagreements: list[dict[str, Any]] = []
    names = list(decoders)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            disagree = np.any(
                np.bitwise_xor(predictions[left], predictions[right]) != 0,
                axis=1,
            )
            disagreements.append(
                {
                    "left": left,
                    "right": right,
                    "disagreement_shots": int(np.sum(disagree)),
                    "disagreement_rate": float(np.mean(disagree)),
                }
            )

    return {
        "schema_version": 1,
        "comparison_type": "exact_shared_detector_shots",
        "configuration": {
            "decoders": list(decoders),
            "shots": int(shots),
            "seed": int(seed),
            "circuit_path": circuit_path,
            "distance": int(distance),
            "physical_error_rate": float(physical_error_rate),
            "basis": basis,
            "rounds": rounds if rounds is not None else "distance",
        },
        "provenance": {
            "circuit_sha256": hashlib.sha256(
                circuit_text.encode("utf-8")
            ).hexdigest(),
            "dem_sha256": hashlib.sha256(
                dem_text.encode("utf-8")
            ).hexdigest(),
            "detector_sample_sha256": hashlib.sha256(
                detector_data.tobytes(order="C")
            ).hexdigest(),
            "observable_sample_sha256": hashlib.sha256(
                actual_observables.tobytes(order="C")
            ).hexdigest(),
            "num_detectors": int(circuit.num_detectors),
            "num_observables": int(circuit.num_observables),
        },
        "rows": rows,
        "pairwise_disagreements": disagreements,
        "interpretation": (
            "Every decoder in this result received the identical detector-shot "
            "matrix. Differences are therefore paired decoder differences rather "
            "than differences caused by independent Monte Carlo samples."
        ),
    }


def write_comparison_json(
    comparison: dict[str, Any],
    path: str = "research_out/comparison.json",
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(comparison, handle, indent=2, sort_keys=True)
        handle.write("\n")
