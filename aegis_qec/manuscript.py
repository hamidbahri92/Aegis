from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project import (
    _resolve_path,
    _sha256_file,
    audit_research_project,
    load_research_project,
)


_LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _latex_escape(value: Any) -> str:
    text = str(value)
    return "".join(_LATEX_REPLACEMENTS.get(char, char) for char in text)


def _section(text: str) -> str:
    return str(text or "").strip()


def _author_latex(author: dict[str, Any]) -> str:
    name = _latex_escape(author.get("name", ""))
    affiliation = str(author.get("affiliation", "")).strip()
    orcid = str(author.get("orcid", "")).strip()
    parts = [name]
    if affiliation:
        parts.append(r"\\" + _latex_escape(affiliation))
    if orcid:
        parts.append(r"\\" + r"\texttt{" + _latex_escape(orcid) + "}")
    return "".join(parts)


def _claim_appendix(project: dict[str, Any]) -> str:
    lines = [
        r"\section{Claim-to-evidence traceability}",
        (
            "The following table is generated from the research-project manifest. "
            "It is intended to make empirical claims auditable against declared "
            "artifacts rather than relying on manuscript prose alone."
        ),
        r"\begin{longtable}{p{0.14\linewidth}p{0.50\linewidth}p{0.28\linewidth}}",
        r"\toprule",
        r"Claim & Text & Evidence \\",
        r"\midrule",
        r"\endhead",
    ]
    for claim in project.get("claims", []):
        evidence = []
        for item in claim.get("evidence", []):
            artifact = _latex_escape(item.get("artifact", ""))
            pointer = _latex_escape(item.get("json_pointer", ""))
            if pointer:
                evidence.append(f"{artifact}: {pointer}")
            else:
                evidence.append(artifact)
        evidence_text = "; ".join(evidence) if evidence else "None declared"
        lines.append(
            "{} & {} & {} \\".format(
                _latex_escape(claim.get("id", "")),
                _latex_escape(claim.get("text", "")),
                _latex_escape(evidence_text),
            )
        )
    lines.extend([r"\bottomrule", r"\end{longtable}"])
    return "\n".join(lines)


def _hypothesis_section(project: dict[str, Any]) -> str:
    hypotheses = project.get("hypotheses", [])
    if not hypotheses:
        return ""
    lines = [r"\section{Hypotheses and analysis commitments}", r"\begin{enumerate}"]
    for item in hypotheses:
        text = _latex_escape(item.get("text", ""))
        identifier = _latex_escape(item.get("id", ""))
        decision_rule = str(item.get("decision_rule", "")).strip()
        entry = f"\n\\item \\textbf{{{identifier}.}} {text}"
        if decision_rule:
            entry += (
                r"\par\emph{Pre-specified decision rule:} "
                + _latex_escape(decision_rule)
            )
        lines.append(entry)
    lines.append(r"\end{enumerate}")
    return "\n".join(lines)


def _results_claims(project: dict[str, Any]) -> str:
    claims = [
        claim
        for claim in project.get("claims", [])
        if str(claim.get("type", "result")).lower()
        in {"result", "interpretation"}
    ]
    if not claims:
        return (
            "No result claims are declared in the project manifest. "
            "Aegis intentionally does not invent conclusions."
        )
    lines = [r"\begin{itemize}"]
    for claim in claims:
        lines.append(
            r"\item " + _latex_escape(claim.get("text", ""))
        )
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _venue_checklist(project: dict[str, Any], audit: dict[str, Any]) -> str:
    venue = str(project.get("venue", "generic")).lower()
    paper = project.get("paper", {})
    artifacts = audit.get("artifacts", {})

    code_url = str(project.get("code_url", "")).strip()
    data_url = str(project.get("data_url", "")).strip()
    dataset_artifacts = [
        value
        for value in artifacts.values()
        if value.get("kind") == "dataset"
    ]

    checks: list[tuple[str, bool, str]] = [
        (
            "All result and interpretation claims have declared evidence",
            all(
                claim.get("passed", False)
                for claim in audit.get("claims", [])
                if claim.get("type") in {"result", "interpretation"}
            ),
            "Every empirical conclusion should resolve to preserved evidence.",
        ),
        (
            "Research protocol is frozen",
            bool(audit.get("protocol_lock", {}).get("valid")),
            "Freeze project and experiment definitions before confirmatory work.",
        ),
        (
            "Code availability is declared",
            bool(code_url or _section(paper.get("code_availability", ""))),
            "Provide a repository/archive path or a justified access statement.",
        ),
        (
            "Data availability is declared",
            bool(data_url or _section(paper.get("data_availability", ""))),
            "State how datasets/evidence can be accessed or why they cannot be shared.",
        ),
        (
            "Limitations are explicit",
            bool(_section(paper.get("limitations", ""))),
            "State scope, failure modes, external-validity limits, and known weaknesses.",
        ),
        (
            "AI usage is disclosed",
            bool(_section(paper.get("ai_usage_disclosure", ""))),
            "Disclose generative-AI use in software, analysis, documentation, or writing.",
        ),
        (
            "Bibliography is declared",
            bool(project.get("bibliography_files")),
            "Cite algorithms, software, datasets, and prior art.",
        ),
    ]

    if venue == "joss":
        checks.extend(
            [
                ("JOSS statement of need present", bool(_section(paper.get("statement_of_need", ""))), ""),
                ("JOSS state of field present", bool(_section(paper.get("state_of_field", ""))), ""),
                ("JOSS software design present", bool(_section(paper.get("software_design", ""))), ""),
                ("JOSS research impact present", bool(_section(paper.get("impact", ""))), ""),
            ]
        )

    if venue in {"neurips", "neurips-ed"}:
        compute = project.get("compute_resources", [])
        checks.extend(
            [
                ("Experimental compute is documented", bool(compute), ""),
                (
                    "Exact reproduction commands are declared",
                    bool(project.get("reproduction_commands")),
                    "",
                ),
            ]
        )
        if venue == "neurips-ed" and dataset_artifacts:
            checks.append(
                (
                    "Dataset contribution has Croissant exportable metadata",
                    all(
                        bool(item.get("description"))
                        for item in dataset_artifacts
                    ),
                    "Each dataset artifact should declare description, license, and public URL before submission.",
                )
            )

    lines = [
        f"# Submission readiness checklist: {venue}",
        "",
        f"Project: {project['title']}",
        "",
    ]
    for label, passed, note in checks:
        lines.append(f"- [{'x' if passed else ' '}] {label}")
        if note:
            lines.append(f"  - {note}")
    lines.extend(
        [
            "",
            "This checklist is generated from project metadata and is not a substitute",
            "for reading the target venue's current official submission instructions.",
        ]
    )
    return "\n".join(lines) + "\n"


def _reproduce_markdown(project: dict[str, Any], audit: dict[str, Any]) -> str:
    lines = [
        f"# Reproduce: {project['title']}",
        "",
        "This file was generated by Aegis QEC from the research-project manifest.",
        "",
        "## Environment",
        "",
        "Install the released package or the exact source revision used by the project.",
        "",
    ]
    code_url = str(project.get("code_url", "")).strip()
    if code_url:
        lines.extend([f"Code: {code_url}", ""])

    commands = project.get("reproduction_commands", [])
    lines.extend(["## Exact commands", ""])
    if commands:
        for command in commands:
            lines.extend(["```bash", str(command), "```", ""])
    else:
        lines.append("No project-level reproduction commands were declared.")
        lines.append("")

    lines.extend(["## Experiment manifests", ""])
    for experiment in audit.get("experiments", []):
        lines.append(
            f"- `{experiment['id']}`: `{experiment['manifest_path']}` "
            f"(SHA-256 `{experiment.get('sha256', 'missing')}`)"
        )

    lines.extend(["", "## Evidence artifacts", ""])
    for artifact_id, artifact in audit.get("artifacts", {}).items():
        lines.append(
            f"- `{artifact_id}`: `{artifact['source_path']}` "
            f"(SHA-256 `{artifact.get('sha256', 'missing')}`)"
        )
    lines.append("")
    return "\n".join(lines)


def _claims_markdown(project: dict[str, Any], audit: dict[str, Any]) -> str:
    by_id = {item["id"]: item for item in audit.get("claims", [])}
    lines = [
        f"# Claim-to-evidence map: {project['title']}",
        "",
    ]
    for claim in project.get("claims", []):
        result = by_id.get(str(claim["id"]), {})
        lines.extend(
            [
                f"## {claim['id']}",
                "",
                str(claim["text"]),
                "",
                f"Type: `{claim.get('type', 'result')}`",
                "",
                f"Audit: **{'PASS' if result.get('passed') else 'FAIL'}**",
                "",
                "Evidence:",
            ]
        )
        if result.get("evidence"):
            for evidence in result["evidence"]:
                lines.append(
                    "- `{}` `{}` — {}".format(
                        evidence.get("artifact", ""),
                        evidence.get("json_pointer", "") or "",
                        "PASS" if evidence.get("passed") else "FAIL",
                    )
                )
        else:
            lines.append("- None declared")
        lines.append("")
    return "\n".join(lines)


def _croissant_for_artifact(
    project: dict[str, Any],
    artifact_spec: dict[str, Any],
    artifact_record: dict[str, Any],
    *,
    packaged_name: str,
) -> dict[str, Any]:
    license_value = artifact_spec.get("license")
    url = artifact_spec.get("url")
    description = str(
        artifact_spec.get("description", "")
        or f"Dataset artifact for {project['title']}"
    )
    if not license_value:
        raise ValueError(
            f"dataset artifact {artifact_spec['id']!r} is missing license"
        )
    if not url:
        raise ValueError(
            f"dataset artifact {artifact_spec['id']!r} is missing url"
        )

    return {
        "@context": {
            "@language": "en",
            "@vocab": "https://schema.org/",
            "sc": "https://schema.org/",
            "cr": "http://mlcommons.org/croissant/",
            "dct": "http://purl.org/dc/terms/",
            "conformsTo": "dct:conformsTo",
        },
        "@type": "sc:Dataset",
        "name": str(artifact_spec.get("name", artifact_spec["id"])),
        "description": description,
        "license": license_value,
        "url": url,
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "distribution": [
            {
                "@type": "cr:FileObject",
                "@id": packaged_name,
                "name": Path(packaged_name).name,
                "contentSize": f"{artifact_record['bytes']} B",
                "encodingFormat": str(
                    artifact_spec.get(
                        "encoding_format",
                        "application/octet-stream",
                    )
                ),
                "sha256": artifact_record["sha256"],
                "contentUrl": url,
            }
        ],
    }


def _latex_document(
    project: dict[str, Any],
    audit: dict[str, Any],
    bibliography_names: list[str],
) -> str:
    paper = project.get("paper", {})
    authors = " \\and ".join(
        _author_latex(author)
        for author in project.get("authors", [])
    )

    parts = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{lmodern}",
        r"\usepackage{microtype}",
        r"\usepackage{geometry}",
        r"\usepackage{booktabs}",
        r"\usepackage{longtable}",
        r"\usepackage{hyperref}",
        r"\usepackage{url}",
        r"\geometry{margin=1in}",
        r"\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue}",
        "",
        r"\title{" + _latex_escape(project["title"]) + "}",
        r"\author{" + authors + "}",
        r"\date{}",
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
        r"\begin{abstract}",
        _latex_escape(_section(paper.get("abstract", ""))),
        r"\end{abstract}",
        "",
        r"\section{Research question}",
        _latex_escape(project["research_question"]),
        "",
        _hypothesis_section(project),
        "",
        r"\section{Statement of need}",
        _latex_escape(_section(paper.get("statement_of_need", ""))),
        "",
        r"\section{State of the field}",
        _latex_escape(_section(paper.get("state_of_field", ""))),
        "",
        r"\section{Software design}",
        _latex_escape(_section(paper.get("software_design", ""))),
        "",
        r"\section{Methods}",
        _latex_escape(_section(paper.get("methods", ""))),
        "",
        r"\section{Results}",
        _results_claims(project),
        "",
        r"\section{Limitations}",
        _latex_escape(_section(paper.get("limitations", ""))),
        "",
        r"\section{Research impact}",
        _latex_escape(_section(paper.get("impact", ""))),
        "",
        r"\section{Data availability}",
        _latex_escape(_section(paper.get("data_availability", ""))),
        "",
        r"\section{Code availability}",
        _latex_escape(_section(paper.get("code_availability", ""))),
        "",
        r"\section{AI usage disclosure}",
        _latex_escape(_section(paper.get("ai_usage_disclosure", ""))),
        "",
        _claim_appendix(project),
        "",
    ]

    if bibliography_names:
        parts.extend(
            [
                r"\bibliographystyle{plain}",
                r"\bibliography{" + ",".join(bibliography_names) + "}",
                "",
            ]
        )

    parts.extend([r"\end{document}", ""])
    return "\n".join(part for part in parts if part is not None)


def _compile_latex(source_dir: Path) -> dict[str, Any]:
    tex_path = source_dir / "paper.tex"
    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    command: list[str] | None = None
    if latexmk:
        command = [
            latexmk,
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "paper.tex",
        ]
    elif pdflatex:
        command = [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "paper.tex",
        ]

    if command is None:
        return {
            "attempted": False,
            "success": False,
            "reason": "latexmk/pdflatex not available",
        }

    completed = subprocess.run(
        command,
        cwd=source_dir,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    pdf_path = source_dir / "paper.pdf"
    return {
        "attempted": True,
        "success": completed.returncode == 0 and pdf_path.is_file(),
        "returncode": completed.returncode,
        "command": command,
        "stdout_tail": completed.stdout[-6000:],
        "stderr_tail": completed.stderr[-6000:],
        "pdf_path": str(pdf_path) if pdf_path.is_file() else None,
        "tex_path": str(tex_path),
    }


def _zip_tree(source_dir: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w") as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.resolve() == destination.resolve():
                continue
            relative = path.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(relative)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def build_submission_package(
    project_path: str,
    *,
    output_dir: str,
    compile_pdf: bool = True,
    require_protocol_lock: bool = True,
) -> dict[str, Any]:
    """Build a reviewer-facing manuscript and reproducibility package."""

    source = Path(project_path).resolve()
    project = load_research_project(str(source))
    audit = audit_research_project(
        str(source),
        require_protocol_lock=require_protocol_lock,
    )

    destination = Path(output_dir).resolve()
    source_dir = destination / "source"
    evidence_dir = destination / "evidence"
    metadata_dir = destination / "metadata"
    for directory in (source_dir, evidence_dir, metadata_dir):
        directory.mkdir(parents=True, exist_ok=True)

    bibliography_names: list[str] = []
    for index, raw_path in enumerate(project.get("bibliography_files", [])):
        path = _resolve_path(source, str(raw_path))
        if not path.is_file():
            continue
        name = f"references-{index}{path.suffix or '.bib'}"
        shutil.copy2(path, source_dir / name)
        bibliography_names.append(Path(name).stem)

    artifact_specs = {
        str(item["id"]): item
        for item in project.get("artifacts", [])
    }
    packaged_artifacts: dict[str, dict[str, Any]] = {}
    croissant_records: list[dict[str, Any]] = []
    for artifact_id, record in audit.get("artifacts", {}).items():
        if not record.get("exists"):
            continue
        source_path = Path(str(record["source_path"]))
        artifact_dir = evidence_dir / artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        destination_path = artifact_dir / source_path.name
        shutil.copy2(source_path, destination_path)
        packaged = {
            **record,
            "packaged_path": str(destination_path.relative_to(destination)),
        }
        packaged_artifacts[artifact_id] = packaged

        artifact_spec = artifact_specs.get(artifact_id, {})
        if record.get("kind") == "dataset" and bool(
            artifact_spec.get("croissant", False)
        ):
            metadata = _croissant_for_artifact(
                project,
                artifact_spec,
                record,
                packaged_name=destination_path.name,
            )
            croissant_path = artifact_dir / "croissant.json"
            croissant_path.write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            croissant_records.append(
                {
                    "artifact": artifact_id,
                    "path": str(croissant_path.relative_to(destination)),
                    "sha256": _sha256_file(croissant_path),
                }
            )

    latex = _latex_document(project, audit, bibliography_names)
    (source_dir / "paper.tex").write_text(latex, encoding="utf-8")

    (destination / "REPRODUCE.md").write_text(
        _reproduce_markdown(project, audit),
        encoding="utf-8",
    )
    (destination / "CLAIMS.md").write_text(
        _claims_markdown(project, audit),
        encoding="utf-8",
    )
    (destination / "REVIEWER_CHECKLIST.md").write_text(
        _venue_checklist(project, audit),
        encoding="utf-8",
    )

    audit_path = metadata_dir / "submission-audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    project_copy = metadata_dir / "research-project.json"
    shutil.copy2(source, project_copy)

    compile_result = (
        _compile_latex(source_dir)
        if compile_pdf
        else {
            "attempted": False,
            "success": False,
            "reason": "PDF compilation disabled",
        }
    )

    required_sections = [
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
    missing_sections = [
        key
        for key in required_sections
        if not _section(project.get("paper", {}).get(key, ""))
    ]

    readiness_errors = list(audit.get("errors", []))
    if missing_sections:
        readiness_errors.append(
            "paper sections missing: " + ", ".join(missing_sections)
        )
    if (
        compile_pdf
        and compile_result.get("attempted")
        and not compile_result.get("success")
    ):
        readiness_errors.append(
            "LaTeX engine was available but PDF compilation failed"
        )

    inventory: list[dict[str, Any]] = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith(".zip"):
            continue
        inventory.append(
            {
                "path": path.relative_to(destination).as_posix(),
                "sha256": _sha256_file(path),
                "bytes": int(path.stat().st_size),
            }
        )

    manifest = {
        "schema_version": 1,
        "package_type": "aegis_qec_submission_package",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_title": project["title"],
        "project_sha256": _sha256_file(source),
        "venue": str(project.get("venue", "generic")),
        "ready": not readiness_errors,
        "readiness_errors": readiness_errors,
        "audit_warnings": audit.get("warnings", []),
        "compile": compile_result,
        "artifacts": packaged_artifacts,
        "croissant": croissant_records,
        "inventory": inventory,
    }
    manifest_path = metadata_dir / "submission-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    archive = destination.with_suffix(".zip")
    _zip_tree(destination, archive)

    return {
        **manifest,
        "output_dir": str(destination),
        "manifest_path": str(manifest_path),
        "archive_path": str(archive),
        "archive_sha256": _sha256_file(archive),
        "archive_bytes": int(archive.stat().st_size),
    }
