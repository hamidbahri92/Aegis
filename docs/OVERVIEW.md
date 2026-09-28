# Aegis QEC overview

Aegis QEC is a Python research toolkit for hardware-aware quantum error-correction experiments. Its production minimum-weight perfect-matching path delegates matching to PyMatching's sparse-blossom implementation and focuses Aegis itself on the surrounding experimentation layer: graph construction, calibrated edge costs, erasure and leakage information, soft inputs, correlation-aware research paths, detector-error-model interoperability, benchmarking, and reproducible interfaces.

## Product and package identity

The product name is **Aegis QEC**.

The package published to PyPI is `aegis-qec`.

The stable public Python namespace is `aegis_qec`.

The historical implementation namespace `a3d` remains importable for compatibility, but new examples and integrations should prefer `aegis_qec`.

Aegis QEC 1.1 requires Python 3.10 or newer. The release CI matrix validates Linux and Windows on Python 3.10 and 3.12.

## Default decoding path

`AegisConfig()` defaults to `decoder_type="mwpm"`. That path constructs an Aegis decoding graph and invokes PyMatching sparse blossom. Each Aegis edge receives a PyMatching fault identifier, and Aegis boundary edges are represented using PyMatching virtual boundaries. The correction vector is mapped back to the original Aegis edge objects.

The backend string is `pymatching-sparse-blossom`.

There is no silent NetworkX production fallback.

Experimental features such as OSD polishing, two-pass correlation-aware MWPM, learned correlation adjustments, union-find decoding, belief-propagation reweighting, and Transformer reweighting must be selected explicitly.

## Interfaces

The primary command-line entry point is `aegis`.

`aegis doctor` checks the environment and performs a small known-answer sparse-blossom decode.

`aegis demo` runs a deterministic first experiment and explains the result.

`aegis benchmark` measures Aegis end-to-end latency and clearly labels it as an Aegis measurement rather than an upstream PyMatching comparison.

`aegis gui` launches the optional Streamlit workbench.

The older entry points remain available for compatibility and specialized workflows.

## Interactive application

The graphical workbench is organized around experiments rather than internal implementation names. The application displays the active Aegis and PyMatching versions, the actual MWPM backend, and optional dependency status. Decoder choices explicitly identify the recommended production path and experimental alternatives.

The current workbench offers deterministic decode experiments, latency measurements, and correction-validation sweeps. The validation sweep is not a circuit-level logical-error-rate experiment and is not presented as one.

## Stim interoperability

Stim detector error models describe probabilistic error mechanisms and detector connectivity. They do not contain the observed detector outcomes for a specific shot. Aegis therefore requires explicit detection-event bits when a detector error model is decoded.

This separation prevents an error model from being mistaken for observed data.

## Evidence policy

Aegis distinguishes three kinds of performance evidence.

First, upstream published results belong to the upstream implementation. The greater-than-100,000-times comparison against NetworkX is a PyMatching surface-code benchmark reported by the PyMatching authors.

Second, `aegis benchmark` measures Aegis end-to-end latency for the workload and environment shown by the command.

Third, Aegis correction-validation sweeps are synthetic validation experiments. They should not be described as circuit-level logical-error-rate measurements.

See [BENCHMARKING.md](BENCHMARKING.md) for the detailed policy.

## Quality and release gates

Pull-request CI runs on Linux and Windows with supported Python versions. It checks repository-wide likely defects, applies stricter linting to release-critical code, runs the test suite, verifies the sparse-blossom backend, exercises the public commands, builds the wheel and source distribution, checks the rendered package metadata with Twine, installs the built wheel, and executes an installed-package smoke test.

PyPI publication performs another build, Twine metadata check, wheel installation, `aegis doctor` self-test, and version assertion before upload.
