# Changelog

This file records user-visible changes to Aegis QEC.

## Unreleased

### Exploratory adaptive discovery

Added resumable random and evolutionary search over Aegis experiment-manifest parameters. Search dimensions and objectives use explicit JSON pointers, candidate experiments keep full run records, failures remain visible, and multi-objective results are reported as Pareto fronts.

Evolutionary discovery uses non-dominated sorting, crowding-distance diversity, crossover, and bounded mutation. Completed assignments are cached in durable state and resume refuses changed search definitions or changed base experiments.

Pareto candidates export fresh-seed, unexecuted confirmation manifests with optional higher-fidelity overrides. Discovery artifacts are explicitly labeled exploratory so search-selected evidence is not silently treated as independent confirmation.

### End-to-end research projects and publication packages

Added versioned research-project manifests that connect research questions, hypotheses, experiment manifests, evidence artifacts, claims, and manuscript metadata.

Added protocol freezing for confirmatory work. Project audits detect changed locked inputs, missing evidence, unresolved JSON pointers, and failed quantitative predicates.

Added project execution across declared experiment manifests with preserved Aegis experiment bundles and a project-run record.

Added LaTeX and Markdown manuscript generation plus reviewer-grade submission packages containing claim-to-evidence maps, reproduction instructions, environment metadata, artifact inventories, checksums, readiness checklists, and optional PDF compilation through Tectonic or latexmk.

Added blind-review packaging that redacts declared author identity, repository/data URLs, and local source paths, plus directory/ZIP package verification and tamper detection.

Submission packages now include exact experiment manifests, a separate machine-readable submission-readiness verdict, venue-focused readiness checks, reproduction commands, compute-resource disclosure, and optional Croissant 1.0 JSON-LD metadata for declared dataset contributions.

Confirmatory project audits now fail closed when a valid frozen protocol is absent.

### Paired decoder inference

Fixed-dataset evaluations now report paired logical-failure contingency counts, left-minus-right error-rate differences with 95 percent intervals, and continuity-corrected asymptotic McNemar p-values.

### Fixed-dataset decoder evaluation

Added `aegis dataset evaluate` for paired decoder comparison on identical stored syndrome rows. Evaluation artifacts hash the exact selected detector and observable subset and report logical-error intervals, throughput, and pairwise decoder disagreement.

### Reusable QEC datasets

Added resumable HDF5 syndrome datasets for decoder benchmarking, ML training, coursework, and regression studies. Datasets preserve syndromes, observables, deterministic train/validation/test labels, circuit and DEM provenance, sparse raw error-mechanism incidence, optional dense mechanism matrices, and content hashes.

Added `aegis dataset generate` and `aegis dataset inspect`. Resume configuration is identity-checked and deterministic chunk sampling produces the same final scientific hashes as uninterrupted generation.

### Experiment catalog

Added experiment templates to the installed wheel plus `aegis templates` and `aegis init-experiment`. Students and research teams can now create a valid study, explanation, decoder comparison, scaling campaign, or regression manifest without cloning the repository.

CI verifies the template resources both from the source checkout and from the built wheel.

### Decoder plug-in SDK

Normalized third-party decoders across Aegis workflows. A plug-in may implement either Sinter's compiled batch contract or file contract; Aegis supplies the missing compatibility side so the same decoder can participate in campaigns, exact shared-shot comparisons, and detector-file prediction.

Added `aegis validate-decoder`, a deterministic conformance suite covering multiprocessing picklability, bit-packed batch output, known-answer decoding, and file round trips. Added strict dtype, shape, and output-size validation at the decoder boundary.

### Version-controlled experiments

Added JSON experiment manifests that can execute studies, Sinter campaigns, exact shared-shot comparisons, detector-shot prediction, finite-size scaling, and one-shot explanations through one reviewable contract.

Every manifest run writes a hashed `aegis-run.json` record containing the manifest identity, environment versions, local input hashes, generated artifact hashes, and machine-readable result.

Added self-verifying `.aegis.zip` research bundles plus `aegis verify-bundle`. Bundle verification rejects missing, modified, unexpected, or unsafe entries.

Added a JSON Schema and version-controlled example manifests for editor, CI, coursework, and team workflows.

### Single-shot explanation

Added a reproducible one-shot surface-code debugger for education and decoder analysis. It records fired detector coordinates, MWPM detection-event pairings, correction-path edges, sampled and predicted logical observables, logical outcome, and provenance hashes. The same explanation is available from the CLI and graphical workbench.

### Finite-size scaling analysis

Added first-order finite-size scaling analysis for campaign artifacts. The fit uses aggregated binomial logical-failure counts, profiles the critical physical-error probability over the scaling exponent, reports a profile-likelihood interval and AIC comparison, and warns when the sampled grid or search range cannot support a stable interpretation.

### Research platform

Added resumable multiprocessing campaigns backed by Sinter, including durable CSV resume, maximum-shot and maximum-error stopping conditions, detection-event counting, JSON summaries, plots, and support for existing Stim circuit files.

Added an extensible decoder registry using the `aegis_qec.decoders` entry-point group. Built-in Aegis adapters provide standard and correlated PyMatching modes.

Added exact shared-shot decoder comparison with circuit, detector-error-model, detector-sample, and observable-sample hashes plus pairwise prediction disagreement statistics.

Added standard-file prediction for existing Stim detector error models and detector-shot data, with input/output provenance hashes for external simulator and hardware pipelines.

IBM calibration access now fails closed instead of silently substituting synthetic calibration data. Synthetic fallback requires explicit opt-in and returned calibration objects identify their provenance.

### Research workbench

Added a reproducible circuit-level surface-code study workflow through the main `aegis study` command and the Streamlit workbench. Studies generate Stim rotated-memory circuits, decode sampled detector events through Aegis's direct detector-error-model bridge, report logical-error rates with 95 percent Wilson intervals, and export JSON, CSV, and plot artifacts.

Study records capture seeds, dependency versions, environment information, circuit parameters, detector counts, timings, and the explicit noise-model mapping. A new research guide documents student projects, practitioner workflows, uncertainty, and interpretation boundaries.

### Community research

Added a structured GitHub issue form for reproducible research results and comparisons.

## 1.1.1 — 2026-10-04

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
