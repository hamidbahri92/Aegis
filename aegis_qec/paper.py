from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from .project import _sha256_file, audit_research_project, load_research_project

_STIM_BIB = """@article{gidney2021stim,
  doi = {10.22331/q-2021-07-06-497},
  url = {https://doi.org/10.22331/q-2021-07-06-497},
  title = {Stim: a fast stabilizer circuit simulator},
  author = {Gidney, Craig},
  journal = {Quantum},
  volume = {5},
  pages = {497},
  year = {2021}
}
"""

_PYMATCHING_BIB = """@article{Higgott2025sparseblossom,
  doi = {10.22331/q-2025-01-20-1600},
  url = {https://doi.org/10.22331/q-2025-01-20-1600},
  title = {Sparse Blossom: correcting a million errors per core second with minimum-weight matching},
  author = {Higgott, Oscar and Gidney, Craig},
  journal = {Quantum},
  volume = {9},
  pages = {1600},
  year = {2025}
}
"""


def _version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _latex_escape(value: Any) -> str:
    replacements = {
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
    return "".join(replacements.get(char, char) for char in str(value))


def _paragraphs(value: Any) -> str:
    parts = [
        part.strip()
        for part in str(value or "").split("\n\n")
        if part.strip()
    ]
    if not parts:
        return r"\emph{Not provided.}"
    return "\n\n".join(_latex_escape(part) for part in parts)


def _authors(project: dict[str, Any]) -> str:
    return r" \and ".join(
        _latex_escape(author["name"])
        for author in project["authors"]
    )


def _anonymize_project(project: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(project)
    value["authors"] = [{"name": "Anonymous Authors"}]
    return value


def _sanitize_audit(
    audit: dict[str, Any],
    *,
    anonymize: bool,
) -> dict[str, Any]:
    if not anonymize:
        return copy.deepcopy(audit)
    value = copy.deepcopy(audit)
    value["project_path"] = "research-project.json"
    for artifact in value.get("artifacts", {}).values():
        if artifact.get("source_path"):
            artifact["source_path"] = Path(artifact["source_path"]).name
    for experiment in value.get("experiments", []):
        if experiment.get("manifest_path"):
            experiment["manifest_path"] = Path(
                experiment["manifest_path"]
            ).name
    for bibliography in value.get("bibliography", []):
        if bibliography.get("path"):
            bibliography["path"] = Path(bibliography["path"]).name
    lock = value.get("protocol_lock")
    if isinstance(lock, dict) and lock.get("path"):
        lock["path"] = Path(lock["path"]).name
    return value


def _hypotheses(project: dict[str, Any]) -> str:
    items = project.get("hypotheses", [])
    if not items:
        return r"\emph{No hypotheses declared.}"
    lines = [r"\begin{enumerate}"]
    for item in items:
        lines.append(
            r"\item \textbf{"
            + _latex_escape(item["id"])
            + r":} "
            + _latex_escape(item["text"])
        )
    lines.append(r"\end{enumerate}")
    return "\n".join(lines)


def _result_claims(project: dict[str, Any]) -> str:
    claims = [
        claim
        for claim in project.get("claims", [])
        if str(claim.get("type", "result")).lower()
        in {"result", "interpretation"}
    ]
    if not claims:
        return r"\emph{No result claims declared.}"
    lines = [r"\begin{itemize}"]
    for claim in claims:
        lines.append(
            r"\item \textbf{"
            + _latex_escape(claim["id"])
            + r":} "
            + _latex_escape(claim["text"])
        )
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def _claim_table(audit: dict[str, Any]) -> str:
    rows = []
    for claim in audit["claims"]:
        evidence = []
        for item in claim["evidence"]:
            label = str(item.get("artifact", ""))
            if item.get("json_pointer"):
                label += str(item["json_pointer"])
            if "actual" in item:
                label += " = " + repr(item["actual"])
            evidence.append(label)
        rows.append(
            "{} & {} & {} & {} \\\\".format(
                _latex_escape(claim["id"]),
                _latex_escape(claim["type"]),
                "PASS" if claim["passed"] else "FAIL",
                _latex_escape("; ".join(evidence) or "none"),
            )
        )
    return "\n".join(rows) or r"\multicolumn{4}{l}{No claims declared.} \\"


def _artifact_table(audit: dict[str, Any]) -> str:
    rows = []
    for artifact_id in sorted(audit["artifacts"]):
        artifact = audit["artifacts"][artifact_id]
        rows.append(
            "{} & {} & {} & {} \\\\".format(
                _latex_escape(artifact_id),
                _latex_escape(artifact.get("kind", "file")),
                _latex_escape(Path(artifact.get("source_path", "")).name),
                _latex_escape(str(artifact.get("sha256", "missing"))[:16]),
            )
        )
    return "\n".join(rows) or r"\multicolumn{4}{l}{No artifacts declared.} \\"


def _environment() -> dict[str, Any]:
    packages = [
        "aegis-qec",
        "numpy",
        "pymatching",
        "stim",
        "sinter",
        "h5py",
        "matplotlib",
        "scipy",
    ]
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": {name: _version(name) for name in packages},
        "github_sha": os.environ.get("GITHUB_SHA"),
    }


def _aegis_bib() -> str:
    version = _version("aegis-qec") or "source"
    year = datetime.now(timezone.utc).year
    return f"""@software{{aegis_qec,
  author = {{Bahri, Hamid}},
  title = {{Aegis QEC: reproducible quantum error-correction research platform}},
  version = {{{version}}},
  url = {{https://github.com/hamidbahri92/Aegis}},
  year = {{{year}}}
}}
"""


def _references(project_path: Path, project: dict[str, Any]) -> str:
    blocks = [_aegis_bib(), _STIM_BIB, _PYMATCHING_BIB]
    for value in project.get("bibliography_files", []):
        path = Path(value)
        if not path.is_absolute():
            path = project_path.parent / path
        blocks.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(block.strip() for block in blocks if block.strip()) + "\n"


def _tex(project: dict[str, Any], audit: dict[str, Any]) -> str:
    paper = project.get("paper", {})
    keywords = project.get("keywords", paper.get("keywords", []))
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.split(",") if part.strip()]
    keyword_text = ", ".join(str(item) for item in keywords)

    return f"""\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{booktabs}}
\\usepackage{{longtable}}
\\usepackage{{array}}
\\usepackage{{hyperref}}
\\usepackage{{microtype}}
\\usepackage{{enumitem}}
\\newcolumntype{{L}}[1]{{>{{\\raggedright\\arraybackslash}}p{{#1}}}}
\\hypersetup{{colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue}}

\\title{{{_latex_escape(project["title"])}}}
\\author{{{_authors(project)}}}
\\date{{}}

\\begin{{document}}
\\maketitle

\\begin{{abstract}}
{_paragraphs(paper.get("abstract"))}
\\end{{abstract}}

\\noindent\\textbf{{Keywords:}} {_latex_escape(keyword_text)}

\\section{{Research question}}
{_latex_escape(project["research_question"])}

\\section{{Hypotheses}}
{_hypotheses(project)}

\\section{{Statement of need}}
{_paragraphs(paper.get("statement_of_need"))}

\\section{{State of the field}}
{_paragraphs(paper.get("state_of_field"))}

The computational workflow can use Stim \\cite{{gidney2021stim}} and
PyMatching sparse blossom \\cite{{Higgott2025sparseblossom}}.

\\section{{Software and research design}}
{_paragraphs(paper.get("software_design"))}

\\section{{Methods}}
{_paragraphs(paper.get("methods"))}

The project was represented by a versioned Aegis research-project manifest.
Result and interpretation claims were audited against declared artifacts and,
where configured, JSON-pointer predicates.

\\section{{Results}}
{_paragraphs(paper.get("results_context"))}

{_result_claims(project)}

\\section{{Limitations}}
{_paragraphs(paper.get("limitations"))}

\\section{{Research impact}}
{_paragraphs(paper.get("impact"))}

\\section{{Data availability}}
{_paragraphs(paper.get("data_availability"))}

\\section{{Code availability}}
{_paragraphs(paper.get("code_availability"))}

\\section{{AI usage disclosure}}
{_paragraphs(paper.get("ai_usage_disclosure"))}

\\section{{Competing interests}}
{_paragraphs(paper.get("competing_interests", "None declared."))}

\\section{{Funding}}
{_paragraphs(paper.get("funding", "No funding statement provided."))}

\\appendix
\\section{{Claim-to-evidence audit}}
\\begin{{longtable}}{{L{{0.15\\linewidth}} L{{0.14\\linewidth}} L{{0.10\\linewidth}} L{{0.52\\linewidth}}}}
\\toprule
Claim & Type & Audit & Evidence \\\\
\\midrule
\\endhead
{_claim_table(audit)}
\\bottomrule
\\end{{longtable}}

\\section{{Artifact inventory}}
\\begin{{longtable}}{{L{{0.18\\linewidth}} L{{0.13\\linewidth}} L{{0.43\\linewidth}} L{{0.18\\linewidth}}}}
\\toprule
Artifact & Kind & File & SHA-256 prefix \\\\
\\midrule
\\endhead
{_artifact_table(audit)}
\\bottomrule
\\end{{longtable}}

\\section{{Reproducibility note}}
A passing Aegis audit establishes traceability and integrity of the declared
evidence. It does not by itself establish external validity, absence of bias,
or generalization beyond the sampled workloads.

\\bibliographystyle{{plain}}
\\bibliography{{references}}
\\end{{document}}
"""


def _paper_md(project: dict[str, Any]) -> str:
    paper = project.get("paper", {})
    lines = [
        "# " + project["title"],
        "",
        "Authors: " + ", ".join(a["name"] for a in project["authors"]),
        "",
        "## Summary",
        str(paper.get("abstract", "")).strip() or "Not provided.",
        "",
        "## Statement of need",
        str(paper.get("statement_of_need", "")).strip() or "Not provided.",
        "",
        "## State of the field",
        str(paper.get("state_of_field", "")).strip() or "Not provided.",
        "",
        "## Software design",
        str(paper.get("software_design", "")).strip() or "Not provided.",
        "",
        "## Methods",
        str(paper.get("methods", "")).strip() or "Not provided.",
        "",
        "## Results",
    ]
    for claim in project.get("claims", []):
        if str(claim.get("type", "result")).lower() in {"result", "interpretation"}:
            lines.append("- " + claim["id"] + ": " + claim["text"])
    lines.extend(
        [
            "",
            "## Limitations",
            str(paper.get("limitations", "")).strip() or "Not provided.",
            "",
            "## Research impact",
            str(paper.get("impact", "")).strip() or "Not provided.",
            "",
            "## Data availability",
            str(paper.get("data_availability", "")).strip() or "Not provided.",
            "",
            "## Code availability",
            str(paper.get("code_availability", "")).strip() or "Not provided.",
            "",
            "## AI usage disclosure",
            str(paper.get("ai_usage_disclosure", "")).strip() or "Not provided.",
            "",
        ]
    )
    return "\n".join(lines)


def _reviewer_readme(project: dict[str, Any], audit: dict[str, Any]) -> str:
    return f"""# Reviewer roadmap

Research package: {project["title"]}

Packaging-time claim/evidence audit: {"PASS" if audit["valid"] else "FAIL"}

Fast review path:

1. Read manuscript/paper.pdf when present, otherwise manuscript/paper.tex.
2. Read CLAIM_EVIDENCE.md for claim-to-artifact traceability.
3. Read audit.json for machine-readable evidence checks.
4. Read REPRODUCE.md for verification commands.
5. Inspect artifacts/ for declared evidence.
6. Verify MANIFEST.json or checksums.sha256 before using artifacts.

Scientific boundary:

A passing audit means declared files exist, hashes were recorded, JSON pointers
resolve, and declared predicates hold. It does not certify an unbiased design,
a realistic device model, or generalization beyond the stated workloads.

Questions a strict reviewer should still ask:

- Does the research question match the experiment design?
- Were confirmatory hypotheses frozen before the relevant experiments?
- Are baselines and competing methods appropriate?
- Are all quantitative claims linked to artifacts?
- Are uncertainty intervals and paired tests appropriate?
- Are negative or null results reported?
- Are code, data, seeds, versions, and commands sufficient?
- Are limitations and external-validity boundaries explicit?
- Is AI assistance disclosed and human validation described?

Project SHA-256: {audit["project_sha256"]}
"""


def _reproduce(project_path: Path, audit: dict[str, Any]) -> str:
    command = "aegis project audit " + project_path.name
    if audit.get("protocol_lock") is not None:
        command += " --require-protocol-lock"
    return f"""# Reproduction and verification

Verify the project:

    {command}

Verify individual experiment bundles:

    aegis verify-bundle path/to/experiment.aegis.zip

Verify reusable datasets:

    aegis dataset inspect path/to/dataset.h5 --json

Re-run a paired decoder comparison:

    aegis dataset evaluate path/to/dataset.h5 --decoder DECODER_A DECODER_B --split test --json

See environment.json for package and platform versions observed when this
submission package was assembled. MANIFEST.json and checksums.sha256 cover the
packaged payload.
"""


def _claim_map(audit: dict[str, Any]) -> str:
    lines = [
        "# Claim-to-evidence map",
        "",
        "Overall audit: " + ("PASS" if audit["valid"] else "FAIL"),
        "",
    ]
    for claim in audit["claims"]:
        lines.extend(
            [
                "## " + claim["id"],
                "",
                "Type: " + claim["type"],
                "",
                claim["text"],
                "",
                "Audit: " + ("PASS" if claim["passed"] else "FAIL"),
                "",
            ]
        )
        for item in claim["evidence"]:
            label = "- artifact " + str(item.get("artifact", ""))
            if item.get("json_pointer"):
                label += "; pointer " + str(item["json_pointer"])
            if "actual" in item:
                label += "; observed " + repr(item["actual"])
            label += "; " + ("PASS" if item.get("passed") else "FAIL")
            lines.append(label)
        lines.append("")
    return "\n".join(lines)


def _checklist(project: dict[str, Any], audit: dict[str, Any]) -> str:
    paper = project.get("paper", {})
    checks = [
        ("Research question is explicit", bool(project.get("research_question"))),
        ("At least one author is declared", bool(project.get("authors"))),
        ("Project audit passes", bool(audit["valid"])),
        ("Statement of need is present", bool(paper.get("statement_of_need"))),
        ("State-of-field comparison is present", bool(paper.get("state_of_field"))),
        ("Design rationale is present", bool(paper.get("software_design"))),
        ("Limitations are present", bool(paper.get("limitations"))),
        ("Data availability is present", bool(paper.get("data_availability"))),
        ("Code availability is present", bool(paper.get("code_availability"))),
        ("AI usage disclosure is present", bool(paper.get("ai_usage_disclosure"))),
    ]
    lines = [
        "# Submission readiness checklist",
        "",
        "Preparation aid only; this is not a guarantee of venue compliance.",
        "",
    ]
    for label, passed in checks:
        lines.append("- [" + ("x" if passed else " ") + "] " + label)
    lines.extend(
        [
            "",
            "Venue-specific checks still required:",
            "",
            "- current page limit and official style",
            "- anonymity requirements",
            "- code/data upload size and artifact rules",
            "- ethics, impact, conflict, and funding requirements",
            "- a human author reading and approving every generated sentence",
        ]
    )
    return "\n".join(lines)


def _redacted_protocol_lock(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    redacted = {
        "schema_version": value.get("schema_version", 1),
        "lock_type": value.get("lock_type"),
        "created_utc": value.get("created_utc"),
        "project_title": value.get("project_title"),
        "protocol_sha256": value.get("protocol_sha256"),
        "redacted": True,
        "files": [],
    }
    for item in value.get("files", []):
        redacted["files"].append(
            {
                "role": item.get("role"),
                "path": Path(str(item.get("path", ""))).name,
                "sha256": item.get("sha256"),
            }
        )
    return redacted


def _copy_artifacts(
    audit: dict[str, Any],
    root: Path,
    *,
    anonymize: bool,
) -> list[dict[str, Any]]:
    records = []
    for artifact_id in sorted(audit["artifacts"]):
        artifact = audit["artifacts"][artifact_id]
        if not artifact.get("exists"):
            continue
        source = Path(artifact["source_path"])
        target_dir = root / artifact_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        shutil.copy2(source, target)
        record = {
            "id": artifact_id,
            "packaged": str(target.relative_to(root.parent)),
            "sha256": _sha256_file(target),
            "bytes": target.stat().st_size,
        }
        if not anonymize:
            record["source"] = str(source)
        records.append(record)
    return records


def _compile(manuscript_dir: Path, mode: str) -> dict[str, Any]:
    if mode not in {"auto", "never", "required"}:
        raise ValueError("compile mode must be auto, never, or required")
    if mode == "never":
        return {"requested": False, "compiled": False, "engine": None}

    choices = []
    if shutil.which("tectonic"):
        choices.append(
            ("tectonic", ["tectonic", "--keep-logs", "paper.tex"])
        )
    if shutil.which("latexmk"):
        choices.append(
            (
                "latexmk",
                [
                    "latexmk",
                    "-pdf",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "paper.tex",
                ],
            )
        )
    if not choices:
        if mode == "required":
            raise RuntimeError(
                "No supported LaTeX compiler found; install tectonic or latexmk."
            )
        return {
            "requested": True,
            "compiled": False,
            "engine": None,
            "reason": "compiler unavailable",
        }

    engine, command = choices[0]
    result = subprocess.run(
        command,
        cwd=manuscript_dir,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    log_path = manuscript_dir / "aegis-latex-build.log"
    log_path.write_text(
        "$ "
        + " ".join(command)
        + "\n\n"
        + result.stdout
        + "\n--- stderr ---\n"
        + result.stderr,
        encoding="utf-8",
    )
    compiled = result.returncode == 0 and (manuscript_dir / "paper.pdf").is_file()
    if not compiled and mode == "required":
        raise RuntimeError(
            "LaTeX compilation failed; see " + str(log_path)
        )
    return {
        "requested": True,
        "compiled": compiled,
        "engine": engine,
        "returncode": result.returncode,
        "log": str(log_path),
    }


def _payload(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in {"MANIFEST.json", "checksums.sha256"}:
            continue
        rows.append(
            {
                "path": rel,
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return rows


def _zip_directory(source: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w") as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(source).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def build_submission_package(
    project_path: str,
    *,
    output_dir: str,
    compile_mode: str = "auto",
    require_protocol_lock: bool = False,
    allow_invalid: bool = False,
    anonymize: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = Path(project_path).resolve()
    project = load_research_project(str(source))
    audit = audit_research_project(
        str(source),
        require_protocol_lock=require_protocol_lock,
    )
    if not audit["valid"] and not allow_invalid:
        raise ValueError(
            "research project audit failed: " + "; ".join(audit["errors"])
        )

    destination = Path(output_dir).resolve()
    zip_path = Path(str(destination) + ".zip")
    if destination.exists() or zip_path.exists():
        if not overwrite:
            raise FileExistsError(
                "submission output already exists; choose a new path or use overwrite"
            )
        if destination.exists():
            shutil.rmtree(destination)
        if zip_path.exists():
            zip_path.unlink()
    destination.mkdir(parents=True)
    manuscript = destination / "manuscript"
    artifacts = destination / "artifacts"
    manuscript.mkdir()
    artifacts.mkdir()

    packaged_project = (
        _anonymize_project(project)
        if anonymize
        else copy.deepcopy(project)
    )
    packaged_audit = _sanitize_audit(audit, anonymize=anonymize)
    (destination / "research-project.json").write_text(
        json.dumps(packaged_project, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lock = source.with_suffix(".protocol.lock.json")
    if lock.is_file():
        packaged_lock = destination / "research-project.protocol.lock.json"
        if anonymize:
            packaged_lock.write_text(
                json.dumps(
                    _redacted_protocol_lock(lock),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        else:
            shutil.copy2(lock, packaged_lock)

    (destination / "audit.json").write_text(
        json.dumps(packaged_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (destination / "environment.json").write_text(
        json.dumps(_environment(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (destination / "CLAIM_EVIDENCE.md").write_text(
        _claim_map(packaged_audit) + "\n",
        encoding="utf-8",
    )
    (destination / "REVIEWER_README.md").write_text(
        _reviewer_readme(packaged_project, packaged_audit) + "\n",
        encoding="utf-8",
    )
    (destination / "REPRODUCE.md").write_text(
        _reproduce(Path("research-project.json"), packaged_audit) + "\n",
        encoding="utf-8",
    )
    (destination / "SUBMISSION_CHECKLIST.md").write_text(
        _checklist(packaged_project, packaged_audit) + "\n",
        encoding="utf-8",
    )

    inventory = _copy_artifacts(
        audit,
        artifacts,
        anonymize=anonymize,
    )
    (destination / "artifact-inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    (manuscript / "paper.tex").write_text(
        _tex(packaged_project, packaged_audit),
        encoding="utf-8",
    )
    (manuscript / "paper.md").write_text(
        _paper_md(packaged_project) + "\n",
        encoding="utf-8",
    )
    (manuscript / "references.bib").write_text(
        _references(source, project),
        encoding="utf-8",
    )

    compile_result = _compile(manuscript, compile_mode)
    (destination / "latex-build.json").write_text(
        json.dumps(compile_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    payload = _payload(destination)
    manifest = {
        "schema_version": 1,
        "package_type": "aegis_qec_submission_package",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_title": packaged_project["title"],
        "project_sha256": audit["project_sha256"],
        "audit_valid": audit["valid"],
        "anonymized": bool(anonymize),
        "payload": payload,
    }
    manifest_path = destination / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checks = payload + [
        {
            "path": "MANIFEST.json",
            "sha256": _sha256_file(manifest_path),
            "bytes": manifest_path.stat().st_size,
        }
    ]
    (destination / "checksums.sha256").write_text(
        "".join(
            item["sha256"] + "  " + item["path"] + "\n"
            for item in checks
        ),
        encoding="utf-8",
    )

    _zip_directory(destination, zip_path)

    return {
        "schema_version": 1,
        "package_type": "aegis_qec_submission_package",
        "path": str(destination),
        "zip_path": str(zip_path),
        "zip_sha256": _sha256_file(zip_path),
        "audit_valid": audit["valid"],
        "compile": compile_result,
        "artifact_count": len(inventory),
        "claim_count": len(audit["claims"]),
    }



def verify_submission_package(path: str) -> dict[str, Any]:
    """Verify payload hashes in a submission directory or ZIP file."""

    source = Path(path).resolve()
    failures: list[str] = []

    if source.is_dir():
        manifest_path = source / "MANIFEST.json"
        if not manifest_path.is_file():
            raise ValueError("submission directory is missing MANIFEST.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest.get("payload", []):
            payload_path = source / str(item["path"])
            if not payload_path.is_file():
                failures.append("missing payload: " + str(item["path"]))
                continue
            if payload_path.stat().st_size != int(item["bytes"]):
                failures.append("size mismatch: " + str(item["path"]))
            if _sha256_file(payload_path) != str(item["sha256"]):
                failures.append("hash mismatch: " + str(item["path"]))
        expected_names = {
            str(item["path"])
            for item in manifest.get("payload", [])
        } | {"MANIFEST.json", "checksums.sha256"}
        actual_names = {
            path.relative_to(source).as_posix()
            for path in source.rglob("*")
            if path.is_file()
        }
        for extra in sorted(actual_names - expected_names):
            failures.append("unexpected payload: " + extra)
        source_hash = None
    elif source.is_file() and source.suffix.lower() == ".zip":
        source_hash = _sha256_file(source)
        with zipfile.ZipFile(source, "r") as archive:
            names = set(archive.namelist())
            if "MANIFEST.json" not in names:
                raise ValueError("submission ZIP is missing MANIFEST.json")
            manifest = json.loads(
                archive.read("MANIFEST.json").decode("utf-8")
            )
            expected_names = {
                str(item["path"])
                for item in manifest.get("payload", [])
            } | {"MANIFEST.json", "checksums.sha256"}
            for extra in sorted(names - expected_names):
                failures.append("unexpected payload: " + extra)
            for item in manifest.get("payload", []):
                name = str(item["path"])
                if name not in names:
                    failures.append("missing payload: " + name)
                    continue
                data = archive.read(name)
                if len(data) != int(item["bytes"]):
                    failures.append("size mismatch: " + name)
                if hashlib.sha256(data).hexdigest() != str(item["sha256"]):
                    failures.append("hash mismatch: " + name)
    else:
        raise ValueError("submission path must be a directory or .zip file")

    return {
        "schema_version": 1,
        "verification_type": "aegis_qec_submission_package",
        "path": str(source),
        "valid": not failures,
        "failures": failures,
        "zip_sha256": source_hash,
    }
