# FILE: gui/app.py
from __future__ import annotations

import random
import time

try:
    import streamlit as st

    STREAMLIT_OK = True
except Exception:
    STREAMLIT_OK = False


def _percentile(samples, fraction):
    ordered = sorted(samples)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(fraction * len(ordered)) - 1))
    return ordered[index]


def main():
    if not STREAMLIT_OK:
        print("Streamlit is not installed. Run: pip install 'aegis-qec[gui]'")
        return

    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
    from a3d.decoder_mwpm import MWPMDecoder

    st.set_page_config(page_title="Aegis QEC", layout="wide")
    st.title("Aegis QEC")
    st.caption(
        "Hardware-aware quantum error-correction experiments with "
        f"{MWPMDecoder.backend} MWPM."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        decoder = st.selectbox("Decoder", ["mwpm", "mwpm2", "mwpm_corr", "uf"])
        reweighter = st.selectbox(
            "Reweighter", ["none", "bp", "transformer", "transformer_sota"]
        )
    with col2:
        distance = st.slider("Code distance", 3, 11, 5, 2)
        rounds = st.slider("Syndrome rounds", 2, 12, 6, 1)
    with col3:
        error_probability = st.slider(
            "Synthetic error probability", 0.0, 0.2, 0.05, 0.005
        )
        run_decode = st.button("Run demo decode", type="primary")

    cfg = AegisConfig(
        distance=distance,
        rounds=rounds,
        decoder_type=decoder,
        reweighter_type=reweighter,
    )
    runtime = DecoderRuntime(cfg, RotatedSurfaceLayout(cfg.distance))

    if run_decode:
        n_x = len(runtime.builder.node_order("X"))
        n_z = len(runtime.builder.node_order("Z"))
        rng = random.Random(123)
        syndrome_x = [
            int(rng.random() < error_probability) for _ in range(n_x)
        ]
        syndrome_z = [
            int(rng.random() < error_probability) for _ in range(n_z)
        ]

        started = time.perf_counter()
        result_x, result_z = runtime.decode_from_syndromes_uniform(
            syndrome_x, syndrome_z
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        st.success(
            f"Decoded in {elapsed_ms:.3f} ms — "
            f"X cost {result_x.avg_cost:.4f}, "
            f"Z cost {result_z.avg_cost:.4f}"
        )

    st.divider()
    st.subheader("Latency experiment")
    trials = st.slider("Trials", 10, 500, 50, 10)
    if st.button("Measure latency"):
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

        st.metric("p50", f"{_percentile(samples, 0.50) * 1e3:.3f} ms")
        st.metric("p95", f"{_percentile(samples, 0.95) * 1e3:.3f} ms")
        st.metric("p99", f"{_percentile(samples, 0.99) * 1e3:.3f} ms")

    st.divider()
    st.subheader("Quick logical-rate sweep")
    probabilities = st.multiselect(
        "Physical error probabilities",
        [0.01, 0.02, 0.04, 0.06, 0.08],
        default=[0.02, 0.06],
    )
    if st.button("Run sweep"):
        from bench.cli import sweep

        data = sweep(
            decoder,
            probabilities,
            distance=distance,
            rounds=rounds,
            trials=50,
        )
        st.dataframe(
            [{"physical_p": physical_p, "logical_rate": rate} for physical_p, rate in data],
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
