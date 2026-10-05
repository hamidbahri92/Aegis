from __future__ import annotations

import json

import pytest

pytest.importorskip("stim")
pytest.importorskip("pymatching")

from aegis_qec.explain import explain_surface_code_shot, write_shot_explanation


def test_single_shot_explanation_is_deterministic_and_consistent(tmp_path):
    first = explain_surface_code_shot(
        distance=3,
        physical_error_rate=0.08,
        basis="x",
        seed=20261005,
    )
    second = explain_surface_code_shot(
        distance=3,
        physical_error_rate=0.08,
        basis="x",
        seed=20261005,
    )

    assert first["provenance"] == second["provenance"]
    assert first["fired_detectors"] == second["fired_detectors"]
    assert first["matched_detection_events"] == second["matched_detection_events"]
    assert first["predicted_observables"] == second["predicted_observables"]
    assert first["actual_observables"] == second["actual_observables"]

    expected_failure = (
        first["predicted_observables"] != first["actual_observables"]
    )
    assert first["logical_failure"] is expected_failure

    fired = {item["detector"] for item in first["fired_detectors"]}
    for pair in first["matched_detection_events"]:
        assert pair["left_detector"] in fired
        if not pair["to_boundary"]:
            assert pair["right_detector"] in fired

    out = tmp_path / "explanation.json"
    write_shot_explanation(first, json_path=str(out), plot_path=None)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["configuration"]["distance"] == 3
    assert len(loaded["provenance"]["detector_shot_sha256"]) == 64


def test_single_shot_explanation_validates_configuration():
    with pytest.raises(ValueError, match="odd integer"):
        explain_surface_code_shot(distance=4)
    with pytest.raises(ValueError, match="basis"):
        explain_surface_code_shot(basis="y")
