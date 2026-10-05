from __future__ import annotations

import csv
import json

import pytest

pytest.importorskip("stim")

from aegis_qec.research import (
    run_surface_code_study,
    wilson_interval,
    write_study_artifacts,
)


def test_wilson_interval_contains_observed_rate():
    low, high = wilson_interval(12, 100)
    assert 0.0 <= low <= 0.12 <= high <= 1.0


def test_surface_code_study_is_reproducible_and_records_environment():
    first = run_surface_code_study(
        distances=[3],
        physical_error_rates=[0.02],
        shots=64,
        basis="x",
        seed=20261005,
    )
    second = run_surface_code_study(
        distances=[3],
        physical_error_rates=[0.02],
        shots=64,
        basis="x",
        seed=20261005,
    )

    assert first["study_type"] == "stim_rotated_surface_code_memory"
    assert first["parameters"]["rounds"] == "distance"
    assert first["environment"]["stim"]
    assert first["environment"]["pymatching"]
    assert len(first["points"]) == 1

    point = first["points"][0]
    second_point = second["points"][0]

    assert point["distance"] == 3
    assert point["rounds"] == 3
    assert point["shots"] == 64
    assert 0 <= point["logical_failures"] <= 64
    assert 0.0 <= point["ci95_low"] <= point["logical_error_rate"] <= point["ci95_high"] <= 1.0
    assert len(point["circuit_sha256"]) == 64
    assert len(point["dem_sha256"]) == 64
    assert point["circuit_sha256"] == second_point["circuit_sha256"]
    assert point["dem_sha256"] == second_point["dem_sha256"]
    assert point["logical_failures"] == second_point["logical_failures"]
    assert point["detection_events"] == second_point["detection_events"]


def test_study_artifact_export_round_trips(tmp_path):
    study = run_surface_code_study(
        distances=[3],
        physical_error_rates=[0.01],
        shots=32,
        basis="z",
        rounds=3,
        seed=7,
    )

    json_path = tmp_path / "study.json"
    csv_path = tmp_path / "study.csv"
    write_study_artifacts(
        study,
        json_path=str(json_path),
        csv_path=str(csv_path),
    )

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["parameters"]["basis"] == "z"
    assert loaded["points"][0]["shots"] == 32

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["distance"] == "3"
    assert rows[0]["basis"] == "z"
