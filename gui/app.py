from __future__ import annotations

import csv
import importlib.metadata as metadata
import io
import json
import random
import time

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


def _research_workbench():
    """Operate research-project and discovery workflows from the local GUI."""

    from pathlib import Path

    st.header("Research lifecycle")
    st.caption(
        "From a question to frozen protocols, tracked evidence, exploratory "
        "discovery, and reviewer-ready manuscript sources."
    )
    project_tab, discovery_tab, submission_tab = st.tabs(
        ["Projects and evidence", "Adaptive discovery", "Submission packages"]
    )

    with project_tab:
        st.subheader("Start a research project")
        with st.form("aegis-project-create"):
            new_project = st.text_input(
                "New project file", value="research-project.json"
            )
            author = st.text_input("Author name", value="Researcher")
            overwrite_project = st.checkbox(
                "Replace existing starter files", value=False
            )
            create_project = st.form_submit_button("Create starter project")
        if create_project:
            try:
                from aegis_qec.project import write_research_project_template

                created = write_research_project_template(
                    new_project,
                    author_name=author,
                    overwrite=overwrite_project,
                )
                st.success("Research project and runnable experiment created.")
                st.json(created)
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(f"Creation failed: {type(exc).__name__}: {exc}")

        st.subheader("Run or review an existing project")
        project_file = st.text_input(
            "Project manifest path", value="research-project.json",
            key="aegis-project-path",
        )
        project_workspace = st.text_input(
            "Experiment workspace", value="research_out/project",
        )
        freeze_col, audit_col, run_col, collect_col = st.columns(4)
        with freeze_col:
            freeze_clicked = st.button("Freeze protocol")
        with audit_col:
            audit_clicked = st.button("Audit evidence")
        with run_col:
            run_clicked = st.button("Run experiments")
        with collect_col:
            collect_clicked = st.button("Collect evidence")
        if collect_clicked:
            try:
                from aegis_qec.project import collect_project_evidence

                run_file = str(
                    Path(project_workspace).resolve() / "project-run.json"
                )
                report = collect_project_evidence(project_file, run_file)
                st.success(
                    f"Pinned {len(report['added'])} new evidence artifacts."
                )
                st.json(report)
            except (OSError, RuntimeError, ValueError, KeyError) as exc:
                st.error(
                    f"Evidence collection failed: {type(exc).__name__}: {exc}"
                )
        if freeze_clicked:
            try:
                from aegis_qec.project import freeze_research_protocol

                record = freeze_research_protocol(project_file)
                st.success("Scientific protocol locked.")
                st.json(record)
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(f"Freeze failed: {type(exc).__name__}: {exc}")
        if audit_clicked:
            try:
                from aegis_qec.project import audit_research_project

                report = audit_research_project(project_file)
                if report["valid"]:
                    st.success("Declared claim/evidence audit passed.")
                else:
                    st.error("Declared claim/evidence audit failed.")
                st.json(report)
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(f"Audit failed: {type(exc).__name__}: {exc}")
        if run_clicked:
            try:
                from aegis_qec.project import run_research_project

                with st.spinner("Executing declared experiments"):
                    report = run_research_project(
                        project_file,
                        workspace=project_workspace,
                    )
                st.success("Experiment run record and bundles written.")
                st.json(report)
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(f"Run failed: {type(exc).__name__}: {exc}")

    with discovery_tab:
        st.subheader("Explore a transparent multi-objective search")
        st.info(
            "Discovery is exploratory. Selected Pareto candidates need "
            "fresh-data confirmation before confirmatory claims."
        )
        with st.form("aegis-discovery-create"):
            starter_path = st.text_input(
                "New discovery configuration", value="discovery.json"
            )
            overwrite_discovery = st.checkbox(
                "Replace existing discovery starter", value=False
            )
            create_discovery = st.form_submit_button("Create discovery starter")
        if create_discovery:
            try:
                from aegis_qec.discovery import write_discovery_starter

                created = write_discovery_starter(
                    starter_path,
                    overwrite=overwrite_discovery,
                )
                st.success("Search definition and base experiment created.")
                st.json(created)
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(f"Starter failed: {type(exc).__name__}: {exc}")

        with st.form("aegis-discovery-run"):
            discovery_file = st.text_input(
                "Discovery configuration path", value="discovery.json"
            )
            discovery_workspace = st.text_input(
                "Search workspace", value="research_out/discovery"
            )
            start_discovery = st.form_submit_button("Run or resume discovery")
        if start_discovery:
            try:
                from aegis_qec.discovery import run_discovery

                with st.spinner("Evaluating search candidates"):
                    report = run_discovery(
                        discovery_file,
                        output_dir=discovery_workspace,
                    )
                st.session_state["aegis-discovery-report"] = report
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(f"Discovery failed: {type(exc).__name__}: {exc}")

        if st.button("Load saved discovery summary"):
            path = Path(discovery_workspace) / "discovery.json"
            try:
                st.session_state["aegis-discovery-report"] = json.loads(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError) as exc:
                st.error(f"Could not load discovery record: {exc}")

        report = st.session_state.get("aegis-discovery-report")
        if report:
            measures = st.columns(3)
            measures[0].metric("Evaluated", report.get("evaluated", 0))
            measures[1].metric("Successful", report.get("successful", 0))
            measures[2].metric("Pareto designs", len(report.get("pareto_front", [])))
            front_rows = []
            for item in report.get("pareto_front", []):
                front_rows.append(
                    {
                        "candidate": item["key"],
                        **item["assignment"],
                        **item["objectives"],
                    }
                )
            if front_rows:
                st.dataframe(front_rows, use_container_width=True, hide_index=True)
            st.caption(report.get("interpretation", ""))
            st.download_button(
                "Download discovery summary JSON",
                data=(json.dumps(report, indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
                file_name="discovery.json",
                mime="application/json",
            )
            st.subheader("Independent confirmation manifests")
            for item in report.get("confirmation_manifests", []):
                confirm_path = Path(item["path"])
                if confirm_path.is_file():
                    st.download_button(
                        f"Download candidate {item['rank']} confirmation manifest",
                        data=confirm_path.read_bytes(),
                        file_name=confirm_path.name,
                        mime="application/json",
                        key=f"confirm-{item['rank']}-{item['candidate']}",
                    )

    with submission_tab:
        st.subheader("Build an auditable manuscript and evidence package")
        with st.form("aegis-submission-build"):
            paper_project = st.text_input(
                "Research project manifest", value="research-project.json"
            )
            submission_dir = st.text_input(
                "Submission output directory", value="submission"
            )
            compile_mode = st.selectbox(
                "LaTeX PDF compilation",
                ["auto", "never", "required"],
            )
            anonymous = st.checkbox("Blind-review package", value=False)
            require_lock = st.checkbox(
                "Require frozen protocol", value=True
            )
            allow_invalid = st.checkbox(
                "Allow incomplete draft evidence", value=False
            )
            force = st.checkbox(
                "Overwrite existing submission output", value=False
            )
            build_clicked = st.form_submit_button("Build submission package")

        if build_clicked:
            try:
                from aegis_qec.paper import build_submission_package

                with st.spinner("Generating the manuscript and reviewer package"):
                    package = build_submission_package(
                        paper_project,
                        output_dir=submission_dir,
                        compile_mode=compile_mode,
                        require_protocol_lock=require_lock,
                        allow_invalid=allow_invalid,
                        anonymize=anonymous,
                        overwrite=force,
                    )
                st.session_state["aegis-submission-package"] = package
            except (OSError, RuntimeError, ValueError) as exc:
                st.error(f"Package build failed: {type(exc).__name__}: {exc}")

        package = st.session_state.get("aegis-submission-package")
        if package:
            st.metric(
                "Scientific submission readiness",
                "Ready" if package.get("submission_ready") else "Needs work",
            )
            st.write("Package:", package["zip_path"])
            for issue in package.get("submission_readiness", {}).get(
                "failures", []
            ):
                st.warning(issue["message"])
            zip_path = Path(package["zip_path"])
            if zip_path.is_file():
                if zip_path.stat().st_size <= 64 * 1024 * 1024:
                    st.download_button(
                        "Download reviewer ZIP",
                        data=zip_path.read_bytes(),
                        file_name=zip_path.name,
                        mime="application/zip",
                    )
                else:
                    st.info(
                        "ZIP exceeds the 64 MB in-app download threshold; "
                        "retrieve it from the shown local output path."
                    )
        st.caption(
            "An intact ZIP is not proof of valid scientific conclusions or "
            "acceptance by a journal. The authors remain responsible for review."
        )


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

    decode_tab, latency_tab, sweep_tab, study_tab, explain_tab, research_tab = st.tabs(
        [
            "Decode",
            "Latency",
            "Validation sweep",
            "Circuit study",
            "Explain one shot",
            "Research lifecycle",
        ]
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

    with research_tab:
        _research_workbench()

    st.divider()
    st.caption(
        "Aegis QEC distinguishes validated production paths from experimental research paths. "
        "Always report the decoder, workload, code distance, rounds, and dependency versions "
        "with benchmark results."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
