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

    decode_tab, latency_tab, sweep_tab, study_tab = st.tabs(
        ["Decode", "Latency", "Validation sweep", "Circuit study"]
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

    st.divider()
    st.caption(
        "Aegis QEC distinguishes validated production paths from experimental research paths. "
        "Always report the decoder, workload, code distance, rounds, and dependency versions "
        "with benchmark results."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
