from __future__ import annotations

import json
from pathlib import Path

from aegis_qec.paper import (
    build_submission_package,
    verify_submission_package,
)
from aegis_qec.project import freeze_research_protocol


def _project_with_evidence(tmp_path: Path) -> Path:
    artifact = tmp_path / "evaluation.json"
    artifact.write_text(
        json.dumps(
            {
                "dataset": {"selected_shots": 100},
                "rows": [
                    {
                        "decoder": "aegis-pymatching",
                        "logical_error_rate": 0.04,
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    experiment = tmp_path / "experiment.json"
    experiment.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "paper-package-study",
                "operation": "study",
                "parameters": {
                    "distances": [3],
                    "physical_error_rates": [0.02],
                    "shots": 8,
                    "basis": "x",
                    "seed": 1234
                }
            },
            indent=2
        )
        + "\n",
        encoding="utf-8",
    )

    bibliography = tmp_path / "references.bib"
    bibliography.write_text(
        "@article{example,title={Example reference},author={Researcher, Ada},year={2026}}\n",
        encoding="utf-8",
    )

    project = tmp_path / "project.json"
    project.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "Evidence-bound QEC study",
                "authors": [
                    {
                        "name": "Ada Researcher",
                        "affiliation": "Example Lab",
                        "email": "ada@example.org",
                    }
                ],
                "keywords": ["QEC", "surface code"],
                "research_question": "Does the decoder remain below the target error rate?",
                "hypotheses": [
                    {
                        "id": "H1",
                        "text": "Logical error rate is below 0.1.",
                    }
                ],
                "experiments": [
                    {
                        "id": "study",
                        "manifest": "experiment.json"
                    }
                ],
                "artifacts": [
                    {
                        "id": "evaluation",
                        "path": "evaluation.json",
                        "kind": "dataset-evaluation",
                    }
                ],
                "claims": [
                    {
                        "id": "C1",
                        "type": "result",
                        "text": "The logical error rate is below 0.1.",
                        "evidence": [
                            {
                                "artifact": "evaluation",
                                "json_pointer": "/rows/0/logical_error_rate",
                                "predicate": {"lt": 0.1},
                            }
                        ],
                    }
                ],
                "bibliography_files": ["references.bib"],
                "code_url": "https://example.org/code",
                "data_url": "https://example.org/data",
                "reproduction_commands": [
                    "aegis project audit project.json",
                ],
                "compute_resources": [
                    {
                        "description": "Small deterministic CPU validation",
                        "cpu": "2 virtual CPU cores",
                        "memory": "4 GB",
                        "wall_time": "under one minute",
                    }
                ],
                "paper": {
                    "abstract": "A reproducible test of a QEC decoder.",
                    "statement_of_need": "QEC comparisons need reusable evidence.",
                    "state_of_field": "Existing tools cover simulation and decoding.",
                    "software_design": "The study uses evidence-bound artifacts.",
                    "methods": "We evaluated a fixed stored workload.",
                    "results_context": "The declared result is listed below.",
                    "limitations": "The result is limited to this workload.",
                    "impact": "The workflow improves reviewability.",
                    "data_availability": "The evidence is included in the package.",
                    "code_availability": "Aegis QEC is open source.",
                    "ai_usage_disclosure": (
                        "AI assistance was used for software development and "
                        "drafting; human authors reviewed and validated outputs."
                    ),
                    "competing_interests": "None declared.",
                    "funding": "No external funding.",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    freeze_research_protocol(str(project))
    return project


def test_submission_package_contains_manuscript_and_evidence(tmp_path):
    project = _project_with_evidence(tmp_path)
    output = tmp_path / "submission"

    report = build_submission_package(
        str(project),
        output_dir=str(output),
        compile_mode="never",
        require_protocol_lock=True,
    )

    assert report["audit_valid"] is True
    assert report["submission_ready"] is True
    assert (output / "manuscript" / "paper.tex").is_file()
    assert (output / "manuscript" / "paper.md").is_file()
    assert (output / "manuscript" / "references.bib").is_file()
    assert (output / "CLAIM_EVIDENCE.md").is_file()
    assert (output / "REVIEWER_README.md").is_file()
    assert (output / "REPRODUCE.md").is_file()
    assert (output / "MANIFEST.json").is_file()
    assert (output / "submission-readiness.json").is_file()
    assert (output / "experiment-inventory.json").is_file()
    assert (output / "experiments" / "study.json").is_file()
    assert (output / "croissant-inventory.json").is_file()
    assert Path(report["zip_path"]).is_file()

    directory_check = verify_submission_package(str(output))
    zip_check = verify_submission_package(report["zip_path"])
    assert directory_check["valid"] is True
    assert zip_check["valid"] is True


def test_submission_verifier_detects_payload_tampering(tmp_path):
    project = _project_with_evidence(tmp_path)
    output = tmp_path / "submission"
    build_submission_package(
        str(project),
        output_dir=str(output),
        compile_mode="never",
    )

    packaged = output / "artifacts" / "evaluation" / "evaluation.json"
    packaged.write_text('{"tampered": true}\n', encoding="utf-8")

    report = verify_submission_package(str(output))
    assert report["valid"] is False
    assert any("hash mismatch" in failure for failure in report["failures"])


def test_anonymous_package_redacts_author_and_local_paths(tmp_path):
    project = _project_with_evidence(tmp_path)
    output = tmp_path / "anonymous"

    build_submission_package(
        str(project),
        output_dir=str(output),
        compile_mode="never",
        anonymize=True,
    )

    packaged_project = (output / "research-project.json").read_text(
        encoding="utf-8"
    )
    audit = (output / "audit.json").read_text(encoding="utf-8")
    tex = (output / "manuscript" / "paper.tex").read_text(encoding="utf-8")
    inventory = (output / "artifact-inventory.json").read_text(
        encoding="utf-8"
    )

    assert "Ada Researcher" not in packaged_project
    assert "ada@example.org" not in packaged_project
    assert "https://example.org/code" not in packaged_project
    assert "https://example.org/data" not in packaged_project
    assert "Ada Researcher" not in tex
    assert str(tmp_path) not in audit
    assert str(tmp_path) not in inventory
    assert "Anonymous Authors" in packaged_project
    assert "Anonymous Authors" in tex


def test_submission_build_refuses_destructive_overwrite(tmp_path):
    project = _project_with_evidence(tmp_path)
    output = tmp_path / "submission"
    output.mkdir()
    (output / "keep.txt").write_text("keep", encoding="utf-8")

    try:
        build_submission_package(
            str(project),
            output_dir=str(output),
            compile_mode="never",
        )
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing submission directory should be protected")

    assert (output / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_dataset_artifact_emits_croissant_metadata(tmp_path):
    project = _project_with_evidence(tmp_path)
    value = json.loads(project.read_text(encoding="utf-8"))
    dataset = tmp_path / "syndromes.h5"
    dataset.write_bytes(b"test-dataset-bytes")
    value["artifacts"].append(
        {
            "id": "dataset",
            "path": "syndromes.h5",
            "kind": "dataset",
            "name": "Shared QEC syndrome dataset",
            "description": "Detector syndromes and logical observables.",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "url": "https://example.org/datasets/syndromes.h5",
            "encoding_format": "application/x-hdf5",
            "croissant": True,
        }
    )
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )
    freeze_research_protocol(str(project))

    output = tmp_path / "submission-croissant"
    report = build_submission_package(
        str(project),
        output_dir=str(output),
        compile_mode="never",
        require_protocol_lock=True,
    )

    croissant_path = (
        output
        / "dataset-metadata"
        / "dataset"
        / "croissant.json"
    )
    metadata = json.loads(croissant_path.read_text(encoding="utf-8"))
    assert metadata["@type"] == "sc:Dataset"
    assert metadata["conformsTo"] == "http://mlcommons.org/croissant/1.0"
    assert metadata["distribution"][0]["sha256"]
    assert report["croissant_count"] == 1


def test_submission_integrity_can_pass_while_readiness_fails(tmp_path):
    project = _project_with_evidence(tmp_path)
    value = json.loads(project.read_text(encoding="utf-8"))
    value["code_url"] = ""
    value["paper"]["code_availability"] = ""
    value["bibliography_files"] = []
    project.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )
    freeze_research_protocol(str(project))

    output = tmp_path / "draft-submission"
    report = build_submission_package(
        str(project),
        output_dir=str(output),
        compile_mode="never",
        require_protocol_lock=True,
    )
    assert report["audit_valid"] is True
    assert report["submission_ready"] is False

    verified = verify_submission_package(report["zip_path"])
    assert verified["valid"] is True
