from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Sequence

from .decoder_plugins import custom_decoder_registry
from .research import wilson_interval


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _require_campaign_dependencies():
    try:
        import sinter
        import stim
    except ImportError as exc:
        raise RuntimeError(
            "Aegis campaigns require Stim/Sinter. Install with: "
            "python -m pip install -U 'aegis-qec[full]'"
        ) from exc
    return sinter, stim


def resolve_workers(workers: int | str) -> int:
    if workers == "auto":
        return max(1, int(os.cpu_count() or 1))
    value = int(workers)
    if value < 1:
        raise ValueError("workers must be a positive integer or 'auto'")
    return value


def _generated_tasks(
    *,
    distances: Sequence[int],
    physical_error_rates: Sequence[float],
    basis: str,
    rounds: int | None,
):
    sinter, stim = _require_campaign_dependencies()
    tasks = []
    for distance in distances:
        distance = int(distance)
        if distance < 3 or distance % 2 == 0:
            raise ValueError("campaign distances must be odd integers >= 3")
        point_rounds = int(rounds) if rounds is not None else distance
        if point_rounds < 1:
            raise ValueError("rounds must be positive")

        for p in physical_error_rates:
            p = float(p)
            if not 0.0 <= p < 0.5:
                raise ValueError("physical error probabilities must satisfy 0 <= p < 0.5")
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
            circuit_text = str(circuit)
            dem_text = str(dem)
            task = sinter.Task(
                circuit=circuit,
                detector_error_model=dem,
                json_metadata={
                    "source": "generated",
                    "code": "rotated_surface_code_memory",
                    "basis": basis,
                    "distance": distance,
                    "rounds": point_rounds,
                    "physical_error_rate": p,
                    "circuit_sha256": hashlib.sha256(
                        circuit_text.encode("utf-8")
                    ).hexdigest(),
                    "dem_sha256": hashlib.sha256(
                        dem_text.encode("utf-8")
                    ).hexdigest(),
                },
            )
            tasks.append(task)
    return tasks


def _file_tasks(circuit_paths: Sequence[str]):
    sinter, stim = _require_campaign_dependencies()
    tasks = []
    for raw_path in circuit_paths:
        path = Path(raw_path)
        circuit = stim.Circuit.from_file(path)
        dem = circuit.detector_error_model(decompose_errors=True)
        circuit_text = str(circuit)
        dem_text = str(dem)
        tasks.append(
            sinter.Task(
                circuit=circuit,
                detector_error_model=dem,
                json_metadata={
                    "source": "stim-file",
                    "file_name": path.name,
                    "circuit_sha256": hashlib.sha256(
                        circuit_text.encode("utf-8")
                    ).hexdigest(),
                    "dem_sha256": hashlib.sha256(
                        dem_text.encode("utf-8")
                    ).hexdigest(),
                    "num_detectors": int(circuit.num_detectors),
                    "num_observables": int(circuit.num_observables),
                },
            )
        )
    return tasks


def build_campaign_tasks(
    *,
    distances: Sequence[int] = (3, 5, 7),
    physical_error_rates: Sequence[float] = (0.003, 0.006, 0.01),
    basis: str = "x",
    rounds: int | None = None,
    circuit_paths: Sequence[str] = (),
):
    basis = str(basis).lower()
    if basis not in {"x", "z"}:
        raise ValueError("basis must be 'x' or 'z'")

    if circuit_paths:
        return _file_tasks(circuit_paths)

    if not distances:
        raise ValueError("at least one distance is required")
    if not physical_error_rates:
        raise ValueError("at least one physical error probability is required")

    return _generated_tasks(
        distances=distances,
        physical_error_rates=physical_error_rates,
        basis=basis,
        rounds=rounds,
    )


def _stat_to_row(stat: Any) -> dict[str, Any]:
    accepted_shots = int(stat.shots) - int(stat.discards)
    if accepted_shots > 0:
        error_rate = float(stat.errors) / accepted_shots
        ci_low, ci_high = wilson_interval(int(stat.errors), accepted_shots)
    else:
        error_rate = None
        ci_low = None
        ci_high = None

    custom_counts = {str(k): int(v) for k, v in stat.custom_counts.items()}
    det_events = custom_counts.get("detection_events")
    det_checked = custom_counts.get("detectors_checked")
    detection_fraction = (
        float(det_events / det_checked)
        if det_events is not None and det_checked
        else None
    )

    return {
        "strong_id": stat.strong_id,
        "decoder": stat.decoder,
        "metadata": stat.json_metadata,
        "shots": int(stat.shots),
        "accepted_shots": accepted_shots,
        "errors": int(stat.errors),
        "discards": int(stat.discards),
        "logical_error_rate": error_rate,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "seconds": float(stat.seconds),
        "shots_per_cpu_second": (
            float(stat.shots / stat.seconds) if stat.seconds > 0 else None
        ),
        "detection_fraction": detection_fraction,
        "custom_counts": custom_counts,
    }


def run_campaign(
    *,
    distances: Sequence[int] = (3, 5, 7),
    physical_error_rates: Sequence[float] = (0.003, 0.006, 0.01),
    basis: str = "x",
    rounds: int | None = None,
    circuit_paths: Sequence[str] = (),
    decoders: Sequence[str] = ("pymatching", "aegis-pymatching"),
    workers: int | str = "auto",
    max_shots: int = 100_000,
    max_errors: int | None = 1000,
    resume_csv: str = "research_out/campaign.csv",
    max_batch_seconds: int | None = 30,
    include_external_plugins: bool = True,
    print_progress: bool = True,
) -> dict[str, Any]:
    """Run a resumable multiprocessing QEC campaign using Sinter."""

    sinter, _ = _require_campaign_dependencies()
    if max_shots < 1:
        raise ValueError("max_shots must be positive")
    if max_errors is not None and max_errors < 1:
        raise ValueError("max_errors must be positive when provided")
    if not decoders:
        raise ValueError("at least one decoder is required")

    tasks = build_campaign_tasks(
        distances=distances,
        physical_error_rates=physical_error_rates,
        basis=basis,
        rounds=rounds,
        circuit_paths=circuit_paths,
    )
    worker_count = resolve_workers(workers)
    registry = custom_decoder_registry(
        include_external=include_external_plugins
    )

    resume_path = Path(resume_csv)
    resume_path.parent.mkdir(parents=True, exist_ok=True)

    stats = sinter.collect(
        num_workers=worker_count,
        tasks=tasks,
        decoders=list(decoders),
        custom_decoders=registry,
        max_shots=int(max_shots),
        max_errors=None if max_errors is None else int(max_errors),
        max_batch_seconds=max_batch_seconds,
        count_detection_events=True,
        save_resume_filepath=resume_path,
        print_progress=bool(print_progress),
    )

    rows = sorted(
        (_stat_to_row(stat) for stat in stats),
        key=lambda row: (
            str(row["decoder"]),
            str(row["metadata"]),
        ),
    )

    return {
        "schema_version": 1,
        "campaign_type": "sinter_qec_campaign",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "aegis_qec": _distribution_version("aegis-qec") or "source-checkout",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "stim": _distribution_version("stim"),
            "pymatching": _distribution_version("pymatching"),
        },
        "configuration": {
            "workers": worker_count,
            "decoders": list(decoders),
            "max_shots": int(max_shots),
            "max_errors": max_errors,
            "max_batch_seconds": max_batch_seconds,
            "resume_csv": str(resume_path),
            "basis": basis,
            "rounds": rounds if rounds is not None else "distance",
            "distances": [int(v) for v in distances],
            "physical_error_rates": [float(v) for v in physical_error_rates],
            "circuit_paths": [str(v) for v in circuit_paths],
        },
        "rows": rows,
        "interpretation": (
            "Sinter campaigns are resumable parallel Monte Carlo collections. "
            "Different decoder task rows are statistically comparable but are not "
            "guaranteed to contain identical sampled shots. Use Aegis exact-shot "
            "comparison when paired per-shot decoder comparison is required."
        ),
    }


def write_campaign_summary(
    campaign: dict[str, Any],
    *,
    json_path: str | None = "research_out/campaign.json",
    plot_path: str | None = "research_out/campaign.png",
) -> None:
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(campaign, handle, indent=2, sort_keys=True)
            handle.write("\n")

    if not plot_path:
        return

    import matplotlib.pyplot as plt

    rows = [
        row
        for row in campaign.get("rows", [])
        if row.get("logical_error_rate") is not None
        and isinstance(row.get("metadata"), dict)
        and row["metadata"].get("physical_error_rate") is not None
        and row["metadata"].get("distance") is not None
    ]
    if not rows:
        return

    path = Path(plot_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    series = sorted(
        {
            (str(row["decoder"]), int(row["metadata"]["distance"]))
            for row in rows
        }
    )
    for decoder, distance in series:
        selected = sorted(
            (
                row
                for row in rows
                if str(row["decoder"]) == decoder
                and int(row["metadata"]["distance"]) == distance
            ),
            key=lambda row: float(row["metadata"]["physical_error_rate"]),
        )
        x_values = [
            float(row["metadata"]["physical_error_rate"]) for row in selected
        ]
        y_values = [float(row["logical_error_rate"]) for row in selected]
        lower = [
            max(0.0, y - float(row["ci95_low"]))
            for y, row in zip(y_values, selected, strict=True)
        ]
        upper = [
            max(0.0, float(row["ci95_high"]) - y)
            for y, row in zip(y_values, selected, strict=True)
        ]
        ax.errorbar(
            x_values,
            y_values,
            yerr=[lower, upper],
            marker="o",
            capsize=3,
            label=f"{decoder}, d={distance}",
        )

    if all(value > 0 for value in [
        float(row["metadata"]["physical_error_rate"]) for row in rows
    ]):
        ax.set_xscale("log")
    ax.set_xlabel("Physical error probability p")
    ax.set_ylabel("Logical error rate")
    ax.set_title("Aegis QEC resumable Sinter campaign")
    ax.set_ylim(bottom=0.0)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)
