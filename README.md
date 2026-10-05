# Aegis QEC — Quantum Error Correction Toolkit for Surface Codes

[![PyPI](https://img.shields.io/pypi/v/aegis-qec.svg)](https://pypi.org/project/aegis-qec/)
![Python](https://img.shields.io/pypi/pyversions/aegis-qec.svg)
[![CI](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml/badge.svg)](https://github.com/hamidbahri92/Aegis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/hamidbahri92/Aegis/blob/main/LICENSE)
**Aegis QEC is an open-source Python toolkit for quantum error correction and surface-code decoding. It connects Stim detector error models to PyMatching sparse-blossom MWPM, adds calibrated and erasure-aware decoding, reproducible benchmarks, explicit validation, and research workflows for fault-tolerant quantum computing.**

Use Aegis when you want to run complete QEC experiments rather than wire together a decoder, noise model, validation layer, benchmark harness, and reporting pipeline yourself. It provides surface-code graph construction, faithful Stim DEM decoding, calibrated edge costs, correction-edge reconstruction, batch execution, controlled decoder comparisons, a Python API, command-line tools, and an optional Streamlit workbench.

The PyPI distribution is **`aegis-qec`**. The public Python namespace is **`aegis_qec`**. The historical **`a3d`** namespace remains importable for compatibility.

## Install Aegis QEC

Install the surface-code QEC toolkit from PyPI and verify the decoder stack immediately:

Aegis QEC requires Python 3.10 or newer.

For the validated core:

```bash
python -m pip install -U aegis-qec
aegis doctor
aegis demo
```

For Stim detector-error-model workflows and the full scientific extras:

```bash
python -m pip install -U "aegis-qec[full]"
```

For the optional Streamlit graphical workbench:

```bash
python -m pip install -U "aegis-qec[gui]"
aegis gui
```

For development:

```bash
python -m pip install -e ".[dev,gui]"
```

`aegis doctor` reports the installed versions, platform, active MWPM backend, optional dependencies, and a known-answer sparse-blossom self-test.

## What Aegis QEC does

Aegis sits between low-level decoder libraries and complete quantum-error-correction experiments. Its job is to make the experiment plumbing explicit, inspectable, reproducible, and testable.

A typical Aegis workflow is:

1. define a rotated surface-code layout and experiment configuration;
2. build X-sector and Z-sector decoding graphs;
3. assign uniform, calibrated, erasure-aware, or experimentally reweighted edge costs;
4. decode detector events with the selected decoder;
5. reconstruct concrete correction edges rather than returning only abstract defect pairings;
6. validate correction behavior or logical observables against an independent oracle;
7. record benchmark configuration, seeds, versions, and artifacts for reproducibility.

The strongest validated path uses PyMatching's sparse-blossom implementation of minimum-weight perfect matching. Aegis also exposes experimental decoders and reweighting methods for research.

## Quick Python example

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

`AegisConfig()` defaults to `decoder_type="mwpm"`. That path compiles the Aegis graph into `pymatching.Matching`, translates Aegis boundary edges into PyMatching virtual-boundary edges, assigns fault identifiers to graph edges, and reconstructs the returned correction vector as concrete Aegis `Edge` objects.

The backend identifies itself as:

```text
pymatching-sparse-blossom
```

There is no NetworkX fallback in the default MWPM path.

## Surface-code graphs and calibrated costs

Aegis graph nodes carry sector, coordinate, time index, and role metadata. Edges represent spatial, temporal, or boundary relationships and carry weights plus optional erasure probabilities.

The runtime can create uniform weights for controlled experiments or derive effective costs from configuration fields such as data-error probability, measurement-error probability, leakage probability, and time-weight scaling.

This makes it possible to test whether informative non-uniform probabilities actually improve decoding on identical sampled errors instead of comparing different workloads.

Aegis also contains experimental cost-adjustment paths including correlation-aware MWPM, belief-propagation reweighting, Transformer-based reweighting, leakage information, and multi-pass decoding. These are research surfaces and should be reported explicitly when used.

## Stim detector error models

A Stim detector error model describes possible error mechanisms. It does **not** contain the observed detector events for a particular shot. Aegis keeps those objects separate.

For faithful DEM decoding, use `PyMatchingMWPMDecoder`:

```python
from a3d.decoder_mwpm_pm import PyMatchingMWPMDecoder

decoder = PyMatchingMWPMDecoder()
prediction = decoder.decode_from_dem(
    "error(0.01) D0 D1\n",
    syndrome=[1, 1],
)
```

Calling `decode_from_dem` without explicit detector bits raises an error. Batch decoding is available through `decode_dem_batch`, allowing one compiled matcher to process many detector shots.

The historical text-to-`DecodingGraph` helper in `a3d.stim_adapter` is a lossy compatibility projection for a narrow DEM subset. It cannot faithfully encode arbitrary Stim hyperedges, repeat structure, logical observables, or all detector-shift semantics. Use the direct Stim/PyMatching bridge when detector-error-model fidelity matters.

## Decoder families

The default `mwpm` decoder is the best-tested Aegis path and is backed by PyMatching sparse blossom.

Aegis also includes research paths for:

- pipelined or two-pass MWPM;
- correlation-adjusted MWPM;
- union find with erasure handling;
- greedy decoding;
- ordered-statistics decoding and optional OSD polishing;
- belief-propagation graph reweighting;
- Transformer-based edge-cost reweighting.

These experimental paths are useful for decoder research, but they do not all have the same validation status as the default sparse-blossom and direct DEM paths.

See [Algorithms](https://github.com/hamidbahri92/Aegis/blob/main/docs/ALGORITHMS.md) for implementation details and trust boundaries.

## Reproducible circuit studies

For student projects, theses, decoder integration work, and research prototypes, Aegis can run a complete Stim circuit-level study and preserve the result as reusable artifacts:

```bash
aegis study \
  --distance 3 5 7 \
  --p 0.003 0.006 0.01 \
  --shots 5000 \
  --basis x \
  --seed 1234
```

The command generates rotated surface-code memory circuits with Stim, samples detector events and logical observables, decodes those exact shots through the Aegis direct DEM bridge, reports logical-error rates with 95 percent Wilson confidence intervals, and writes JSON, CSV, and PNG artifacts. The JSON includes the experiment parameters, per-point seeds, dependency versions, environment details, timings, and the exact noise-model mapping used by the study.

The same workflow is available in the **Circuit study** tab of `aegis gui`, including downloadable reproducibility records.

See the [Research Guide](https://github.com/hamidbahri92/Aegis/blob/main/docs/RESEARCH_GUIDE.md) for student project ideas, practitioner workflows, interpretation boundaries, and the Python API.

## Research platform and large campaigns

For larger Monte Carlo work, Aegis integrates Sinter instead of reimplementing its multiprocessing collector:

```bash
aegis campaign \
  --distance 3 5 7 \
  --p 0.003 0.006 0.01 \
  --decoder pymatching aegis-pymatching \
  --workers auto \
  --max-shots 1000000 \
  --max-errors 1000 \
  --resume research_out/campaign.csv
```

Campaigns are durable and resumable. Sinter task identities bind the exact circuit, detector error model, decoder, and metadata. Aegis adds circuit and DEM hashes, confidence intervals, environment information, JSON summaries, and plots.

Aegis also accepts existing Stim circuit files:

```bash
aegis campaign --circuit experiment.stim --workers auto
```

When two decoders must be compared on exactly the same detector shots, use the paired comparison path:

```bash
aegis compare \
  --decoder aegis-pymatching aegis-pymatching-correlated \
  --distance 5 --p 0.006 --shots 100000 --seed 1234
```

The comparison artifact hashes the shared detector and observable samples and reports pairwise decoder disagreement.

Third-party research decoders can register through the `aegis_qec.decoders` entry-point group and then participate in campaigns and exact-shot comparisons without modifying Aegis itself.

See [Platform](https://github.com/hamidbahri92/Aegis/blob/main/docs/PLATFORM.md) for the plug-in contract, Sinter architecture, hardware provenance rules, and campaign semantics.

## Benchmarking and validation

Aegis deliberately separates different kinds of evidence because decoder-kernel speed, end-to-end application latency, structural correctness, and circuit-level logical performance are not interchangeable.

### End-to-end Aegis latency

```bash
aegis benchmark --decoder mwpm --distance 5 --rounds 6 --steps 1000
```

or:

```bash
aegis-bench realtime --decoder mwpm --distance 5 --rounds 6 --steps 1000
```

These measurements include Aegis orchestration around the decoder, so they should not be presented as raw sparse-blossom kernel timing.

### Circuit-level DEM acceptance

```bash
aegis-bench circuit-acceptance --distance 3 --rounds 3 --shots 1000 --p 0.01 --seed 1234
```

This benchmark generates a noisy Stim rotated-surface-code memory circuit, samples detector events and logical observables, and requires the Aegis direct DEM bridge to reproduce raw PyMatching predictions on the same shots.

### Controlled calibration advantage

```bash
aegis-bench calibration-advantage \
  --shots 10000 \
  --seed 20260928 \
  --out-json bench_out/calibration.json \
  --plot bench_out/calibration.png
```

Uniform and calibrated decoders receive the same sampled physical error chains. The experiment has exact residual-chain logical ground truth for its controlled graph and reports paired statistics, confidence intervals, expected rates, and relative improvement.

### Structural stress testing

```bash
aegis-bench sweep --decoder mwpm --p 0.01 0.02 0.04 --distance 5 --rounds 6 --trials 200
```

Structural sweeps test correction-chain behavior on synthetic detector patterns. They are software-validation tools, not physical logical-error-rate or threshold estimators.

Read [Benchmarking](https://github.com/hamidbahri92/Aegis/blob/main/docs/BENCHMARKING.md) before interpreting or publishing results.

## Sparse-blossom performance attribution

Aegis QEC uses PyMatching's sparse-blossom MWPM implementation. The published sparse-blossom work by Oscar Higgott and Craig Gidney reports very large speedups over older matching approaches, including a greater-than-one-hundred-thousand-times comparison with a NetworkX implementation at large code distance in the paper's benchmark.

Those are upstream PyMatching results, not blanket Aegis end-to-end speed claims.

If you publish Aegis timings, report the workload, Aegis version, PyMatching version, Python version, operating system, CPU, code distance, rounds, sample count, weight policy, optional reweighting or polishing settings, and whether the number is decoder-only or end-to-end.

Reference: Oscar Higgott and Craig Gidney, *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025), DOI 10.22331/q-2025-01-20-1600.

## Command-line interface

The primary command is `aegis`.

```text
aegis doctor
aegis demo
aegis study
aegis campaign
aegis compare
aegis decoders
aegis benchmark
aegis gui
```

Specialized and compatibility entry points are also installed:

```text
aegis-run
aegis-metrics
aegis-threshold
aegis-export-header
aegis-bench
aegis-gui
aegis-ci
```

The historical `aegis-threshold` command is retained for compatibility. Its structural sweep is not a physical QEC threshold estimator.

## Graphical workbench

Installing `aegis-qec[gui]` provides the optional Streamlit workbench:

```bash
aegis gui
```

The GUI is intended for interactive exploration. Its Circuit study workflow uses the same research implementation as the CLI and can export the JSON and CSV records needed to reproduce a study. Scripted or published work should still preserve the exact command, version, seed, and exported artifacts.

## Package architecture

The public high-level API lives under `aegis_qec`.

The historical `a3d` namespace contains much of the lower-level implementation, including decoding graphs, MWPM adapters, detector-error-model integration, calibration and correlation logic, experimental decoders, and research modules.

The `bench` package provides reproducible benchmark and acceptance commands.

The `gui` and `scripts` packages provide the optional interactive workbench and launch helpers.

A detailed package-level mental model is available in [Overview](https://github.com/hamidbahri92/Aegis/blob/main/docs/OVERVIEW.md).

## Validation status

The default MWPM path has the strongest test coverage. Tests verify sparse-blossom backend identity, detector-to-detector and detector-to-boundary corrections, virtual-boundary translation, correction-edge reconstruction, matcher reuse for batch decoding, comparison with PyMatching's independent decoded-edge oracle, explicit DEM detector inputs, and circuit-level DEM parity.

Hosted CI tests Ubuntu and Windows on Python 3.10, 3.11, and 3.12. It runs repository defect lint, stricter lint over release-critical surfaces, the full pytest suite, command-line smoke tests, package builds, Twine metadata and README rendering checks, built-wheel installation, circuit acceptance, and the controlled calibration benchmark.

Experimental decoders and hardware-facing research modules remain intentionally distinguished from the best-validated production path.

## Reproducible research

For results intended for comparison or publication, preserve:

- the Aegis version or exact commit;
- Python, PyMatching, Stim, NumPy, and optional dependency versions;
- operating system and processor;
- decoder and optional polishing or reweighting settings;
- code distance and number of rounds;
- graph construction and weight policy;
- random seed and input-generation procedure;
- sample count and timed region;
- raw JSON, plots, logs, or other output artifacts.

Aegis is intentionally explicit about what each benchmark establishes so that structural tests, controlled models, circuit-level acceptance, and upstream decoder results are not conflated.

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

See [Contributing](https://github.com/hamidbahri92/Aegis/blob/main/CONTRIBUTING.md) before opening a pull request.

## Documentation

- [Overview](https://github.com/hamidbahri92/Aegis/blob/main/docs/OVERVIEW.md) — architecture, package identity, graph model, interfaces, and validation surfaces.
- [Algorithms](https://github.com/hamidbahri92/Aegis/blob/main/docs/ALGORITHMS.md) — sparse-blossom MWPM, graph translation, DEM decoding, erasures, and experimental decoders.
- [Benchmarking](https://github.com/hamidbahri92/Aegis/blob/main/docs/BENCHMARKING.md) — performance methodology, circuit acceptance, calibration experiments, structural sweeps, and reproducibility.
- [Research Guide](https://github.com/hamidbahri92/Aegis/blob/main/docs/RESEARCH_GUIDE.md) — circuit studies, student projects, practitioner workflows, uncertainty, artifacts, and reproducible reporting.
- [Platform](https://github.com/hamidbahri92/Aegis/blob/main/docs/PLATFORM.md) — resumable Sinter campaigns, exact shared-shot comparisons, decoder plug-ins, and hardware provenance.

## Project scope

Aegis QEC is built for **quantum error correction**, **surface-code and rotated-surface-code decoding**, **minimum-weight perfect matching (MWPM)**, **sparse blossom**, **PyMatching**, **Stim detector error models**, **calibrated and erasure-aware decoding**, **decoder benchmarking**, and **fault-tolerant quantum computing research**.

## Cite Aegis QEC

If Aegis QEC contributes to your research, cite the software and the decoder papers used by your experiment. Machine-readable citation metadata is provided in [CITATION.cff](https://github.com/hamidbahri92/Aegis/blob/main/CITATION.cff).

If the project saves you time, a GitHub star helps other quantum-error-correction researchers discover it. Reproducible bug reports, benchmark improvements, decoder implementations, tests, and documentation contributions are welcome.

## License

Aegis QEC is released under the MIT License. See [LICENSE](https://github.com/hamidbahri92/Aegis/blob/main/LICENSE).
