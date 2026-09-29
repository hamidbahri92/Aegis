# Aegis QEC

[![PyPI](https://img.shields.io/pypi/v/aegis-qec.svg)](https://pypi.org/project/aegis-qec/)
![Python](https://img.shields.io/pypi/pyversions/aegis-qec.svg)
[![CI](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/hamidbahri92/Aegis/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/hamidbahri92/Aegis?style=social)](https://github.com/hamidbahri92/Aegis/stargazers)

**Aegis QEC is a Python toolkit for surface-code decoding experiments built around PyMatching's sparse-blossom MWPM engine.** It gives you a practical layer for building decoding graphs, supplying calibrated or erasure-aware costs, decoding Stim detector error models, validating correction plumbing, and running reproducible benchmarks without hiding which parts are validated and which parts are experimental.

The PyPI package is `aegis-qec`. The public Python namespace is `aegis_qec`. The older `a3d` namespace remains available for compatibility.

## Start in sixty seconds

Aegis QEC requires Python 3.10 or newer.

```bash
python -m pip install -U aegis-qec
aegis doctor
aegis demo
```

`aegis doctor` reports the installed versions, platform, active MWPM backend, optional dependencies, and the result of a known-answer sparse-blossom self-test.

For Stim detector-error-model workflows:

```bash
python -m pip install -U "aegis-qec[full]"
aegis-bench circuit-acceptance --distance 3 --rounds 3 --shots 1000 --p 0.01
```

For the optional Streamlit workbench:

```bash
python -m pip install -U "aegis-qec[gui]"
aegis gui
```

## The default path

`AegisConfig()` defaults to `decoder_type="mwpm"`. That path compiles the Aegis decoding graph into PyMatching, represents Aegis boundary edges as PyMatching virtual-boundary edges, assigns fault identifiers to graph edges, and maps the returned correction vector back to concrete Aegis `Edge` objects.

The backend identifies itself as:

```text
pymatching-sparse-blossom
```

There is no NetworkX fallback in the default MWPM path.

```python
from aegis_qec import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

cfg = AegisConfig(distance=5, rounds=6)
runtime = DecoderRuntime(cfg, RotatedSurfaceLayout(cfg.distance))

n_x = len(runtime.builder.node_order("X"))
n_z = len(runtime.builder.node_order("Z"))

result_x, result_z = runtime.decode_from_syndromes_uniform(
    [0] * n_x,
    [0] * n_z,
)

print(result_x.corrections)
print(result_z.corrections)
```

## Detector error models without ambiguous inputs

A Stim detector error model describes possible error mechanisms. It does not contain the observed detection events for a particular shot. Aegis keeps those two things separate.

```python
from a3d.decoder_mwpm_pm import PyMatchingMWPMDecoder

decoder = PyMatchingMWPMDecoder()
prediction = decoder.decode_from_dem(
    "error(0.01) D0 D1\n",
    syndrome=[1, 1],
)
```

Calling `decode_from_dem` without explicit detector bits raises an error. Batch decoding is also available through `decode_dem_batch`.

The historical text-to-`DecodingGraph` helper in `a3d.stim_adapter` is a lossy compatibility projection for a narrow DEM subset. For faithful DEM decoding, use `PyMatchingMWPMDecoder`, which delegates the detector error model to Stim and PyMatching.

## What you can measure

Aegis deliberately separates four kinds of evidence.

**End-to-end latency.** `aegis benchmark` and `aegis-bench realtime` measure the Aegis path, including Python orchestration around the decoder.

```bash
aegis benchmark --decoder mwpm --distance 5 --rounds 6 --steps 1000
```

**Circuit-level DEM acceptance.** `aegis-bench circuit-acceptance` samples a noisy Stim surface-code circuit and requires the Aegis DEM bridge to reproduce raw PyMatching predictions shot for shot.

**Controlled calibration advantage.** `aegis-bench calibration-advantage` compares uniform and correctly calibrated graph weights on identical sampled physical error chains, with exact residual-chain logical ground truth for the controlled model.

```bash
aegis-bench calibration-advantage \
  --shots 10000 \
  --seed 20260928 \
  --out-json bench_out/calibration.json \
  --plot bench_out/calibration.png
```

**Structural stress tests.** `aegis-bench sweep` checks correction-chain behavior on synthetic detector-bit patterns. It is useful for software validation, but it is not a circuit-level logical-error-rate or threshold measurement.

See [Benchmarking](https://github.com/hamidbahri92/Aegis/blob/main/docs/BENCHMARKING.md) for the exact interpretation of each result.

## About sparse-blossom performance claims

Aegis QEC uses PyMatching's sparse-blossom implementation. The published sparse-blossom work by Oscar Higgott and Craig Gidney reports very large speedups over older matching approaches, including a greater-than-one-hundred-thousand-times comparison with a NetworkX implementation at large code distance in the paper's benchmark.

That is an upstream PyMatching result, not a blanket Aegis end-to-end speed claim. If you publish Aegis timings, report the workload, Aegis version, PyMatching version, Python version, operating system, CPU, code distance, rounds, sample count, weight policy, and whether the number is decoder-only or end-to-end.

Reference: Oscar Higgott and Craig Gidney, *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025), DOI 10.22331/q-2025-01-20-1600.

## Validated core and experimental research paths

The default `mwpm` path is the best-tested Aegis decoder path. Tests cover sparse-blossom backend identity, virtual-boundary translation, correction-edge reconstruction, batch reuse, direct comparison with PyMatching's decoded-edge oracle, explicit DEM detector inputs, and circuit-level DEM parity.

Aegis also contains research paths for pipelined or correlation-adjusted MWPM, union-find with erasure handling, belief-propagation reweighting, Transformer-based reweighting, OSD polishing, leakage information, correlation models, and hardware-facing calibration acquisition. These are useful experimental surfaces, but they do not all have the same validation status as the default MWPM and DEM paths.

Read [Algorithms](https://github.com/hamidbahri92/Aegis/blob/main/docs/ALGORITHMS.md) for the implementation model and [Overview](https://github.com/hamidbahri92/Aegis/blob/main/docs/OVERVIEW.md) for the package architecture.

## Commands

The primary command is `aegis`.

```text
aegis doctor
aegis demo
aegis benchmark
aegis gui
```

Specialized compatibility and research entry points are also installed: `aegis-run`, `aegis-metrics`, `aegis-threshold`, `aegis-export-header`, `aegis-bench`, `aegis-gui`, and `aegis-ci`.

The historical `aegis-threshold` command is retained for compatibility. Its structural sweep is not a physical QEC threshold estimator.

## Develop locally

```bash
git clone https://github.com/hamidbahri92/Aegis.git
cd Aegis
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,gui]"
aegis-ci
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

Hosted CI tests Ubuntu and Windows across Python 3.10, 3.11, and 3.12. It runs repository defect lint, stricter lint on release-critical surfaces, pytest, backend and CLI checks, package builds, Twine metadata validation, wheel installation, circuit acceptance, and the controlled calibration benchmark.

See [Contributing](https://github.com/hamidbahri92/Aegis/blob/main/CONTRIBUTING.md) before opening a pull request.

## Cite, star, or contribute

If Aegis QEC helps your research, please cite the software and the underlying decoder paper used by your experiment. Machine-readable metadata lives in [CITATION.cff](https://github.com/hamidbahri92/Aegis/blob/main/CITATION.cff).

If it saves you time, a GitHub star is a simple way to make the project easier for other quantum-error-correction researchers to discover. If you find a reproducible bug, open an issue. If you can improve a decoder, benchmark, test, or explanation, contributions are welcome.

## License

MIT. See [LICENSE](https://github.com/hamidbahri92/Aegis/blob/main/LICENSE).
