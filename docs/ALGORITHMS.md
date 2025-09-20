
# Aegis Algorithms (State of the Art)

This document explains the decoding and reweighting stack:
- **LLR/NLL Costs:** all edges use negative log-odds derived from error probabilities, fused with erasures.
- **UF‑E with Peeling:** erasure-first peeling along high-probability time edges, followed by union-find growth.
- **MWPM Variants:**
  - **MWPM (classic):** baseline Blossom-based matching (via NetworkX).
  - **MWPM2 (pipelined):** MWPM → local correlation pass → MWPM.
  - **MWPM‑Corr:** motif-based local correlation potentials applied before MWPM.
- **Reweighting:**
  - **Transformer reweighter:** compact Transformer predicts edge logit adjustments from structural features.
  - **BP reweighter:** loopy belief propagation on the edge adjacency graph (min-sum style) to encourage coherent structures.

All methods fall back gracefully when optional deps are missing.

- **Data-driven Correlations:** `CorrelationParams` JSON loaded into MWPM‑Corr; train via `scripts/train_correlations.py` from decode logs.
