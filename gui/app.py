# FILE: gui/app.py
try:
    import streamlit as st
    STREAMLIT_OK = True
except Exception:
    STREAMLIT_OK = False

def main():
    if not STREAMLIT_OK:
        print("Streamlit not installed. `pip install streamlit` and try `aegis-gui`.")
        return
    st.set_page_config(page_title="Aegis QEC Dashboard", layout="wide")
    st.title("Aegis — Quantum Error Correction Dashboard")
    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
    col1, col2, col3 = st.columns(3)
    with col1:
        dec = st.selectbox("Decoder", ["mwpm","mwpm2","mwpm_corr","uf"])
        rw  = st.selectbox("Reweighter", ["none","bp","transformer","transformer_sota"])
    with col2:
        dist = st.slider("Distance", 3, 11, 5, 2)
        rnds = st.slider("Rounds", 2, 12, 6, 1)
    with col3:
        p = st.slider("Synthetic p", 0.0, 0.2, 0.05, 0.005)
        run = st.button("Run demo decode")
    cfg = AegisConfig(distance=dist, rounds=rnds, decoder_type=dec)
    cfg.reweighter_type = rw
    layout = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, layout)
    import random
    if run:
        nX = len(rt.builder.node_order("X")); nZ = len(rt.builder.node_order("Z"))
        random.seed(123)
        sX = [1 if random.random()<p else 0 for _ in range(nX)]
        sZ = [1 if random.random()<p else 0 for _ in range(nZ)]
        resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
        st.success(f"X avg_cost={resX.avg_cost:.4f} (conf={getattr(resX,'confidence',0):.2f}), "
                   f"Z avg_cost={resZ.avg_cost:.4f} (conf={getattr(resZ,'confidence',0):.2f})")
    st.markdown("---")
    st.subheader("Quick sweep")
    ps = st.multiselect("p values", [0.01,0.02,0.04,0.06,0.08], default=[0.02,0.06])
    if st.button("Run sweep"):
        from bench.generate_plots import run_sweep
        data = run_sweep(dec, ps, distance=dist, rounds=rnds, trials=50)
        st.write({"decoder": dec, "data": data})
        try:
            import matplotlib.pyplot as plt
            xs = [x for x,_ in data]; ys = [y for _,y in data]
            fig = plt.figure()
            plt.plot(xs, ys, marker="o")
            plt.xlabel("p"); plt.ylabel("logical error rate"); plt.title(dec)
            st.pyplot(fig)
        except Exception:
            st.info("matplotlib not available; showing data only.")

if __name__ == "__main__":
    main()


    st.markdown("---")
    st.subheader("Realtime sample (latency SLO)")
    trials = st.slider("Trials", 10, 500, 50, 10)
    if st.button("Run realtime sample"):
        import time
        nX = len(rt.builder.node_order("X"))
        nZ = len(rt.builder.node_order("Z"))
        lat = []
        import random
        random.seed(1)
        for _ in range(trials):
            sX = [random.randint(0,1) for _ in range(nX)]
            sZ = [random.randint(0,1) for _ in range(nZ)]
            t0 = time.perf_counter()
            _ = rt.decode_from_syndromes_uniform(sX, sZ)
            t1 = time.perf_counter()
            lat.append(t1 - t0)
        lat.sort()
        if lat:
            p50 = lat[int(0.50*len(lat))-1]
            p95 = lat[int(0.95*len(lat))-1]
            p99 = lat[int(0.99*len(lat))-1] if len(lat)>1 else lat[-1]
            st.info(f"p50={p50*1e3:.2f} ms | p95={p95*1e3:.2f} ms | p99={p99*1e3:.2f} ms (n={len(lat)})")


    st.subheader("Latest realtime latency CSV")
    import os
    if os.path.exists("bench_out/realtime_latency.csv"):
        import pandas as pd
        st.dataframe(pd.read_csv("bench_out/realtime_latency.csv"))
    else:
        st.caption("Run the realtime sample or CLI to populate latency CSV.")
