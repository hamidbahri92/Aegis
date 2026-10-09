"""Public, bounded browser demo. Safe to serve on shared free-tier CPU hosting.

The full local research workbench remains available with `aegis gui`.
This public entry point deliberately has no user-supplied paths, uploads,
shell commands, or unrestricted experiments.
"""

from __future__ import annotations

import json

import streamlit as st

from aegis_qec.public_demo import (
    ALLOWED_BASIS,
    ALLOWED_DISTANCES,
    ALLOWED_PROBABILITIES,
    ALLOWED_SEEDS,
    ALLOWED_SHOTS,
    explain_demo_shot,
    run_demo_study,
)

st.set_page_config(
    page_title="Try Aegis QEC | Quantum Error Correction",
    page_icon="🛡️",
    layout="centered",
)

st.title("Aegis QEC: Try Quantum Error Correction")
st.write(
    "Explore how a small simulated quantum surface code produces detector events, "
    "how minimum-weight perfect matching (MWPM) processes them, and what a "
    "reproducible circuit-level experiment records. No local installation needed."
)
st.caption(
    "Real Stim circuit simulation and PyMatching sparse-blossom decoding, "
    "using Aegis QEC's existing Python functions. These are simulated results, "
    "not quantum hardware measurements."
)


@st.cache_data(ttl=1800, max_entries=24, show_spinner=False)
def _explain_cached(distance: int, basis: str, probability: float, seed: int) -> dict:
    return explain_demo_shot(
        distance=distance, basis=basis, probability=probability, seed=seed
    )


@st.cache_data(ttl=1800, max_entries=8, show_spinner=False)
def _study_cached(basis: str, shots: int) -> dict:
    return run_demo_study(basis=basis, shots=shots)


def _download_record(label: str, filename: str, record: dict, key: str) -> None:
    st.download_button(
        label,
        data=json.dumps(record, indent=2, sort_keys=True),
        file_name=filename,
        mime="application/json",
        key=key,
    )


tab_shot, tab_study, tab_learn = st.tabs(
    ["Explain one shot", "Small reproducible study", "Learn and contribute"]
)

with tab_shot:
    st.subheader("What did the decoder actually do?")
    st.write(
        "Choose a tiny experiment, then inspect which detector events fired, "
        "which events MWPM matched, and whether its logical prediction agreed "
        "with the one simulated shot."
    )
    with st.form("single-shot-demo"):
        distance = st.selectbox(
            "Code distance (larger means more checks)",
            ALLOWED_DISTANCES,
            index=1,
        )
        basis = st.selectbox("Memory basis", ALLOWED_BASIS)
        probability = st.selectbox(
            "Physical error probability",
            ALLOWED_PROBABILITIES,
            index=1,
        )
        seed = st.selectbox("Reproducible random seed", ALLOWED_SEEDS)
        run_shot = st.form_submit_button("Decode a simulated shot", type="primary")

    if run_shot:
        try:
            with st.spinner("Generating and decoding one small circuit shot..."):
                st.session_state["public_demo_shot"] = _explain_cached(
                    distance, basis, probability, seed
                )
        except (ImportError, RuntimeError, ValueError) as exc:
            st.error(f"Unable to complete the demonstration: {exc}")

    if "public_demo_shot" in st.session_state:
        record = st.session_state["public_demo_shot"]
        success = not record["logical_failure"]
        st.write(
            f"Observed {record['fired_detector_count']} fired detector events. "
            f"The predicted and simulated logical observables "
            f"{'agreed' if success else 'disagreed'} in this shot."
        )

        from aegis_qec.explain import shot_explanation_figure

        fig = shot_explanation_figure(record)
        st.pyplot(fig)
        import matplotlib.pyplot as plt

        plt.close(fig)

        st.caption(
            "The diagram plots detector coordinates and matching choices. "
            "Boundary matches are identified separately; an empty plot means "
            "this sampled shot had no fired detectors."
        )
        st.write("Detector events:")
        st.dataframe(record["fired_detectors"], hide_index=True)
        st.write("Matched detection events:")
        st.dataframe(record["matched_detection_events"], hide_index=True)
        st.write(record["interpretation"])
        _download_record(
            "Download complete one-shot evidence (JSON)",
            "aegis-qec-one-shot.json",
            record,
            "shot-download",
        )

with tab_study:
    st.subheader("Reproduce a small surface-code experiment")
    st.write(
        "The example compares code distances 3 and 5 at two predefined "
        "physical error probabilities. Sampling limits are deliberately "
        "small to protect free shared compute."
    )
    with st.form("study-demo"):
        study_basis = st.selectbox("Memory basis", ALLOWED_BASIS, key="study-basis")
        shots = st.selectbox(
            "Simulated shots per study point",
            ALLOWED_SHOTS,
            index=1,
        )
        run_study = st.form_submit_button("Run the small study", type="primary")

    if run_study:
        try:
            with st.spinner("Running four bounded circuit study points..."):
                st.session_state["public_demo_study"] = _study_cached(
                    study_basis, shots
                )
        except (ImportError, RuntimeError, ValueError) as exc:
            st.error(f"Unable to complete the study: {exc}")

    if "public_demo_study" in st.session_state:
        study = st.session_state["public_demo_study"]
        rows = [
            {
                "Code distance": point["distance"],
                "Physical error p": point["physical_error_rate"],
                "Shots": point["shots"],
                "Logical failures": point["logical_failures"],
                "Observed failure fraction": point["logical_error_rate"],
                "95% CI lower": point["ci95_low"],
                "95% CI upper": point["ci95_high"],
            }
            for point in study["points"]
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        st.warning(
            "This is a teaching demonstration, NOT a physical threshold estimate "
            "or a statistically conclusive decoder comparison. Small samples can "
            "have wide confidence intervals."
        )
        st.write(study["interpretation"])
        st.caption(
            "The downloadable record includes simulated circuit/DEM hashes, "
            "software versions, seeds, model parameters, and the exact results."
        )
        _download_record(
            "Download reproducibility record (JSON)",
            "aegis-qec-small-study.json",
            study,
            "study-download",
        )

with tab_learn:
    st.subheader("Keep learning and challenge the results")
    st.markdown(
        """
        Aegis QEC is an open-source research and learning toolkit built around
        [Stim](https://github.com/quantumlib/Stim) for stabilizer simulation and
        [PyMatching](https://github.com/oscarhiggott/PyMatching) for
        sparse-blossom MWPM. It is **not** a universal QEC simulator or a
        substitute for independent scientific validation.

        - [Start Here: learn, test, and contribute](https://github.com/hamidbahri92/Aegis-QEC/blob/main/docs/START_HERE.md)
        - [Research guide and interpretation limits](https://github.com/hamidbahri92/Aegis-QEC/blob/main/docs/RESEARCH_GUIDE.md)
        - [Join the public research discussion](https://github.com/hamidbahri92/Aegis-QEC/discussions/53)
        - [Report a reproducible result or bug](https://github.com/hamidbahri92/Aegis-QEC/issues)
        - [Explore the complete source and local workbench](https://github.com/hamidbahri92/Aegis-QEC)
        """
    )
    st.write(
        "We welcome independent replication, scientific criticism, learning "
        "feedback, accessibility improvements, and focused contributions."
    )

st.divider()
st.caption(
    "This shared demo does not accept uploaded files, arbitrary commands, "
    "or unrestricted simulation workloads. Run the full Aegis QEC toolkit "
    "locally for larger research experiments."
)
