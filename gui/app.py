from __future__ import annotations

import csv
import importlib.metadata as metadata
import io
import json
import random
import time
from pathlib import Path

try:
    import streamlit as st

    STREAMLIT_OK = True
except Exception:
    STREAMLIT_OK = False


DECODER_LABELS = {
    "mwpm": "Sparse-blossom MWPM — recommended",
    "mwpm2": "Two-pass correlation-aware MWPM — experimental",
    "mwpm_corr": "Correlation-model MWPM — experimental",
    "uf": "Union Find with erasures — experimental",
}

REWEIGHTER_LABELS = {
    "none": "None — recommended",
    "bp": "Belief-propagation reweighting — experimental",
    "transformer": "Transformer reweighting — experimental",
    "transformer_sota": "Transformer SOTA reweighting — experimental",
}


def _version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not installed"


def _percentile(samples, fraction):
    ordered = sorted(samples)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(fraction * len(ordered)) - 1))
    return ordered[index]


def _research_project_tab():
    from aegis_qec.project import (
        freeze_research_protocol,
        run_research_project,
        write_research_project_template,
    )

    st.write(
        "Create a reviewable research project, freeze confirmatory protocols, "
        "and execute all declared experiments from one project file."
    )
    col1, col2 = st.columns(2)
    with col1:
        project_path = st.text_input(
            "Research project path",
            value="research-project.json",
            key="studio_project_path",
            help="JSON project contract containing the question, protocol, evidence, and paper metadata.",
        )
        author = st.text_input(
            "Lead author",
            value="Researcher",
            key="studio_project_author",
        )
    with col2:
        workspace = st.text_input(
            "Project run workspace",
            value="research_out/project",
            key="studio_project_workspace",
        )
        overwrite = st.checkbox(
            "Replace starter files if they already exist",
            value=False,
            key="studio_project_overwrite",
        )

    create_col, freeze_col, run_col = st.columns(3)
    with create_col:
        if st.button(
            "Create starter project",
            type="primary",
            key="studio_create_project",
            use_container_width=True,
        ):
            try:
                created = write_research_project_template(
                    project_path,
                    author_name=author,
                    overwrite=overwrite,
                )
                st.session_state["studio_project_created"] = created
                st.success(f"Created {created['project_path']}")
            except Exception as exc:
                st.error(f"Project creation failed: {type(exc).__name__}: {exc}")

    with freeze_col:
        if st.button(
            "Freeze protocol",
            key="studio_freeze_project",
            use_container_width=True,
        ):
            try:
                lock = freeze_research_protocol(project_path)
                st.session_state["studio_protocol_lock"] = lock
                st.success("Protocol frozen.")
                st.code(lock["protocol_sha256"])
            except Exception as exc:
                st.error(f"Protocol freeze failed: {type(exc).__name__}: {exc}")

    with run_col:
        if st.button(
            "Run project",
            key="studio_run_project",
            use_container_width=True,
        ):
            try:
                report = run_research_project(
                    project_path,
                    workspace=workspace,
                )
                st.session_state["studio_project_run"] = report
                st.success("Project run completed.")
            except Exception as exc:
                st.error(f"Project run failed: {type(exc).__name__}: {exc}")

    report = st.session_state.get("studio_project_run")
    if report:
        st.subheader("Latest project run")
        metrics = st.columns(3)
        metrics[0].metric("Experiments", len(report.get("experiments", [])))
        metrics[1].metric("Discoveries", len(report.get("discoveries", [])))
        metrics[2].metric(
            "Evidence record",
            "saved" if report.get("path") else "missing",
        )
        rows = []
        for item in report.get("experiments", []):
            rows.append(
                {
                    "kind": "experiment",
                    "id": item["id"],
                    "evidence": item["bundle"]["path"],
                }
            )
        for item in report.get("discoveries", []):
            rows.append(
                {
                    "kind": "discovery",
                    "id": item["id"],
                    "evidence": item["result_path"],
                }
            )
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption(
            "Project execution preserves experiment bundles and discovery records; "
            "it does not convert exploratory search into confirmatory evidence."
        )


def _research_discovery_tab():
    from aegis_qec.discovery import run_discovery, write_discovery_starter

    st.write(
        "Search declared experiment parameters while preserving every candidate, "
        "objective value, failure, and confirmation proposal."
    )
    col1, col2 = st.columns(2)
    with col1:
        discovery_path = st.text_input(
            "Discovery configuration",
            value="discovery.json",
            key="studio_discovery_path",
        )
    with col2:
        discovery_out = st.text_input(
            "Discovery workspace",
            value="research_out/discovery",
            key="studio_discovery_out",
        )

    create_col, run_col = st.columns(2)
    with create_col:
        if st.button(
            "Create discovery starter",
            key="studio_create_discovery",
            use_container_width=True,
        ):
            try:
                created = write_discovery_starter(discovery_path)
                st.session_state["studio_discovery_created"] = created
                st.success("Discovery starter created.")
                st.write(created)
            except Exception as exc:
                st.error(
                    f"Discovery starter failed: {type(exc).__name__}: {exc}"
                )

    with run_col:
        if st.button(
            "Run or resume discovery",
            type="primary",
            key="studio_run_discovery",
            use_container_width=True,
        ):
            try:
                report = run_discovery(
                    discovery_path,
                    output_dir=discovery_out,
                )
                st.session_state["studio_discovery_report"] = report
                st.success("Exploratory discovery completed.")
            except Exception as exc:
                st.error(f"Discovery failed: {type(exc).__name__}: {exc}")

    report = st.session_state.get("studio_discovery_report")
    if report:
        metrics = st.columns(4)
        metrics[0].metric("Evaluated", report["evaluated"])
        metrics[1].metric("Succeeded", report["successful"])
        metrics[2].metric("Failed", report["failed"])
        metrics[3].metric("Pareto candidates", len(report["pareto_front"]))

        if report["pareto_front"]:
            rows = []
            for rank, item in enumerate(report["pareto_front"], start=1):
                row = {
                    "rank": rank,
                    "candidate": item["key"],
                }
                row.update(
                    {
                        f"objective:{name}": value
                        for name, value in item["objectives"].items()
                    }
                )
                row.update(
                    {
                        f"parameter:{name}": value
                        for name, value in item["assignment"].items()
                    }
                )
                rows.append(row)
            st.subheader("Pareto front")
            st.dataframe(rows, use_container_width=True, hide_index=True)

        if report["confirmation_manifests"]:
            st.subheader("Independent confirmation candidates")
            st.dataframe(
                report["confirmation_manifests"],
                use_container_width=True,
                hide_index=True,
            )
        st.warning(report["interpretation"])


def _research_evidence_tab():
    from aegis_qec.project import audit_research_project

    st.write(
        "Audit claims against declared files and exact JSON fields before writing "
        "or submitting conclusions."
    )
    col1, col2 = st.columns([3, 1])
    with col1:
        project_path = st.text_input(
            "Project to audit",
            value=st.session_state.get(
                "studio_project_path",
                "research-project.json",
            ),
            key="studio_audit_path",
        )
    with col2:
        require_lock = st.checkbox(
            "Require protocol lock",
            value=False,
            key="studio_audit_lock",
        )

    if st.button(
        "Audit evidence",
        type="primary",
        key="studio_audit_project",
    ):
        try:
            report = audit_research_project(
                project_path,
                require_protocol_lock=require_lock,
            )
            st.session_state["studio_audit_report"] = report
        except Exception as exc:
            st.error(f"Audit failed to run: {type(exc).__name__}: {exc}")

    report = st.session_state.get("studio_audit_report")
    if report:
        if report["valid"]:
            st.success("Project evidence audit passed.")
        else:
            st.error("Project evidence audit failed.")

        metrics = st.columns(4)
        metrics[0].metric("Claims", len(report.get("claims", [])))
        metrics[1].metric("Artifacts", len(report.get("artifacts", {})))
        metrics[2].metric("Experiments", len(report.get("experiments", [])))
        metrics[3].metric("Discoveries", len(report.get("discoveries", [])))

        if report["errors"]:
            st.subheader("Blocking errors")
            for error in report["errors"]:
                st.write(f"- {error}")
        if report["warnings"]:
            with st.expander("Warnings"):
                for warning in report["warnings"]:
                    st.write(f"- {warning}")

        if report.get("claims"):
            st.subheader("Claim-to-evidence status")
            st.dataframe(
                [
                    {
                        "claim": item["id"],
                        "type": item["type"],
                        "passed": item["passed"],
                        "text": item["text"],
                        "evidence_items": len(item["evidence"]),
                    }
                    for item in report["claims"]
                ],
                use_container_width=True,
                hide_index=True,
            )


def _research_submission_tab():
    from aegis_qec.paper import (
        build_submission_package,
        verify_submission_package,
    )

    st.write(
        "Generate LaTeX/Markdown manuscript sources plus the reviewer evidence "
        "package. Package integrity and scientific submission readiness are "
        "reported separately."
    )
    project_path = st.text_input(
        "Project for manuscript",
        value=st.session_state.get(
            "studio_project_path",
            "research-project.json",
        ),
        key="studio_submission_project",
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        output = st.text_input(
            "Submission directory",
            value="research_out/submission",
            key="studio_submission_out",
        )
    with col2:
        compile_mode = st.selectbox(
            "PDF compilation",
            ["auto", "never", "required"],
            index=0,
            key="studio_compile_mode",
            help="Auto uses Tectonic or latexmk when installed.",
        )
    with col3:
        anonymous = st.checkbox(
            "Blind-review package",
            value=False,
            key="studio_anonymous",
        )
        require_lock = st.checkbox(
            "Require protocol lock",
            value=False,
            key="studio_submission_lock",
        )

    if st.button(
        "Build reviewer package",
        type="primary",
        key="studio_build_submission",
    ):
        try:
            report = build_submission_package(
                project_path,
                output_dir=output,
                compile_mode=compile_mode,
                require_protocol_lock=require_lock,
                anonymize=anonymous,
                overwrite=True,
            )
            verification = verify_submission_package(report["zip_path"])
            st.session_state["studio_submission_report"] = report
            st.session_state["studio_submission_verification"] = verification
        except Exception as exc:
            st.error(
                f"Submission package failed: {type(exc).__name__}: {exc}"
            )

    report = st.session_state.get("studio_submission_report")
    verification = st.session_state.get("studio_submission_verification")
    if report:
        metrics = st.columns(4)
        metrics[0].metric(
            "Evidence audit",
            "PASS" if report["audit_valid"] else "FAIL",
        )
        metrics[1].metric(
            "Submission readiness",
            "PASS" if report.get("submission_ready") else "INCOMPLETE",
        )
        metrics[2].metric(
            "Package integrity",
            (
                "PASS"
                if verification and verification.get("valid")
                else "FAIL"
            ),
        )
        metrics[3].metric(
            "PDF",
            "built" if report["compile"].get("compiled") else "source only",
        )

        failures = report.get("submission_readiness", {}).get("failures", [])
        if failures:
            st.subheader("Readiness gaps")
            for failure in failures:
                st.write(f"- {failure['message']}")
        else:
            st.success(
                "Machine-audited readiness checks pass. Human scientific and "
                "venue-specific review is still required."
            )

        st.write(f"Reviewer ZIP: {report['zip_path']}")
        zip_path = Path(report["zip_path"])
        if zip_path.is_file():
            st.download_button(
                "Download reviewer ZIP",
                data=zip_path.read_bytes(),
                file_name=zip_path.name,
                mime="application/zip",
                key="studio_download_submission",
            )


def _research_studio():
    st.header("Research Studio")
    st.caption(
        "Move from a research question to exploratory discovery, evidence audit, "
        "and a reviewer-grade manuscript package using one evidence model."
    )
    project_tab, discovery_tab, evidence_tab, submission_tab = st.tabs(
        ["Project", "Discovery", "Evidence", "Submission"]
    )
    with project_tab:
        _research_project_tab()
    with discovery_tab:
        _research_discovery_tab()
    with evidence_tab:
        _research_evidence_tab()
    with submission_tab:
        _research_submission_tab()


def main():
    if not STREAMLIT_OK:
        print("Aegis QEC GUI requires the optional GUI extra.")
        print("Install it with: python -m pip install -U 'aegis-qec[gui]'")
        return 2

    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
    from a3d.decoder_mwpm import MWPMDecoder

    st.set_page_config(page_title="Aegis QEC", page_icon="🛡️", layout="wide")
    st.title("Aegis QEC")
    st.caption("A research workbench for hardware-aware quantum error-correction experiments.")

    with st.sidebar:
        st.header("Environment")
        st.write(f"Aegis QEC: {_version('aegis-qec')}")
        st.write(f"PyMatching: {_version('pymatching')}")
        st.write(f"Backend: {MWPMDecoder.backend}")
        st.write(f"Stim: {_version('stim')}")
        st.write(f"Streamlit: {_version('streamlit')}")
        st.divider()
        st.caption("Use 'aegis doctor' in a terminal for a complete installation check.")

    st.info(
        "The published >100,000× comparison belongs to PyMatching's named surface-code "
        "benchmark against NetworkX. Results in this application are Aegis end-to-end measurements."
    )

    _research_studio()

    st.divider()
    st.header("Decoder and circuit lab")
    st.caption(
        "Use these lower-level tools for teaching, debugging, controlled sweeps, "
        "and circuit studies. Publication workflows should preserve the exported evidence."
    )
    st.subheader("Experiment configuration")
    col1, col2, col3 = st.columns(3)

    with col1:
        decoder = st.selectbox(
            "Decoder",
            list(DECODER_LABELS),
            format_func=DECODER_LABELS.get,
            help="Sparse-blossom MWPM is the default validated production backend.",
        )
        reweighter = st.selectbox(
            "Edge reweighting",
            list(REWEIGHTER_LABELS),
            format_func=REWEIGHTER_LABELS.get,
            help="Reweighting modes other than None are experimental research paths.",
        )

    with col2:
        distance = st.slider("Code distance", 3, 11, 5, 2)
        rounds = st.slider("Syndrome rounds", 2, 12, 6, 1)

    with col3:
        error_probability = st.slider(
            "Synthetic detection-event probability",
            0.0,
            0.2,
            0.05,
            0.005,
        )
        seed = st.number_input("Random seed", min_value=0, value=123, step=1)

    try:
        cfg = AegisConfig(
            distance=distance,
            rounds=rounds,
            decoder_type=decoder,
            reweighter_type=reweighter,
            run_certificate=False,
        )
        runtime = DecoderRuntime(cfg, RotatedSurfaceLayout(cfg.distance))
    except Exception as exc:
        st.error(f"Could not construct this experiment: {type(exc).__name__}: {exc}")
        return 1

    decode_tab, latency_tab, sweep_tab, study_tab, explain_tab = st.tabs(
        ["Decode", "Latency", "Validation sweep", "Circuit study", "Explain one shot"]
    )

    with decode_tab:
        st.write(
            "Generate a deterministic synthetic syndrome using the selected probability, "
            "then decode it with the selected backend."
        )
        if st.button("Run demo decode", type="primary"):
            try:
                n_x = len(runtime.builder.node_order("X"))
                n_z = len(runtime.builder.node_order("Z"))
                rng = random.Random(int(seed))
                syndrome_x = [int(rng.random() < error_probability) for _ in range(n_x)]
                syndrome_z = [int(rng.random() < error_probability) for _ in range(n_z)]

                started = time.perf_counter()
                result_x, result_z = runtime.decode_from_syndromes_uniform(
                    syndrome_x,
                    syndrome_z,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000.0

                metric1, metric2, metric3, metric4 = st.columns(4)
                metric1.metric("Decode time", f"{elapsed_ms:.3f} ms")
                metric2.metric("X detection events", sum(syndrome_x))
                metric3.metric("Z detection events", sum(syndrome_z))
                metric4.metric(
                    "Correction edges",
                    len(result_x.corrections) + len(result_z.corrections),
                )

                with st.expander("Detailed result"):
                    st.write(f"Backend: {MWPMDecoder.backend}")
                    st.write(f"X average correction cost: {result_x.avg_cost:.6f}")
                    st.write(f"Z average correction cost: {result_z.avg_cost:.6f}")
                    st.write(f"X correction edges: {len(result_x.corrections)}")
                    st.write(f"Z correction edges: {len(result_z.corrections)}")
            except Exception as exc:
                st.error(f"Decode failed: {type(exc).__name__}: {exc}")

    with latency_tab:
        st.write("Measure end-to-end Aegis latency on deterministic synthetic syndromes.")
        trials = st.slider("Latency samples", 10, 500, 50, 10)
        if st.button("Measure latency"):
            try:
                n_x = len(runtime.builder.node_order("X"))
                n_z = len(runtime.builder.node_order("Z"))
                rng = random.Random(1)
                samples = []

                for _ in range(trials):
                    syndrome_x = [rng.randint(0, 1) for _ in range(n_x)]
                    syndrome_z = [rng.randint(0, 1) for _ in range(n_z)]
                    started = time.perf_counter()
                    runtime.decode_from_syndromes_uniform(syndrome_x, syndrome_z)
                    samples.append(time.perf_counter() - started)

                p50, p95, p99 = st.columns(3)
                p50.metric("p50", f"{_percentile(samples, 0.50) * 1e3:.3f} ms")
                p95.metric("p95", f"{_percentile(samples, 0.95) * 1e3:.3f} ms")
                p99.metric("p99", f"{_percentile(samples, 0.99) * 1e3:.3f} ms")
            except Exception as exc:
                st.error(f"Latency experiment failed: {type(exc).__name__}: {exc}")

    with sweep_tab:
        st.write("Run a small deterministic sweep and inspect correction-validation failures.")
        probabilities = st.multiselect(
            "Physical error probabilities",
            [0.01, 0.02, 0.04, 0.06, 0.08],
            default=[0.02, 0.06],
        )
        trials = st.slider("Trials per probability", 10, 500, 50, 10, key="sweep_trials")
        if st.button("Run validation sweep"):
            if not probabilities:
                st.warning("Choose at least one physical error probability.")
            else:
                try:
                    from bench.cli import sweep

                    data = sweep(
                        decoder,
                        probabilities,
                        distance=distance,
                        rounds=rounds,
                        trials=trials,
                    )
                    st.dataframe(
                        [
                            {"synthetic_event_probability": p, "validation_failure_rate": rate}
                            for p, rate in data
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                except Exception as exc:
                    st.error(f"Sweep failed: {type(exc).__name__}: {exc}")

    with study_tab:
        st.write(
            "Run a real circuit-level rotated surface-code memory study with Stim, "
            "decode the sampled detector events through Aegis, and export a reproducible record."
        )
        if _version("stim") == "not installed":
            st.warning(
                "Circuit studies require Stim. Install the full scientific extra with "
                "python -m pip install -U 'aegis-qec[full]'."
            )
        else:
            study_col1, study_col2, study_col3 = st.columns(3)
            with study_col1:
                study_distances = st.multiselect(
                    "Study distances",
                    [3, 5, 7, 9, 11],
                    default=[3, 5, 7],
                )
                study_basis = st.selectbox(
                    "Memory basis",
                    ["x", "z"],
                    help="Choose the logical memory experiment generated by Stim.",
                )
            with study_col2:
                study_probabilities = st.multiselect(
                    "Circuit error probabilities",
                    [0.001, 0.002, 0.003, 0.005, 0.006, 0.008, 0.01, 0.015, 0.02],
                    default=[0.003, 0.006, 0.01],
                )
                study_shots = st.slider(
                    "Shots per point",
                    100,
                    10000,
                    1000,
                    100,
                )
            with study_col3:
                use_distance_rounds = st.checkbox(
                    "Use rounds = distance",
                    value=True,
                    help="Recommended for a first scaling study.",
                )
                study_rounds = st.number_input(
                    "Fixed rounds",
                    min_value=1,
                    value=5,
                    step=1,
                    disabled=use_distance_rounds,
                )
                study_seed = st.number_input(
                    "Study base seed",
                    min_value=0,
                    value=1234,
                    step=1,
                )

            if st.button("Run circuit study", type="primary"):
                if not study_distances or not study_probabilities:
                    st.warning("Choose at least one distance and one physical error probability.")
                else:
                    try:
                        import matplotlib.pyplot as plt

                        from aegis_qec.research import run_surface_code_study

                        study = run_surface_code_study(
                            distances=study_distances,
                            physical_error_rates=study_probabilities,
                            shots=int(study_shots),
                            basis=study_basis,
                            rounds=None if use_distance_rounds else int(study_rounds),
                            seed=int(study_seed),
                        )
                        st.session_state["aegis_circuit_study"] = study

                        table = [
                            {
                                "distance": point["distance"],
                                "rounds": point["rounds"],
                                "p": point["physical_error_rate"],
                                "shots": point["shots"],
                                "failures": point["logical_failures"],
                                "logical_error_rate": point["logical_error_rate"],
                                "ci95_low": point["ci95_low"],
                                "ci95_high": point["ci95_high"],
                                "decode_shots_per_second": point["decode_shots_per_second"],
                            }
                            for point in study["points"]
                        ]
                        st.dataframe(table, use_container_width=True, hide_index=True)

                        fig, ax = plt.subplots(figsize=(7.0, 4.5))
                        for study_distance in sorted(
                            {int(point["distance"]) for point in study["points"]}
                        ):
                            selected = sorted(
                                (
                                    point
                                    for point in study["points"]
                                    if int(point["distance"]) == study_distance
                                ),
                                key=lambda point: float(point["physical_error_rate"]),
                            )
                            x_values = [
                                float(point["physical_error_rate"]) for point in selected
                            ]
                            y_values = [
                                float(point["logical_error_rate"]) for point in selected
                            ]
                            lower = [
                                max(0.0, y - float(point["ci95_low"]))
                                for y, point in zip(y_values, selected, strict=True)
                            ]
                            upper = [
                                max(0.0, float(point["ci95_high"]) - y)
                                for y, point in zip(y_values, selected, strict=True)
                            ]
                            ax.errorbar(
                                x_values,
                                y_values,
                                yerr=[lower, upper],
                                marker="o",
                                capsize=4,
                                label=f"d={study_distance}",
                            )
                        ax.set_xlabel("Physical error probability p")
                        ax.set_ylabel("Logical error rate")
                        ax.set_title("Circuit-level rotated surface-code memory study")
                        if all(
                            float(point["physical_error_rate"]) > 0.0
                            for point in study["points"]
                        ):
                            ax.set_xscale("log")
                        ax.set_ylim(bottom=0.0)
                        ax.grid(True, alpha=0.25)
                        ax.legend(title="Code distance")
                        fig.tight_layout()
                        st.pyplot(fig)
                        plt.close(fig)
                    except Exception as exc:
                        st.error(f"Circuit study failed: {type(exc).__name__}: {exc}")

            study = st.session_state.get("aegis_circuit_study")
            if study:
                st.info(study["interpretation"])
                json_bytes = (
                    json.dumps(study, indent=2, sort_keys=True) + "\n"
                ).encode("utf-8")

                csv_buffer = io.StringIO()
                fieldnames = [
                    "distance",
                    "rounds",
                    "basis",
                    "physical_error_rate",
                    "shots",
                    "logical_failures",
                    "logical_error_rate",
                    "ci95_low",
                    "ci95_high",
                    "detectors",
                    "observables",
                    "detection_events",
                    "circuit_sha256",
                    "dem_sha256",
                    "seed",
                    "sample_seconds",
                    "decode_seconds",
                    "decode_shots_per_second",
                ]
                writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
                writer.writeheader()
                for point in study["points"]:
                    writer.writerow({name: point.get(name) for name in fieldnames})

                download_col1, download_col2 = st.columns(2)
                with download_col1:
                    st.download_button(
                        "Download reproducibility JSON",
                        data=json_bytes,
                        file_name="aegis_surface_code_study.json",
                        mime="application/json",
                    )
                with download_col2:
                    st.download_button(
                        "Download result CSV",
                        data=csv_buffer.getvalue().encode("utf-8"),
                        file_name="aegis_surface_code_study.csv",
                        mime="text/csv",
                    )

    with explain_tab:
        st.write(
            "Inspect one real circuit-level shot: fired detectors, MWPM pairings, "
            "observable prediction, and logical outcome."
        )
        if _version("stim") == "not installed":
            st.warning(
                "Shot explanation requires the full scientific extra: "
                "python -m pip install -U 'aegis-qec[full]'."
            )
        else:
            explain_col1, explain_col2, explain_col3 = st.columns(3)
            with explain_col1:
                explain_distance = st.selectbox(
                    "Explain distance",
                    [3, 5, 7, 9, 11],
                    index=1,
                )
                explain_basis = st.selectbox(
                    "Explain memory basis",
                    ["x", "z"],
                )
            with explain_col2:
                explain_p = st.number_input(
                    "Explain physical error probability",
                    min_value=0.0,
                    max_value=0.49,
                    value=0.01,
                    step=0.001,
                    format="%.4f",
                )
                explain_rounds = st.number_input(
                    "Explain rounds",
                    min_value=1,
                    value=int(explain_distance),
                    step=1,
                )
            with explain_col3:
                explain_seed = st.number_input(
                    "Explain seed",
                    min_value=0,
                    value=1234,
                    step=1,
                )

            if st.button("Explain one shot", type="primary"):
                try:
                    import matplotlib.pyplot as plt

                    from aegis_qec.explain import (
                        explain_surface_code_shot,
                        shot_explanation_figure,
                    )

                    explanation = explain_surface_code_shot(
                        distance=int(explain_distance),
                        physical_error_rate=float(explain_p),
                        basis=explain_basis,
                        rounds=int(explain_rounds),
                        seed=int(explain_seed),
                    )
                    st.session_state["aegis_shot_explanation"] = explanation

                    metric1, metric2, metric3 = st.columns(3)
                    metric1.metric(
                        "Fired detectors",
                        explanation["fired_detector_count"],
                    )
                    metric2.metric(
                        "MWPM pairs",
                        len(explanation["matched_detection_events"]),
                    )
                    metric3.metric(
                        "Outcome",
                        (
                            "Logical failure"
                            if explanation["logical_failure"]
                            else "Logical success"
                        ),
                    )

                    fig = shot_explanation_figure(explanation)
                    st.pyplot(fig)
                    plt.close(fig)

                    st.subheader("Fired detectors")
                    st.dataframe(
                        explanation["fired_detectors"],
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.subheader("Matched detection events")
                    st.dataframe(
                        explanation["matched_detection_events"],
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.write(
                        "Actual observables:",
                        explanation["actual_observables"],
                    )
                    st.write(
                        "Predicted observables:",
                        explanation["predicted_observables"],
                    )
                except Exception as exc:
                    st.error(
                        f"Shot explanation failed: {type(exc).__name__}: {exc}"
                    )

            explanation = st.session_state.get("aegis_shot_explanation")
            if explanation:
                st.info(explanation["interpretation"])
                st.download_button(
                    "Download shot explanation JSON",
                    data=(
                        json.dumps(explanation, indent=2, sort_keys=True) + "\n"
                    ).encode("utf-8"),
                    file_name="aegis_shot_explanation.json",
                    mime="application/json",
                )

    st.divider()
    st.caption(
        "Aegis QEC distinguishes validated production paths from experimental research paths. "
        "Always report the decoder, workload, code distance, rounds, and dependency versions "
        "with benchmark results."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
