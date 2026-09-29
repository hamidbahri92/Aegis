# Changelog

All notable user-facing changes to Aegis QEC are recorded here.

## Unreleased

### Scientific validation and repository hygiene

The historical structural correction check is now named for what it measures. It verifies syndrome annihilation and correction-chain boundary topology but does not claim to determine logical success without the sampled physical error chain.

A Stim circuit-level acceptance path now samples detector events and logical observables and compares Aegis DEM predictions with raw PyMatching shot for shot.

The sparse-blossom graph adapter is cross-checked against PyMatching's decoded edge output so fault-ID-to-Aegis-edge mapping errors are directly testable.

The placeholder `edge_reweighter.pt` checkpoint was removed. The Transformer training script is explicitly documented as experimental scaffolding and generated checkpoints are ignored by Git.

Python 3.11 is now included in the hosted CI matrix alongside 3.10 and 3.12.

The stale pre-1.1 Dependabot pull requests were closed as superseded.

A controlled non-uniform calibration benchmark now compares uniform and correctly calibrated MWPM weights on identical sampled physical error chains with exact residual-chain homology in the benchmark graph. The result is explicitly scoped as graph-level evidence, not a claim that device calibration ingestion is already end to end.

The historical `trial_error_rate` helper is now documented and deprecated as a synthetic decoder smoke proxy rather than a logical-error-rate estimator.

The legacy `stim_adapter.graph_from_dem_text` parser is deprecated and renamed `graph_from_dem_text_approximate`. Production DEM decoding continues through Stim and PyMatching directly; the approximate parser is retained only for compatibility with explicitly lossy structural experiments.

## 1.1.0 — 2026-09-28

### Behavior changes and migration note

Version 1.1 changes the behavior of default-constructed configurations. `AegisConfig()` previously selected the OSD path; it now selects PyMatching sparse-blossom MWPM. Optional OSD polishing is also disabled by default.

Existing code that depends on the previous default should set `decoder_type="osd"` explicitly. Code that depended on the historical NetworkX MWPM implementation must migrate because NetworkX is no longer an Aegis production fallback.

### Package identity

Aegis is standardized as **Aegis QEC** in public documentation.

The PyPI distribution remains `aegis-qec`.

The stable public Python namespace is `aegis_qec`, while `a3d` remains available for compatibility.

Python 3.10 is the minimum supported version for this release.

### Decoder

The default `AegisConfig` decoder is now `mwpm`.

Production MWPM uses PyMatching 2.4+ sparse blossom with no silent NetworkX fallback.

Aegis graph edges are mapped to PyMatching fault identifiers so returned correction vectors map back to concrete Aegis correction edges.

Explicit Aegis boundary edges are translated to PyMatching virtual-boundary edges.

Compiled matchers are cached, and batched sparse-blossom decoding is available.

Optional OSD polishing is disabled by default so the ordinary production path remains sparse blossom end to end.

Detector error models now require explicit observed detection-event bits instead of returning a placeholder correction.

### User experience

A new `aegis` command is the primary entry point.

`aegis doctor` reports the environment and performs a known-answer sparse-blossom self-test.

`aegis demo` provides a deterministic first decoding experiment.

`aegis benchmark` reports end-to-end latency with a clear scope statement.

`aegis gui` launches a reorganized interactive workbench that labels recommended and experimental paths separately.

The benchmark CLI now prints useful terminal summaries instead of silently writing files.

### Benchmark semantics

The published greater-than-100,000-times comparison is explicitly attributed to PyMatching's named surface-code benchmark against NetworkX.

Aegis end-to-end latency measurements are labeled separately.

The synthetic sweep output is renamed `validation_failure_rate` and is no longer presented as a circuit-level logical-error rate.

### Quality and release engineering

CI validates Linux and Windows on Python 3.10 and 3.12.

CI runs repository defect linting, strict release-surface linting, the test suite, backend assertions, command-line smoke tests, package builds, Twine metadata checks, wheel installation, and installed-package self-tests.

The PyPI publication workflow performs package validation and an installed-wheel doctor check before upload.

The obsolete v13 release workflow and duplicate local CI launcher were removed.
