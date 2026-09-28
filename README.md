# Aegis QEC

[![PyPI](https://img.shields.io/pypi/v/aegis-qec.svg)](https://pypi.org/project/aegis-qec/)
![Python](https://img.shields.io/pypi/pyversions/aegis-qec.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![CI](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml/badge.svg)

**Aegis QEC is a Python research toolkit for hardware-aware quantum error-correction experiments, with exact sparse-blossom minimum-weight perfect matching, surface-code graph construction, soft information, erasure/leakage models, correlation reweighting, and Stim/DEM interoperability.**

The package on PyPI is `aegis-qec`. The public Python namespace is `aegis_qec`. The historical `a3d` namespace remains available for compatibility.

## Why Aegis QEC

Aegis QEC is for researchers, students, and quantum-control engineers who want to experiment with realistic decoder inputs without rebuilding the plumbing around graph construction, error weighting, leakage, correlations, metrics, and benchmarking.

It is not trying to replace PyMatching or Stim. Aegis uses them where they are strongest and adds the hardware-aware experimentation layer around them.

## Fast MWPM by default

`decoder_type="mwpm"` now uses **PyMatching v2+ sparse blossom directly**. The old NetworkX MWPM implementation is no longer the production backend.

The sparse-blossom algorithm by Oscar Higgott and Craig Gidney avoids the all-pairs shortest-path construction used by many older MWPM implementations. PyMatching reports more than a **100,000x speedup over NetworkX** on its published surface-code benchmark. That number is the PyMatching benchmark result, not a promise that every Aegis workload is exactly 100,000x faster; Aegis includes graph construction and optional post-processing that also contribute to end-to-end latency.

Paper: Higgott and Gidney, *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025), https://doi.org/10.22331/q-2025-01-20-1600

## Install

```bash
pip install -U aegis-qec
```

For the full research stack including Stim interoperability:

```bash
pip install -U "aegis-qec[full]"
```

## Five-minute start

```python
from aegis_qec import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

cfg = AegisConfig(distance=5, rounds=6, decoder_type="mwpm")
layout = RotatedSurfaceLayout(cfg.distance)
runtime = DecoderRuntime(cfg, layout)

n_x = len(runtime.builder.node_order("X"))
n_z = len(runtime.builder.node_order("Z"))

result_x, result_z = runtime.decode_from_syndromes_uniform(
    [0] * n_x,
    [0] * n_z,
)

print(result_x.avg_cost, result_z.avg_cost)
```

The compatibility import still works:

```python
import a3d
```

## Decoder stack

Aegis currently includes sparse-blossom MWPM, pipelined MWPM, correlation-aware MWPM, union-find with erasures, greedy matching with OSD fallback, BP reweighting, optional Transformer reweighting, soft-information inputs, leakage-aware weighting, confidence scoring, profiling, and detector-error-model utilities.

The ordinary `mwpm`, `mwpm2`, and correlation-aware MWPM paths share the same sparse-blossom backend. `MWPMDecoder.decode_batch(...)` reuses one compiled PyMatching graph for many syndrome shots.

## Command-line tools

The existing command-line entry points remain available:

```bash
aegis-run
aegis-metrics
aegis-threshold
aegis-export-header
aegis-ci
```

For repository benchmarks, run `python -m bench.cli ...` from a source checkout. The Streamlit dashboard is launched from a checkout with `python -m scripts.run_gui` after installing the GUI dependencies.

## Correctness and performance policy

Performance claims must be benchmarked against a named workload and backend. Aegis does not silently substitute NetworkX for sparse blossom. The MWPM backend identifies itself as `pymatching-sparse-blossom`, and tests cover detector-to-detector paths, virtual boundaries, batch decoding, and the public package namespace.

A detector error model describes an error model, not an observed syndrome. DEM interoperability should therefore always be tested with explicit detection-event data rather than treating a DEM file by itself as a decode request.

## Development

```bash
git clone https://github.com/hamidbahri92/Aegis.git
cd Aegis
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
ruff check .
```

## Project identity

Use **Aegis QEC** in prose, documentation, screenshots, and announcements. Use `aegis-qec` for the PyPI distribution and `aegis_qec` for Python imports. `a3d` is a compatibility namespace rather than the public product name.

For discoverability, the GitHub repository itself should ultimately be renamed from `Aegis` to `aegis-qec` or `Aegis-QEC`.

## Who this is for

The primary audience is QEC researchers and graduate students who need reproducible decoding experiments with realistic weights and fast exact MWPM. A second audience is quantum-hardware and control engineers exploring decoder latency, leakage, soft information, and hardware-aware interfaces. A third audience is educators who want a readable Python stack that can expose the pieces around a production-grade matching backend.

The strongest public story is therefore not “another quantum SDK.” It is: **fast, exact QEC decoding plus an experimental workbench for the messy hardware information that real decoders have to consume.**

## Citation

If Aegis QEC contributes to published work, please cite the project and the underlying decoder implementations that your experiment uses. In particular, sparse-blossom performance comes from PyMatching and should be credited to Higgott and Gidney.

## License

MIT. See [LICENSE](LICENSE).
