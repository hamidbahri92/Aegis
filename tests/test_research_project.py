from __future__ import annotations

import json

import pytest

from aegis_qec.project import (
    audit_research_project,
    collect_project_evidence,
    freeze_research_protocol,
    run_research_project,
    verify_protocol_lock,
    write_research_project_template,
)


def _write_project(path, *, artifact_path=None):
    artifacts = []
    claims = []
    if artifact_path is not None:
        artifacts = [
            {
                "id": "result",
                "path": artifact_path.name,
                "kind": "result-json",
            }
        ]
        claims = [
            {
                "id": "C1",
                "type": "result",
                "text": "The measured logical error rate is below 0.1.",
                "evidence": [
                    {
                        "artifact": "result",
                        "json_pointer": "/metrics/logical_error_rate",
                        "predicate": {"lt": 0.1},
                    }
                ],
            }
        ]

    project = {
        "schema_version": 1,
        "title": "Test research project",
        "authors": [{"name": "Researcher"}],
        "research_question": "Does the tested decoder satisfy the target rate?",
        "hypotheses": [
            {
                "id": "H1",
                "text": "The logical error rate is below 0.1.",
            }
        ],
        "experiments": [],
        "artifacts": artifacts,
        "claims": claims,
        "bibliography_files": [],
        "paper": {},
    }
    path.write_text(
        json.dumps(project, indent=2) + "\n",
        encoding="utf-8",
    )


def test_project_init_creates_project_and_starter_experiment(tmp_path):
    project_path = tmp_path / "research-project.json"
    created = write_research_project_template(
        str(project_path),
        author_name="Ada Researcher",
    )

    assert project_path.is_file()
    assert (tmp_path / "experiment.json").is_file()
    assert created["project_path"] == str(project_path.resolve())

    project = json.loads(project_path.read_text(encoding="utf-8"))
    assert project["authors"][0]["name"] == "Ada Researcher"
    assert project["experiments"][0]["manifest"] == "experiment.json"


def test_claim_to_evidence_audit_and_protocol_lock(tmp_path):
    artifact = tmp_path / "result.json"
    artifact.write_text(
        json.dumps({"metrics": {"logical_error_rate": 0.05}}),
        encoding="utf-8",
    )
    project = tmp_path / "project.json"
    _write_project(project, artifact_path=artifact)

    lock = freeze_research_protocol(str(project))
    assert lock["protocol_sha256"]

    report = audit_research_project(
        str(project),
        require_protocol_lock=True,
    )
    assert report["valid"] is True
    claim = report["claims"][0]
    assert claim["passed"] is True
    assert claim["evidence"][0]["actual"] == pytest.approx(0.05)

    verification = verify_protocol_lock(
        str(project),
        str(project.with_suffix(".protocol.lock.json")),
    )
    assert verification["valid"] is True


def test_claim_predicate_failure_is_a_hard_audit_failure(tmp_path):
    artifact = tmp_path / "result.json"
    artifact.write_text(
        json.dumps({"metrics": {"logical_error_rate": 0.2}}),
        encoding="utf-8",
    )
    project = tmp_path / "project.json"
    _write_project(project, artifact_path=artifact)

    report = audit_research_project(str(project))
    assert report["valid"] is False
    assert any("predicate failed" in error for error in report["errors"])


def test_result_claim_without_evidence_fails(tmp_path):
    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["claims"] = [
        {
            "id": "C1",
            "type": "result",
            "text": "Unsupported result claim.",
            "evidence": [],
        }
    ]
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    report = audit_research_project(str(project))
    assert report["valid"] is False
    assert any("has no evidence" in error for error in report["errors"])


def test_protocol_lock_detects_project_change(tmp_path):
    project = tmp_path / "project.json"
    _write_project(project)
    freeze_research_protocol(str(project))

    value = json.loads(project.read_text(encoding="utf-8"))
    value["research_question"] = "A changed question."
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    verification = verify_protocol_lock(
        str(project),
        str(project.with_suffix(".protocol.lock.json")),
    )
    assert verification["valid"] is False
    assert any(
        "scientific protocol changed" in item
        for item in verification["failures"]
    )


def test_project_run_executes_declared_manifest_and_bundle(tmp_path):
    experiment = tmp_path / "experiment.json"
    experiment.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "tiny-project-study",
                "operation": "study",
                "parameters": {
                    "distances": [3],
                    "physical_error_rates": [0.02],
                    "shots": 8,
                    "basis": "x",
                    "seed": 1234,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["experiments"] = [{"id": "tiny", "manifest": "experiment.json"}]
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    report = run_research_project(
        str(project),
        workspace=str(tmp_path / "workspace"),
    )
    assert report["experiments"][0]["id"] == "tiny"
    assert (tmp_path / "workspace" / "tiny" / "tiny.aegis.zip").is_file()
    assert (tmp_path / "workspace" / "project-run.json").is_file()



def test_manuscript_edits_do_not_invalidate_frozen_protocol(tmp_path):
    project = tmp_path / "project.json"
    _write_project(project)
    freeze_research_protocol(str(project))

    value = json.loads(project.read_text(encoding="utf-8"))
    value["paper"] = {
        "abstract": "Edited after the experiment.",
        "methods": "Clarified wording only.",
    }
    value["claims"] = [
        {
            "id": "M1",
            "type": "method",
            "text": "The manuscript was edited after protocol freeze.",
            "evidence": [],
        }
    ]
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    verification = verify_protocol_lock(
        str(project),
        str(project.with_suffix(".protocol.lock.json")),
    )
    assert verification["valid"] is True


def test_confirmatory_freeze_requires_analysis_fields(tmp_path):
    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["protocol"] = {
        "mode": "confirmatory",
        "primary_outcome": "",
        "analysis_plan": "",
        "stopping_rule": "",
    }
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="confirmatory protocol is missing"):
        freeze_research_protocol(str(project))


def test_confirmatory_audit_requires_protocol_lock(tmp_path):
    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["protocol"] = {
        "mode": "confirmatory",
        "primary_outcome": "Logical error rate",
        "analysis_plan": "Use a pre-specified Wilson interval.",
        "stopping_rule": "Collect exactly 1000 shots.",
    }
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    report = audit_research_project(str(project))
    assert report["valid"] is False
    assert any(
        "protocol lock required" in error
        for error in report["errors"]
    )


def _write_tiny_discovery(tmp_path):
    base = tmp_path / "search-base.json"
    base.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "project-discovery-study",
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
                "base_experiment": "search-base.json",
                "algorithm": "random",
                "seed": 7,
                "budget": 1,
                "population_size": 1,
                "parameters": [
                    {
                        "path": "/parameters/rounds",
                        "type": "choice",
                        "values": [3],
                    }
                ],
                "objectives": [
                    {
                        "name": "logical_error_rate",
                        "json_pointer": "/result/points/0/logical_error_rate",
                        "direction": "minimize",
                    }
                ],
                "confirmation_overrides": {
                    "/parameters/shots": 16
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return discovery


def test_exploratory_project_runs_declared_discovery(tmp_path):
    discovery = _write_tiny_discovery(tmp_path)
    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["protocol"] = {
        "mode": "exploratory",
        "search_plan": "One-point discovery smoke test.",
    }
    value["discoveries"] = [
        {
            "id": "search",
            "manifest": discovery.name,
        }
    ]
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    audit = audit_research_project(str(project))
    assert audit["valid"] is True
    assert audit["discoveries"][0]["algorithm"] == "random"

    report = run_research_project(
        str(project),
        workspace=str(tmp_path / "workspace"),
    )
    assert report["discoveries"][0]["id"] == "search"
    assert report["discoveries"][0]["pareto_count"] == 1
    assert report["discoveries"][0]["confirmation_manifests"]


def test_confirmatory_project_rejects_adaptive_discovery(tmp_path):
    discovery = _write_tiny_discovery(tmp_path)
    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["protocol"] = {
        "mode": "confirmatory",
        "primary_outcome": "Logical error rate",
        "analysis_plan": "Use a fixed Wilson interval.",
        "stopping_rule": "Exactly eight shots.",
    }
    value["discoveries"] = [
        {
            "id": "search",
            "manifest": discovery.name,
        }
    ]
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="confirmatory projects cannot contain adaptive discovery",
    ):
        freeze_research_protocol(str(project))


def test_collect_project_evidence_pins_hashes_and_is_idempotent(tmp_path):
    experiment = tmp_path / "experiment.json"
    experiment.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "evidence-collection-study",
                "operation": "study",
                "parameters": {
                    "distances": [3],
                    "physical_error_rates": [0.02],
                    "shots": 8,
                    "basis": "x",
                    "seed": 1234,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["experiments"] = [{"id": "tiny", "manifest": experiment.name}]
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )
    freeze_research_protocol(str(project))

    run = run_research_project(
        str(project),
        workspace=str(tmp_path / "workspace"),
    )
    collected = collect_project_evidence(str(project), run["path"])
    assert any(item.startswith("run-") for item in collected["added"])
    assert any(
        item.endswith("-experiment-tiny-study_json")
        for item in collected["added"]
    )

    audit = audit_research_project(str(project), require_protocol_lock=True)
    assert audit["valid"] is True
    assert all(item["sha256"] for item in audit["artifacts"].values())

    repeated = collect_project_evidence(str(project), run["path"])
    assert repeated["added"] == []

    result_path = tmp_path / "workspace" / "tiny" / "study.json"
    result_path.write_text('{"tampered": true}\n', encoding="utf-8")
    audit = audit_research_project(str(project))
    assert audit["valid"] is False
    assert any("hash mismatch" in message for message in audit["errors"])


def test_collect_project_evidence_refuses_tampered_run_file(tmp_path):
    experiment = tmp_path / "experiment.json"
    experiment.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "tamper-check-study",
                "operation": "study",
                "parameters": {
                    "distances": [3],
                    "physical_error_rates": [0.02],
                    "shots": 8,
                    "basis": "x",
                    "seed": 1234,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    project = tmp_path / "project.json"
    _write_project(project)
    original = json.loads(project.read_text(encoding="utf-8"))
    original["experiments"] = [{"id": "tiny", "manifest": "experiment.json"}]
    project.write_text(
        json.dumps(original, indent=2) + "\n",
        encoding="utf-8",
    )
    run = run_research_project(
        str(project),
        workspace=str(tmp_path / "workspace"),
    )
    result_path = tmp_path / "workspace" / "tiny" / "study.json"
    result_path.write_text('{"tampered": true}\n', encoding="utf-8")

    before = project.read_bytes()
    with pytest.raises(ValueError, match="hash mismatch"):
        collect_project_evidence(str(project), run["path"])
    assert project.read_bytes() == before


def test_evidence_collection_rejects_changed_experiment_definition(tmp_path):
    experiment = tmp_path / "experiment.json"
    experiment.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "manifest-integrity",
                "operation": "study",
                "parameters": {
                    "distances": [3],
                    "physical_error_rates": [0.02],
                    "shots": 8,
                    "basis": "x",
                    "seed": 1234,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    project = tmp_path / "project.json"
    _write_project(project)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["experiments"] = [{"id": "tiny", "manifest": experiment.name}]
    project.write_text(json.dumps(value) + "\n", encoding="utf-8")
    run = run_research_project(
        str(project),
        workspace=str(tmp_path / "workspace"),
    )
    before = project.read_bytes()
    definition = json.loads(experiment.read_text(encoding="utf-8"))
    definition["parameters"]["shots"] = 100
    experiment.write_text(json.dumps(definition) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="executed experiment manifest changed"):
        collect_project_evidence(str(project), run["path"])
    assert project.read_bytes() == before
