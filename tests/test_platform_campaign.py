from __future__ import annotations

import json

import pytest

pytest.importorskip("stim")
pytest.importorskip("sinter")

from aegis_qec.campaign import build_campaign_tasks, resolve_workers
from aegis_qec.comparison import compare_decoders_exact_shots
from aegis_qec.decoder_plugins import available_decoders, custom_decoder_registry


def test_campaign_task_has_strong_provenance_metadata():
    tasks = build_campaign_tasks(
        distances=[3],
        physical_error_rates=[0.01],
        basis="x",
    )
    assert len(tasks) == 1
    task = tasks[0]
    assert task.json_metadata["distance"] == 3
    assert task.json_metadata["rounds"] == 3
    assert task.json_metadata["physical_error_rate"] == 0.01
    assert len(task.json_metadata["circuit_sha256"]) == 64
    assert len(task.json_metadata["dem_sha256"]) == 64


def test_decoder_registry_exposes_aegis_sinter_decoders():
    names = available_decoders(include_external=False)
    assert "aegis-pymatching" in names
    assert "aegis-pymatching-correlated" in names

    registry = custom_decoder_registry(include_external=False)
    assert hasattr(registry["aegis-pymatching"], "compile_decoder_for_dem")


def test_exact_shot_comparison_is_reproducible():
    first = compare_decoders_exact_shots(
        decoders=["aegis-pymatching", "aegis-pymatching-correlated"],
        shots=64,
        seed=20261005,
        distance=3,
        physical_error_rate=0.02,
        basis="x",
        include_external_plugins=False,
    )
    second = compare_decoders_exact_shots(
        decoders=["aegis-pymatching", "aegis-pymatching-correlated"],
        shots=64,
        seed=20261005,
        distance=3,
        physical_error_rate=0.02,
        basis="x",
        include_external_plugins=False,
    )

    assert first["provenance"]["detector_sample_sha256"] == second["provenance"][
        "detector_sample_sha256"
    ]
    assert first["provenance"]["observable_sample_sha256"] == second["provenance"][
        "observable_sample_sha256"
    ]
    assert [row["errors"] for row in first["rows"]] == [
        row["errors"] for row in second["rows"]
    ]
    assert first["pairwise_disagreements"] == second["pairwise_disagreements"]


def test_resolve_workers_validation():
    assert resolve_workers(1) == 1
    assert resolve_workers("1") == 1
    assert resolve_workers("auto") >= 1
    with pytest.raises(ValueError):
        resolve_workers(0)


def test_comparison_is_json_serializable():
    result = compare_decoders_exact_shots(
        decoders=["aegis-pymatching"],
        shots=8,
        seed=3,
        distance=3,
        physical_error_rate=0.01,
        include_external_plugins=False,
    )
    json.dumps(result, allow_nan=False)
