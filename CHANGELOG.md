# Changelog

All notable user-facing changes to Aegis QEC are recorded here.

## 1.1.0 — 2026-09-28

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
