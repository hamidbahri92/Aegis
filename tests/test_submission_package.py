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
                "experiments": [],
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
                "bibliography_files": [],
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
    assert (output / "manuscript" / "paper.tex").is_file()
    assert (output / "manuscript" / "paper.md").is_file()
    assert (output / "manuscript" / "references.bib").is_file()
    assert (output / "CLAIM_EVIDENCE.md").is_file()
    assert (output / "REVIEWER_README.md").is_file()
    assert (output / "REPRODUCE.md").is_file()
    assert (output / "MANIFEST.json").is_file()
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
