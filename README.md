# Aegis QEC

[![PyPI](https://img.shields.io/pypi/v/aegis-qec.svg)](https://pypi.org/project/aegis-qec/)
![Python](https://img.shields.io/pypi/pyversions/aegis-qec.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/hamidbahri92/Aegis/blob/main/LICENSE)
![CI](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml/badge.svg)

**Aegis QEC is a hardware-aware quantum error-correction research toolkit built around PyMatching sparse-blossom minimum-weight perfect matching.** It adds surface-code graph construction, calibrated weights, erasure and leakage information, correlation-aware experiments, Stim detector-error-model interoperability, benchmarking tools, and an optional interactive workbench.

The PyPI distribution is `aegis-qec`. The stable public Python namespace is `aegis_qec`. The historical `a3d` namespace remains available for compatibility.

## Install

Aegis QEC 1.1 requires Python 3.10 or newer. Continuous integration validates the supported release surfaces on Linux and Windows with Python 3.10, 3.11, and 3.12.

```bash
python -m pip install -U aegis-qec
```

For Stim interoperability and the broader research stack:

```bash
python -m pip install -U "aegis-qec[full]"
```

For the interactive application:

```bash
python -m pip install -U "aegis-qec[gui]"
```

## First minute

Aegis has one primary command:

```bash
aegis
```

Start by checking the installation:

```bash
aegis doctor
```

The doctor reports the installed Aegis version, Python version, PyMatching version, active MWPM backend, optional Stim and Streamlit availability, and the result of a small known-answer sparse-blossom decode.

Run a deterministic example:

```bash
aegis demo
```

Measure end-to-end decoder latency:

```bash
aegis benchmark --decoder mwpm --distance 5 --rounds 6 --steps 200
```

Launch the interactive workbench:

```bash
aegis gui
```

The older commands remain available for compatibility and advanced workflows: `aegis-run`, `aegis-metrics`, `aegis-threshold`, `aegis-export-header`, `aegis-bench`, `aegis-gui`, and `aegis-ci`. The historical `aegis-threshold` command is a structural stress sweep, not a physical QEC threshold estimator.

## Python API

```python
from aegis_qec import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

cfg = AegisConfig(distance=5, rounds=6)
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

`AegisConfig()` defaults to the `mwpm` decoder. In Aegis QEC 1.1, that production MWPM path is PyMatching 2.4+ sparse blossom. Experimental OSD polishing, correlation-aware variants, union-find decoding, belief-propagation reweighting, and Transformer reweighting are opt-in.

## Sparse blossom

Aegis translates its decoding graph into a PyMatching graph, maps explicit Aegis boundary edges to PyMatching virtual boundaries, and assigns each Aegis edge a PyMatching fault identifier. The returned correction vector can therefore be mapped back to concrete Aegis correction edges.

The production backend identifies itself as:

```text
pymatching-sparse-blossom
```

Aegis does not silently replace sparse blossom with the historical NetworkX MWPM implementation.

## Performance evidence

Aegis keeps upstream algorithm benchmarks, Aegis end-to-end latency, structural stress tests, controlled calibration experiments, and circuit-level logical-error measurements separate. See the [benchmarking documentation](https://github.com/hamidbahri92/Aegis/blob/main/docs/BENCHMARKING.md) for definitions, provenance, and the relevant PyMatching references.

A controlled graph-level experiment is available with `aegis-bench calibration-advantage`. It compares a uniform-weight baseline with correctly calibrated non-uniform weights on identical sampled physical error chains and evaluates the homology of physical-error XOR correction. It demonstrates the value of informative weights in that controlled model; it is not evidence that real IBM calibration data are already mapped into production surface-code weights.

## Interactive workbench

The Streamlit application is designed around experiments rather than internal class names. It shows the active environment and backend, labels the recommended sparse-blossom path separately from experimental decoders, and provides three guided activities:

- a deterministic synthetic decode with timing and correction summaries;
- an end-to-end latency experiment with p50, p95, and p99 measurements;
- a correction-validation sweep for synthetic detection-event inputs.

The structural sweep is deliberately **not** presented as a circuit-level logical-error-rate measurement. It checks syndrome annihilation and the topology of the proposed correction chain without access to the sampled physical error chain.

For a real circuit-level acceptance check of the DEM bridge, install the full extra and run:

```bash
aegis-bench circuit-acceptance --distance 3 --rounds 3 --shots 1000 --p 0.01
```

This generates a noisy Stim surface-code circuit, samples detector events and logical observables, and requires Aegis DEM predictions to match raw PyMatching exactly on the same shots.

## Stim and detector error models

A Stim detector error model describes error mechanisms, detector connectivity, and observables. It does not contain the observed detection events for a particular shot. Aegis therefore requires explicit observed detector bits when decoding a DEM.

```python
from a3d.decoder_mwpm_pm import PyMatchingMWPMDecoder

decoder = PyMatchingMWPMDecoder()
prediction = decoder.decode_from_dem(
    "error(0.01) D0 D1\n",
    syndrome=[1, 1],
)
```

## Development

```bash
git clone https://github.com/hamidbahri92/Aegis.git
cd Aegis
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,gui]"
aegis-ci
```

On Windows PowerShell, activate the environment with `.\.venv\Scripts\Activate.ps1`.

Hosted CI and `aegis-ci` both enforce a repository-wide real-defect Ruff gate, stricter linting on the Aegis QEC release surfaces, the test suite, and package build validation. Hosted CI additionally builds the distribution, checks its long description with Twine, installs the built wheel, and exercises the user-facing commands.

## Release identity

Use **Aegis QEC** as the product name in prose. Use `aegis-qec` for the PyPI distribution and `aegis_qec` for the public Python import. `a3d` is a compatibility namespace.

Version 1.1.0 is the release that establishes this identity, makes sparse-blossom MWPM the true default path, and introduces the unified `aegis` command.

See [the changelog](https://github.com/hamidbahri92/Aegis/blob/main/CHANGELOG.md) for release notes.

## Citation

If Aegis QEC contributes to published work, cite Aegis and the underlying decoder implementation used by the experiment. Sparse-blossom algorithm and performance claims should credit Higgott and Gidney. Machine-readable citation metadata is provided in [CITATION.cff](https://github.com/hamidbahri92/Aegis/blob/main/CITATION.cff).

## License

MIT. See [LICENSE](https://github.com/hamidbahri92/Aegis/blob/main/LICENSE).
