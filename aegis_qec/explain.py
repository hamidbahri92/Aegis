from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


def _require_dependencies():
    try:
        import pymatching
        import stim
    except ImportError as exc:
        raise RuntimeError(
            "Shot explanation requires Stim and PyMatching. Install with: "
            "python -m pip install -U 'aegis-qec[full]'"
        ) from exc
    return pymatching, stim


def explain_surface_code_shot(
    *,
    distance: int = 5,
    physical_error_rate: float = 0.006,
    basis: str = "x",
    rounds: int | None = None,
    seed: int = 1234,
) -> dict[str, Any]:
    """Generate and explain one rotated surface-code memory shot."""

    pymatching, stim = _require_dependencies()

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

    circuit = stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis}",
        distance=distance,
        rounds=point_rounds,
        after_clifford_depolarization=p,
        before_round_data_depolarization=p,
        before_measure_flip_probability=p,
        after_reset_flip_probability=p,
    )
    dem = circuit.detector_error_model(decompose_errors=True)
    detector_bits, actual_observables = circuit.compile_detector_sampler(
        seed=int(seed)
    ).sample(
        shots=1,
        separate_observables=True,
    )

    syndrome = np.asarray(detector_bits[0], dtype=np.uint8)
    actual = np.asarray(actual_observables[0], dtype=np.uint8)
    matching = pymatching.Matching.from_detector_error_model(dem)
    predicted = np.asarray(matching.decode(syndrome), dtype=np.uint8)
    matched_pairs = np.asarray(
        matching.decode_to_matched_dets_array(syndrome),
        dtype=int,
    )
    correction_edges = np.asarray(
        matching.decode_to_edges_array(syndrome),
        dtype=int,
    )

    detector_coordinates = circuit.get_detector_coordinates()
    fired_ids = [int(index) for index in np.flatnonzero(syndrome)]

    def coordinates(detector_id: int) -> list[float]:
        return [
            float(value)
            for value in detector_coordinates.get(int(detector_id), [])
        ]

    fired_detectors = [
        {
            "detector": detector_id,
            "coordinates": coordinates(detector_id),
        }
        for detector_id in fired_ids
    ]

    pairs = []
    for left, right in matched_pairs.tolist():
        pairs.append(
            {
                "left_detector": int(left),
                "left_coordinates": coordinates(int(left)),
                "right_detector": None if int(right) < 0 else int(right),
                "right_coordinates": (
                    None if int(right) < 0 else coordinates(int(right))
                ),
                "to_boundary": bool(int(right) < 0),
            }
        )

    path_edges = []
    for left, right in correction_edges.tolist():
        path_edges.append(
            {
                "left_detector": int(left),
                "left_coordinates": coordinates(int(left)),
                "right_detector": None if int(right) < 0 else int(right),
                "right_coordinates": (
                    None if int(right) < 0 else coordinates(int(right))
                ),
                "to_boundary": bool(int(right) < 0),
            }
        )

    actual_list = [int(value) for value in actual.tolist()]
    predicted_list = [int(value) for value in predicted.tolist()]
    logical_failure = bool(np.any(predicted != actual))

    circuit_text = str(circuit)
    dem_text = str(dem)
    detector_bytes = syndrome.tobytes(order="C")
    actual_bytes = actual.tobytes(order="C")

    return {
        "schema_version": 1,
        "explanation_type": "single_surface_code_memory_shot",
        "configuration": {
            "distance": distance,
            "rounds": point_rounds,
            "basis": basis,
            "physical_error_rate": p,
            "seed": int(seed),
        },
        "provenance": {
            "circuit_sha256": hashlib.sha256(
                circuit_text.encode("utf-8")
            ).hexdigest(),
            "dem_sha256": hashlib.sha256(
                dem_text.encode("utf-8")
            ).hexdigest(),
            "detector_shot_sha256": hashlib.sha256(detector_bytes).hexdigest(),
            "actual_observable_sha256": hashlib.sha256(actual_bytes).hexdigest(),
        },
        "num_detectors": int(circuit.num_detectors),
        "num_observables": int(circuit.num_observables),
        "fired_detector_count": len(fired_ids),
        "fired_detectors": fired_detectors,
        "matched_detection_events": pairs,
        "correction_path_edges": path_edges,
        "actual_observables": actual_list,
        "predicted_observables": predicted_list,
        "logical_failure": logical_failure,
        "interpretation": (
            "Fired detectors are the observed detection events for one sampled "
            "surface-code memory shot. Matched detection events show which defects "
            "MWPM paired, including virtual-boundary matches. Correction path edges "
            "show the graph edges used by the MWPM solution. A logical failure means "
            "the decoder's predicted observable flips disagree with Stim's sampled "
            "logical observable for this same shot."
        ),
    }


def shot_explanation_figure(explanation: dict[str, Any]):
    """Build a matplotlib figure for one shot explanation."""
    from .plotting import new_agg_figure

    fig, ax = new_agg_figure(figsize=(8.0, 6.0))

    fired = explanation.get("fired_detectors", [])
    x_values = []
    y_values = []
    labels = []
    for item in fired:
        coords = item.get("coordinates") or []
        if len(coords) < 2:
            continue
        x_values.append(float(coords[0]))
        y_values.append(float(coords[1]))
        time_coord = coords[2] if len(coords) >= 3 else None
        label = f"D{item['detector']}"
        if time_coord is not None:
            label += f" t={time_coord:g}"
        labels.append(label)

    if x_values:
        ax.scatter(x_values, y_values, s=70)
        for x, y, label in zip(x_values, y_values, labels, strict=True):
            ax.annotate(label, (x, y), xytext=(4, 4), textcoords="offset points")

    for pair in explanation.get("matched_detection_events", []):
        if pair.get("to_boundary"):
            left = pair.get("left_coordinates") or []
            if len(left) >= 2:
                ax.annotate(
                    "boundary",
                    (float(left[0]), float(left[1])),
                    xytext=(12, -12),
                    textcoords="offset points",
                )
            continue
        left = pair.get("left_coordinates") or []
        right = pair.get("right_coordinates") or []
        if len(left) >= 2 and len(right) >= 2:
            ax.plot(
                [float(left[0]), float(right[0])],
                [float(left[1]), float(right[1])],
                linestyle="--",
            )

    config = explanation["configuration"]
    outcome = (
        "logical failure"
        if explanation["logical_failure"]
        else "logical success"
    )
    ax.set_title(
        "Aegis QEC one-shot MWPM explanation\n"
        f"d={config['distance']}, p={config['physical_error_rate']:.4g}, "
        f"basis={config['basis'].upper()} — {outcome}"
    )
    ax.set_xlabel("Detector coordinate x")
    ax.set_ylabel("Detector coordinate y")
    ax.grid(True, alpha=0.25)
    ax.set_aspect("equal", adjustable="datalim")
    fig.tight_layout()
    return fig


def write_shot_explanation(
    explanation: dict[str, Any],
    *,
    json_path: str | None = "research_out/shot-explanation.json",
    plot_path: str | None = "research_out/shot-explanation.png",
) -> None:
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(explanation, handle, indent=2, sort_keys=True)
            handle.write("\n")

    if not plot_path:
        return

    path = Path(plot_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = shot_explanation_figure(explanation)
    fig.savefig(path, dpi=180)
    fig.clear()
