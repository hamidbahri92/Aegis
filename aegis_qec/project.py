from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_PROJECT_SCHEMA_VERSION = 1
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_safe_id(value: str, *, field: str) -> str:
    value = str(value)
    if not _SAFE_ID_RE.fullmatch(value):
        raise ValueError(
            f"{field} must match {_SAFE_ID_RE.pattern!r}; got {value!r}"
        )
    return value


def _resolve_path(project_path: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project_path.parent / path
    return path.resolve()


def _json_pointer_get(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError(
            f"JSON pointer must be empty or start with '/': {pointer!r}"
        )
    current = value
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            try:
                index = int(token)
            except ValueError as exc:
                raise KeyError(
                    f"JSON pointer list token is not an integer: {token!r}"
                ) from exc
            current = current[index]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise KeyError(
                f"JSON pointer {pointer!r} traversed into a scalar at {token!r}"
            )
    return current


def _predicate_result(actual: Any, predicate: dict[str, Any]) -> tuple[bool, str]:
    if not predicate:
        return True, "no predicate"

    known = {"eq", "ne", "lt", "lte", "gt", "gte", "between"}
    unknown = set(predicate) - known
    if unknown:
        raise ValueError(
            "unknown evidence predicate(s): " + ", ".join(sorted(unknown))
        )
    if len(predicate) != 1:
        raise ValueError("evidence predicate must contain exactly one operator")

    operator, expected = next(iter(predicate.items()))
    if operator == "eq":
        passed = actual == expected
    elif operator == "ne":
        passed = actual != expected
    elif operator == "lt":
        passed = actual < expected
    elif operator == "lte":
        passed = actual <= expected
    elif operator == "gt":
        passed = actual > expected
    elif operator == "gte":
        passed = actual >= expected
    else:
        if (
            not isinstance(expected, list)
            or len(expected) != 2
        ):
            raise ValueError("'between' requires [lower, upper]")
        passed = expected[0] <= actual <= expected[1]

    return bool(passed), f"{operator} {expected!r}"


def load_research_project(path: str) -> dict[str, Any]:
    """Load and structurally validate a version-1 research project manifest."""

    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        project = json.load(handle)
    if not isinstance(project, dict):
        raise ValueError("research project must be a JSON object")
    if int(project.get("schema_version", 0)) != _PROJECT_SCHEMA_VERSION:
        raise ValueError("unsupported research project schema_version")

    title = str(project.get("title", "")).strip()
    question = str(project.get("research_question", "")).strip()
    if not title:
        raise ValueError("research project title is required")
    if not question:
        raise ValueError("research_question is required")

    authors = project.get("authors", [])
    if not isinstance(authors, list) or not authors:
        raise ValueError("authors must contain at least one author")
    for index, author in enumerate(authors):
        if not isinstance(author, dict):
            raise ValueError(f"authors[{index}] must be an object")
        if not str(author.get("name", "")).strip():
            raise ValueError(f"authors[{index}].name is required")

    hypotheses = project.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        raise ValueError("hypotheses must be a list")
    hypothesis_ids: set[str] = set()
    for index, hypothesis in enumerate(hypotheses):
        if not isinstance(hypothesis, dict):
            raise ValueError(f"hypotheses[{index}] must be an object")
        hypothesis_id = _require_safe_id(
            hypothesis.get("id", ""),
            field=f"hypotheses[{index}].id",
        )
        if hypothesis_id in hypothesis_ids:
            raise ValueError(f"duplicate hypothesis id {hypothesis_id!r}")
        hypothesis_ids.add(hypothesis_id)
        if not str(hypothesis.get("text", "")).strip():
            raise ValueError(f"hypotheses[{index}].text is required")

    experiments = project.get("experiments", [])
    if not isinstance(experiments, list):
        raise ValueError("experiments must be a list")
    experiment_ids: set[str] = set()
    for index, experiment in enumerate(experiments):
        if not isinstance(experiment, dict):
            raise ValueError(f"experiments[{index}] must be an object")
        experiment_id = _require_safe_id(
            experiment.get("id", ""),
            field=f"experiments[{index}].id",
        )
        if experiment_id in experiment_ids:
            raise ValueError(f"duplicate experiment id {experiment_id!r}")
        experiment_ids.add(experiment_id)
        if not str(experiment.get("manifest", "")).strip():
            raise ValueError(f"experiments[{index}].manifest is required")

    artifacts = project.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("artifacts must be a list")
    artifact_ids: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ValueError(f"artifacts[{index}] must be an object")
        artifact_id = _require_safe_id(
            artifact.get("id", ""),
            field=f"artifacts[{index}].id",
        )
        if artifact_id in artifact_ids:
            raise ValueError(f"duplicate artifact id {artifact_id!r}")
        artifact_ids.add(artifact_id)
        if not str(artifact.get("path", "")).strip():
            raise ValueError(f"artifacts[{index}].path is required")

    claims = project.get("claims", [])
    if not isinstance(claims, list):
        raise ValueError("claims must be a list")
    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise ValueError(f"claims[{index}] must be an object")
        claim_id = _require_safe_id(
            claim.get("id", ""),
            field=f"claims[{index}].id",
        )
        if claim_id in claim_ids:
            raise ValueError(f"duplicate claim id {claim_id!r}")
        claim_ids.add(claim_id)
        if not str(claim.get("text", "")).strip():
            raise ValueError(f"claims[{index}].text is required")
        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError(f"claims[{index}].evidence must be a list")

    protocol = project.get("protocol", {})
    if not isinstance(protocol, dict):
        raise ValueError("protocol must be an object")
    mode = str(protocol.get("mode", "exploratory")).lower()
    if mode not in {"exploratory", "confirmatory"}:
        raise ValueError("protocol.mode must be exploratory or confirmatory")

    paper = project.get("paper", {})
    if not isinstance(paper, dict):
        raise ValueError("paper must be an object")

    bibliography_files = project.get("bibliography_files", [])
    if not isinstance(bibliography_files, list):
        raise ValueError("bibliography_files must be a list")

    return project


def _artifact_inventory(
    project_path: Path,
    project: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for artifact in project.get("artifacts", []):
        artifact_id = str(artifact["id"])
        path = _resolve_path(project_path, str(artifact["path"]))
        record = {
            "id": artifact_id,
            "kind": str(artifact.get("kind", "file")),
            "description": str(artifact.get("description", "")),
            "source_path": str(path),
            "exists": path.is_file(),
        }
        if not path.is_file():
            errors.append(
                f"artifact {artifact_id!r} does not exist: {path}"
            )
        else:
            record["sha256"] = _sha256_file(path)
            record["bytes"] = int(path.stat().st_size)
        records[artifact_id] = record
    return records, errors


def _audit_claims(
    project_path: Path,
    project: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    claim_results: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    json_cache: dict[str, Any] = {}

    for claim in project.get("claims", []):
        claim_id = str(claim["id"])
        claim_type = str(claim.get("type", "result")).lower()
        evidence_items = claim.get("evidence", [])
        if claim_type in {"result", "interpretation"} and not evidence_items:
            errors.append(
                f"claim {claim_id!r} is a {claim_type} claim but has no evidence"
            )

        result = {
            "id": claim_id,
            "type": claim_type,
            "text": str(claim["text"]),
            "passed": True,
            "evidence": [],
        }

        for index, evidence in enumerate(evidence_items):
            if not isinstance(evidence, dict):
                errors.append(
                    f"claim {claim_id!r} evidence[{index}] must be an object"
                )
                result["passed"] = False
                continue

            artifact_id = str(evidence.get("artifact", ""))
            artifact = artifacts.get(artifact_id)
            evidence_result: dict[str, Any] = {
                "artifact": artifact_id,
                "json_pointer": evidence.get("json_pointer"),
                "passed": True,
            }
            if artifact is None:
                errors.append(
                    f"claim {claim_id!r} references unknown artifact "
                    f"{artifact_id!r}"
                )
                evidence_result["passed"] = False
                result["passed"] = False
                result["evidence"].append(evidence_result)
                continue
            if not artifact.get("exists"):
                evidence_result["passed"] = False
                result["passed"] = False
                result["evidence"].append(evidence_result)
                continue

            pointer = evidence.get("json_pointer")
            predicate = evidence.get("predicate", {})
            if pointer is None:
                if predicate:
                    errors.append(
                        f"claim {claim_id!r} evidence for {artifact_id!r} "
                        "has a predicate but no json_pointer"
                    )
                    evidence_result["passed"] = False
                    result["passed"] = False
            else:
                path = Path(str(artifact["source_path"]))
                cache_key = str(path)
                if cache_key not in json_cache:
                    try:
                        json_cache[cache_key] = json.loads(
                            path.read_text(encoding="utf-8")
                        )
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                        errors.append(
                            f"claim {claim_id!r} needs JSON artifact "
                            f"{artifact_id!r}, but it could not be parsed: {exc}"
                        )
                        evidence_result["passed"] = False
                        result["passed"] = False
                        result["evidence"].append(evidence_result)
                        continue
                try:
                    actual = _json_pointer_get(
                        json_cache[cache_key],
                        str(pointer),
                    )
                    passed, predicate_text = _predicate_result(
                        actual,
                        predicate if isinstance(predicate, dict) else {},
                    )
                    evidence_result["actual"] = actual
                    evidence_result["predicate"] = predicate
                    evidence_result["predicate_text"] = predicate_text
                    evidence_result["passed"] = passed
                    if not passed:
                        errors.append(
                            f"claim {claim_id!r} evidence predicate failed: "
                            f"artifact={artifact_id!r} pointer={pointer!r} "
                            f"actual={actual!r} expected={predicate!r}"
                        )
                        result["passed"] = False
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    errors.append(
                        f"claim {claim_id!r} evidence could not resolve "
                        f"{artifact_id!r}{pointer}: {exc}"
                    )
                    evidence_result["passed"] = False
                    result["passed"] = False

            result["evidence"].append(evidence_result)

        if claim_type not in {
            "result",
            "interpretation",
            "method",
            "background",
            "limitation",
        }:
            warnings.append(
                f"claim {claim_id!r} uses non-standard type {claim_type!r}"
            )
        claim_results.append(result)

    return claim_results, errors, warnings


def audit_research_project(
    path: str,
    *,
    require_protocol_lock: bool = False,
) -> dict[str, Any]:
    """Audit a project manifest and all declared claim-to-evidence links."""

    project_path = Path(path).resolve()
    project = load_research_project(str(project_path))
    errors: list[str] = []
    warnings: list[str] = []

    artifacts, artifact_errors = _artifact_inventory(
        project_path,
        project,
    )
    errors.extend(artifact_errors)

    experiment_records: list[dict[str, Any]] = []
    from .experiment import load_experiment_manifest

    for experiment in project.get("experiments", []):
        experiment_id = str(experiment["id"])
        manifest_path = _resolve_path(
            project_path,
            str(experiment["manifest"]),
        )
        record = {
            "id": experiment_id,
            "manifest_path": str(manifest_path),
            "exists": manifest_path.is_file(),
        }
        if not manifest_path.is_file():
            errors.append(
                f"experiment {experiment_id!r} manifest does not exist: "
                f"{manifest_path}"
            )
        else:
            try:
                manifest = load_experiment_manifest(str(manifest_path))
                record["operation"] = manifest["operation"]
                record["sha256"] = _sha256_file(manifest_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(
                    f"experiment {experiment_id!r} manifest is invalid: {exc}"
                )
        experiment_records.append(record)

    bibliography_records: list[dict[str, Any]] = []
    for raw_path in project.get("bibliography_files", []):
        bib_path = _resolve_path(project_path, str(raw_path))
        record = {
            "path": str(bib_path),
            "exists": bib_path.is_file(),
        }
        if not bib_path.is_file():
            errors.append(f"bibliography file does not exist: {bib_path}")
        else:
            record["sha256"] = _sha256_file(bib_path)
        bibliography_records.append(record)

    claim_results, claim_errors, claim_warnings = _audit_claims(
        project_path,
        project,
        artifacts,
    )
    errors.extend(claim_errors)
    warnings.extend(claim_warnings)

    lock_path = project_path.with_suffix(".protocol.lock.json")
    lock_result: dict[str, Any] | None = None
    if lock_path.is_file():
        lock_result = verify_protocol_lock(
            str(project_path),
            str(lock_path),
        )
        if not lock_result["valid"]:
            errors.extend(
                f"protocol lock: {message}"
                for message in lock_result["failures"]
            )
    elif require_protocol_lock:
        errors.append(
            f"protocol lock required but not found: {lock_path}"
        )
    else:
        warnings.append(
            "project protocol is not frozen; create a protocol lock before "
            "confirmatory experiments"
        )

    paper = project.get("paper", {})
    required_paper_fields = [
        "abstract",
        "statement_of_need",
        "state_of_field",
        "software_design",
        "methods",
        "limitations",
        "impact",
        "ai_usage_disclosure",
        "data_availability",
        "code_availability",
    ]
    for field in required_paper_fields:
        if not str(paper.get(field, "")).strip():
            warnings.append(f"paper.{field} is empty")

    return {
        "schema_version": 1,
        "audit_type": "aegis_qec_research_project",
        "project_path": str(project_path),
        "project_sha256": _sha256_file(project_path),
        "title": project["title"],
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "experiments": experiment_records,
        "artifacts": artifacts,
        "claims": claim_results,
        "bibliography": bibliography_records,
        "protocol_lock": lock_result,
    }


def _protocol_projection(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": int(project["schema_version"]),
        "research_question": project["research_question"],
        "hypotheses": project.get("hypotheses", []),
        "protocol": project.get("protocol", {}),
        "experiments": project.get("experiments", []),
    }


def _protocol_projection_sha256(project: dict[str, Any]) -> str:
    canonical = json.dumps(
        _protocol_projection(project),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def freeze_research_protocol(
    project_path: str,
    *,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Freeze scientific protocol inputs before confirmatory work."""

    source = Path(project_path).resolve()
    project = load_research_project(str(source))
    protocol = project.get("protocol", {})
    if str(protocol.get("mode", "exploratory")).lower() == "confirmatory":
        required = ["primary_outcome", "analysis_plan", "stopping_rule"]
        missing = [
            name
            for name in required
            if not str(protocol.get(name, "")).strip()
        ]
        if missing:
            raise ValueError(
                "confirmatory protocol is missing: " + ", ".join(missing)
            )
    files: list[dict[str, Any]] = []

    for experiment in project.get("experiments", []):
        path = _resolve_path(source, str(experiment["manifest"]))
        if not path.is_file():
            raise FileNotFoundError(
                f"experiment manifest does not exist: {path}"
            )
        files.append(
            {
                "role": f"experiment:{experiment['id']}",
                "path": str(path),
                "sha256": _sha256_file(path),
            }
        )

    protocol_projection = _protocol_projection(project)
    lock = {
        "schema_version": 1,
        "lock_type": "aegis_qec_research_protocol",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_title_at_freeze": project["title"],
        "project_path": str(source),
        "project_protocol": protocol_projection,
        "project_protocol_sha256": _protocol_projection_sha256(project),
        "files": files,
    }
    canonical = json.dumps(
        lock,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    lock["protocol_sha256"] = _sha256_bytes(canonical)

    destination = (
        Path(output_path).resolve()
        if output_path
        else source.with_suffix(".protocol.lock.json")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lock["path"] = str(destination)
    lock["file_sha256"] = _sha256_file(destination)
    return lock


def verify_protocol_lock(
    project_path: str,
    lock_path: str,
) -> dict[str, Any]:
    """Verify a frozen scientific protocol against current definitions."""

    source = Path(project_path).resolve()
    project = load_research_project(str(source))
    lock_file = Path(lock_path).resolve()
    lock = json.loads(lock_file.read_text(encoding="utf-8"))
    failures: list[str] = []

    if lock.get("lock_type") != "aegis_qec_research_protocol":
        failures.append("not an Aegis research protocol lock")

    stored_protocol_hash = str(lock.get("project_protocol_sha256", ""))
    actual_protocol_hash = _protocol_projection_sha256(project)
    if stored_protocol_hash != actual_protocol_hash:
        failures.append("scientific protocol changed after freeze")

    expected_lock_hash = str(lock.get("protocol_sha256", ""))
    lock_without_hash = {
        key: value
        for key, value in lock.items()
        if key != "protocol_sha256"
    }
    actual_lock_hash = _sha256_bytes(
        json.dumps(
            lock_without_hash,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    if expected_lock_hash != actual_lock_hash:
        failures.append("protocol lock metadata failed its own integrity hash")

    experiment_by_role = {
        f"experiment:{experiment['id']}": _resolve_path(
            source,
            str(experiment["manifest"]),
        )
        for experiment in project.get("experiments", [])
    }
    locked_roles = {
        str(item.get("role", ""))
        for item in lock.get("files", [])
    }
    if locked_roles != set(experiment_by_role):
        failures.append("experiment set changed after protocol freeze")

    for item in lock.get("files", []):
        role = str(item.get("role", ""))
        path = experiment_by_role.get(role)
        if path is None:
            continue
        if not path.is_file():
            failures.append(f"locked experiment manifest is missing: {path}")
            continue
        actual = _sha256_file(path)
        if actual != str(item.get("sha256", "")):
            failures.append(f"locked experiment manifest changed: {path}")

    return {
        "schema_version": 1,
        "verification_type": "aegis_qec_research_protocol",
        "path": str(lock_file),
        "valid": not failures,
        "failures": failures,
        "protocol_sha256": lock.get("protocol_sha256"),
        "project_protocol_sha256": actual_protocol_hash,
    }


def run_research_project(
    project_path: str,
    *,
    workspace: str,
) -> dict[str, Any]:
    """Run all declared experiment manifests and preserve per-experiment bundles."""

    source = Path(project_path).resolve()
    project = load_research_project(str(source))
    destination = Path(workspace).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    from .experiment import (
        create_research_bundle,
        run_experiment_manifest,
    )

    experiment_runs: list[dict[str, Any]] = []
    for experiment in project.get("experiments", []):
        experiment_id = str(experiment["id"])
        manifest_path = _resolve_path(
            source,
            str(experiment["manifest"]),
        )
        experiment_dir = destination / experiment_id
        experiment_dir.mkdir(parents=True, exist_ok=True)
        run_record = run_experiment_manifest(
            str(manifest_path),
            output_dir=str(experiment_dir),
        )
        bundle_path = experiment_dir / f"{experiment_id}.aegis.zip"
        bundle = create_research_bundle(
            manifest_path=str(manifest_path),
            run_record=run_record,
            bundle_path=str(bundle_path),
        )
        experiment_runs.append(
            {
                "id": experiment_id,
                "manifest_path": str(manifest_path),
                "manifest_sha256": _sha256_file(manifest_path),
                "run_record": run_record,
                "bundle": bundle,
            }
        )

    project_run = {
        "schema_version": 1,
        "record_type": "aegis_qec_research_project_run",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_path": str(source),
        "project_sha256": _sha256_file(source),
        "workspace": str(destination),
        "experiments": experiment_runs,
    }
    output = destination / "project-run.json"
    output.write_text(
        json.dumps(project_run, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    project_run["path"] = str(output)
    project_run["sha256"] = _sha256_file(output)
    return project_run


def write_research_project_template(
    output_path: str,
    *,
    author_name: str = "Researcher",
    overwrite: bool = False,
) -> dict[str, str]:
    """Create an editable research project and a runnable starter experiment."""

    destination = Path(output_path).resolve()
    experiment_path = destination.parent / "experiment.json"
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"{destination} already exists; use overwrite=True or --force"
        )
    if experiment_path.exists() and not overwrite:
        raise FileExistsError(
            f"{experiment_path} already exists; use overwrite=True or --force"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)

    from .template_catalog import write_experiment_template

    write_experiment_template(
        "first-study",
        str(experiment_path),
        overwrite=overwrite,
    )

    project = {
        "$schema": (
            "https://raw.githubusercontent.com/hamidbahri92/Aegis/"
            "main/schemas/research-project-v1.schema.json"
        ),
        "schema_version": 1,
        "title": "Untitled Aegis QEC research project",
        "authors": [{"name": str(author_name)}],
        "keywords": [
            "quantum error correction",
            "surface code",
            "reproducible research",
        ],
        "research_question": "Replace with the precise research question.",
        "protocol": {
            "mode": "exploratory",
            "primary_outcome": "",
            "analysis_plan": "",
            "stopping_rule": "",
            "search_plan": "",
            "multiple_comparisons": "",
        },
        "hypotheses": [
            {
                "id": "H1",
                "text": "Replace with a falsifiable hypothesis.",
            }
        ],
        "experiments": [
            {
                "id": "study",
                "manifest": experiment_path.name,
            }
        ],
        "artifacts": [],
        "claims": [],
        "bibliography_files": [],
        "paper": {
            "venue": "generic",
            "abstract": "",
            "statement_of_need": "",
            "state_of_field": "",
            "software_design": "",
            "methods": "",
            "results_context": "",
            "limitations": "",
            "impact": "",
            "data_availability": "",
            "code_availability": "",
            "ai_usage_disclosure": "",
            "competing_interests": "",
            "funding": "",
        },
    }
    destination.write_text(
        json.dumps(project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "project_path": str(destination),
        "experiment_path": str(experiment_path),
    }
