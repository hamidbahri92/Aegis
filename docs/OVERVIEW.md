# Aegis QEC overview

Aegis QEC is a hardware-aware quantum error-correction experimentation layer built around fast, proven decoding kernels.

The default exact MWPM backend is PyMatching v2+ sparse blossom. Aegis adds the surrounding research machinery: surface-code decoding graphs, calibrated negative-log-odds weights, erasure and leakage information, soft inputs, correlation-aware reweighting, confidence and profiling hooks, batch decoding, Stim detector-error-model interoperability, benchmark tooling, and an optional Streamlit dashboard.

## Public interfaces

Install the distribution with `pip install aegis-qec` and import the stable API from `aegis_qec`. Existing code that imports `a3d` remains compatible.

Use `aegis-bench` for sweeps and latency experiments. Install the `gui` extra and run `aegis-gui` for the interactive dashboard.

## Decoder families

`mwpm` is exact sparse-blossom MWPM. `mwpm2` performs a sparse-blossom pass, local correlation reweighting, and a second sparse-blossom pass. `mwpm_corr` applies learned or motif-based correlation adjustments before sparse-blossom MWPM. Aegis also includes union-find with erasures and greedy/OSD experimental paths.

## Stim interoperability

Stim detector error models describe error mechanisms and detector connectivity. They do not contain the observed detection events for a particular shot. Aegis therefore requires explicit syndrome bits when decoding a DEM instead of returning a placeholder empty correction.

See [ALGORITHMS.md](ALGORITHMS.md) for implementation details and the performance-claim scope.
