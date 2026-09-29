# Changelog

This file records user-visible changes to Aegis QEC.

## Unreleased

### Detector-error-model safety

The historical DEM-text-to-Aegis-graph projection is being made explicit as a lossy compatibility path. Faithful detector-error-model decoding uses Stim and PyMatching directly and requires the observed detector bits for each shot.

### Validation

Circuit acceptance compares the Aegis DEM bridge with raw PyMatching on identical Stim-generated detector samples and logical observables.

The custom graph adapter is checked against PyMatching's decoded-edge output so correction-edge reconstruction can be tested independently.

The controlled calibration experiment compares uniform and non-uniform graph weights on identical sampled physical error chains with exact residual-chain logical ground truth for its small benchmark graph.

Structural correction checks are described as structural validation rather than physical logical-error-rate or threshold measurements.

### Quality

Hosted CI covers Ubuntu and Windows on Python 3.10, 3.11, and 3.12. Release-critical code receives stricter linting in addition to repository defect checks, tests, command smoke tests, package validation, and installed-wheel checks.

## 1.1.0 — 2026-09-28

### Aegis QEC identity

The public product name is **Aegis QEC**.

The PyPI distribution is `aegis-qec`.

The public Python namespace is `aegis_qec`. The historical `a3d` namespace remains available for compatibility.

Python 3.10 is the minimum supported version.

### Default decoding path

`AegisConfig()` now defaults to `decoder_type="mwpm"`.

The default MWPM implementation uses PyMatching 2.4 or newer and identifies its backend as `pymatching-sparse-blossom`. There is no NetworkX fallback in this path.

Aegis graph edges are assigned PyMatching fault identifiers so decoded corrections can be reconstructed as concrete Aegis `Edge` objects. Explicit Aegis boundary edges are translated into PyMatching virtual-boundary edges.

Compiled matchers are cached for repeated graph topologies and weights, and batch decoding is available.

Optional OSD polishing is disabled by default. Existing applications that depended on the previous OSD default should select `decoder_type="osd"` explicitly.

### Detector error models

The direct DEM interface requires observed detector-event bits. Calling `decode_from_dem` without a syndrome raises an error instead of treating an error model as observed data.

Batch DEM decoding is available for multiple detector shots using one compiled matcher.

### Command-line experience

The `aegis` command is the primary entry point.

`aegis doctor` checks the installation, dependency versions, active sparse-blossom backend, and a known-answer decode.

`aegis demo` runs a deterministic first experiment.

`aegis benchmark` reports Aegis end-to-end latency.

`aegis gui` launches the optional interactive workbench.

Specialized and historical entry points remain installed for compatibility.

### Benchmark semantics

Aegis end-to-end timings are reported separately from upstream PyMatching performance results.

Synthetic structural sweeps are not presented as circuit-level logical-error-rate measurements or physical threshold estimates.

The sparse-blossom performance results cited by Aegis are attributed to the upstream Higgott and Gidney work rather than claimed as universal Aegis speedups.

### Packaging and release

Version 1.1.0 establishes the `aegis-qec` distribution and `aegis_qec` public namespace, validates package metadata and README rendering during CI, installs the built wheel for smoke tests, and supports tag-driven PyPI release automation.
