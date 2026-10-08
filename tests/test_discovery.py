from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis_qec.discovery import (
    _atomic_json_write,
    load_discovery_manifest,
    pareto_front,
    run_discovery,
    write_discovery_starter,
)


def _tiny_discovery(tmp_path):
    base = tmp_path / "base.json"
    base.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "tiny-discovery-study",
                "operation": "study",
                "parameters": {
                    "distances": [3],
                    "physical_error_rates": [0.02],
                    "shots": 8,
                    "basis": "x",
                    "rounds": 3,
                    "seed": 1234,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    discovery = tmp_path / "discovery.json"
    discovery.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "tiny-search",
                "base_experiment": "base.json",
                "algorithm": "evolutionary",
                "seed": 41,
                "budget": 3,
                "population_size": 2,
                "mutation_probability": 0.5,
                "parameters": [
                    {
                        "path": "/parameters/distances/0",
                        "type": "choice",
                        "values": [3, 5],
                    },
                    {
                        "path": "/parameters/rounds",
                        "type": "choice",
                        "values": [3, 5],
                    },
                ],
                "objectives": [
                    {
                        "name": "logical_error_rate",
                        "json_pointer": "/result/points/0/logical_error_rate",
                        "direction": "minimize",
                    },
                    {
                        "name": "detectors",
                        "json_pointer": "/result/points/0/detectors",
                        "direction": "minimize",
                    },
                ],
                "confirmation_overrides": {
                    "/parameters/shots": 32
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return base, discovery


def test_pareto_front_preserves_non_dominated_tradeoffs():
    discovery = {
        "objectives": [
            {"name": "error", "direction": "minimize"},
            {"name": "speed", "direction": "maximize"},
        ]
    }
    candidates = [
        {
            "key": "a",
            "status": "success",
            "objectives": {"error": 0.01, "speed": 100.0},
        },
        {
            "key": "b",
            "status": "success",
            "objectives": {"error": 0.02, "speed": 200.0},
        },
        {
            "key": "c",
            "status": "success",
            "objectives": {"error": 0.03, "speed": 90.0},
        },
    ]

    assert {item["key"] for item in pareto_front(candidates, discovery)} == {
        "a",
        "b",
    }


def test_discovery_starter_creates_runnable_base_and_config(tmp_path):
    discovery = tmp_path / "discovery.json"
    created = write_discovery_starter(str(discovery))

    assert discovery.is_file()
    assert (tmp_path / "discovery-experiment.json").is_file()
    loaded = load_discovery_manifest(str(discovery))
    assert loaded["algorithm"] == "evolutionary"
    assert loaded["budget"] == 16
    assert len(loaded["objectives"]) == 2
    assert created["discovery_path"] == str(discovery.resolve())


def test_tiny_discovery_is_resumable_and_exports_confirmation(tmp_path):
    _, discovery = _tiny_discovery(tmp_path)
    output = tmp_path / "search"

    first = run_discovery(str(discovery), output_dir=str(output))
    assert first["exploratory"] is True
    assert 1 <= first["evaluated"] <= 3
    assert first["successful"] >= 1
    assert first["pareto_front"]
    assert first["confirmation_manifests"]

    state_before = json.loads(
        (output / "discovery-state.json").read_text(encoding="utf-8")
    )
    second = run_discovery(str(discovery), output_dir=str(output))
    state_after = json.loads(
        (output / "discovery-state.json").read_text(encoding="utf-8")
    )

    assert state_before["evaluation_order"] == state_after["evaluation_order"]
    assert second["pareto_front"] == first["pareto_front"]

    confirmation_path = first["confirmation_manifests"][0]["path"]
    confirmation = json.loads(
        open(confirmation_path, "r", encoding="utf-8").read()
    )
    assert confirmation["parameters"]["shots"] == 32
    assert confirmation["parameters"]["seed"] != 1234
    assert "discovery_provenance" in confirmation
    assert "not executed" in confirmation["discovery_provenance"]["note"]


def test_discovery_resume_rejects_changed_configuration(tmp_path):
    _, discovery = _tiny_discovery(tmp_path)
    output = tmp_path / "search"
    run_discovery(str(discovery), output_dir=str(output))

    value = json.loads(discovery.read_text(encoding="utf-8"))
    value["seed"] = 42
    discovery.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="different config"):
        run_discovery(str(discovery), output_dir=str(output))


def test_discovery_rejects_objective_without_json_pointer(tmp_path):
    _, discovery = _tiny_discovery(tmp_path)
    value = json.loads(discovery.read_text(encoding="utf-8"))
    value["objectives"][0]["json_pointer"] = "result/value"
    discovery.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="JSON pointer"):
        load_discovery_manifest(str(discovery))


def test_discovery_resume_rejects_altered_run_evidence(tmp_path):
    _, discovery = _tiny_discovery(tmp_path)
    output = tmp_path / "search"
    run_discovery(str(discovery), output_dir=str(output))

    state = json.loads(
        (output / "discovery-state.json").read_text(encoding="utf-8")
    )
    successful = [
        state["candidates"][key]
        for key in state["evaluation_order"]
        if state["candidates"][key]["status"] == "success"
    ]
    assert successful
    record_path = Path(successful[0]["run_record_path"])
    record_path.write_text('{"tampered": true}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="stored candidate result changed"):
        run_discovery(str(discovery), output_dir=str(output))


def test_discovery_resume_rejects_changed_candidate_assignment(tmp_path):
    _, discovery = _tiny_discovery(tmp_path)
    output = tmp_path / "search"
    run_discovery(str(discovery), output_dir=str(output))

    state_path = output / "discovery-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    candidate = state["candidates"][state["evaluation_order"][0]]
    candidate["assignment"]["/parameters/distances/0"] = 123
    state_path.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="assignment changed"):
        run_discovery(str(discovery), output_dir=str(output))


def test_checkpoint_replacement_failure_preserves_previous_state(tmp_path, monkeypatch):
    from aegis_qec import discovery

    state_path = tmp_path / "state.json"
    _atomic_json_write(state_path, {"completed": 1})

    def fail_replace(source, destination):
        raise OSError("simulated interrupted replacement")

    monkeypatch.setattr(discovery.os, "replace", fail_replace)
    with pytest.raises(OSError, match="interrupted"):
        _atomic_json_write(state_path, {"completed": 2})

    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "completed": 1
    }
    assert not list(tmp_path.glob(".aegis-discovery-*.tmp"))
