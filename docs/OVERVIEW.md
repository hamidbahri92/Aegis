# Aegis QEC overview

Aegis QEC is an experimentation layer around quantum-error-correction decoding. Its strongest path combines Aegis surface-code graph construction and experiment orchestration with PyMatching's sparse-blossom minimum-weight perfect matching. The project also contains research decoders, reweighting methods, benchmarking tools, a Stim detector-error-model bridge, and an optional graphical workbench.

This document describes the code that exists today. It separates the stable public interface and validated paths from experimental modules so users can choose the right level of trust for a given experiment.

## Package identity

The product name is **Aegis QEC**.

The PyPI distribution is `aegis-qec`.

The public Python namespace is `aegis_qec`.

The historical implementation namespace `a3d` remains importable for compatibility and still contains most low-level modules.

Aegis QEC 1.1 requires Python 3.10 or newer. Hosted CI tests Ubuntu and Windows with Python 3.10, 3.11, and 3.12.

## Mental model

At the top level, `aegis_qec` exposes `AegisConfig`, `DecoderRuntime`, and `RotatedSurfaceLayout`. The runtime creates decoding graphs for the X and Z sectors, applies optional cost transformations, dispatches to the selected decoder, and returns concrete correction edges.

The default decoder is `mwpm`. `a3d.decoder_mwpm.MWPMDecoder` translates the Aegis graph into a `pymatching.Matching`, converts Aegis boundary edges into PyMatching virtual-boundary edges, assigns one fault identifier per Aegis edge, and reconstructs Aegis correction edges from PyMatching's fault vector. The compiled matcher is cached and reused when the graph topology and effective weights are unchanged.

The direct Stim path is separate. `a3d.decoder_mwpm_pm.PyMatchingMWPMDecoder` constructs a PyMatching decoder from a Stim detector error model and requires explicit detector events for each shot. This is the preferred route when the detector error model itself is the source of graph semantics.

## Graphs and costs

Aegis graph nodes carry sector, coordinate, time index, and role metadata. Edges represent spatial, temporal, or boundary relationships and carry weights plus optional erasure probabilities.

The runtime can create uniform costs for controlled tests or costs derived from configuration fields such as data-error probability, measurement-error probability, leakage probability, and time-weight scaling. The default MWPM backend consumes the resulting effective costs.

Aegis also exposes optional reweighting paths. Belief-propagation reweighting, Transformer reweighting, correlation adjustments, and multi-pass MWPM are experimental and should be reported explicitly when used.

## Decoder families

The best-tested path is `mwpm`, backed by PyMatching sparse blossom.

`mwpm2`, `pipelined_mwpm`, and `pmwpm` select a two-pass MWPM experiment that adjusts local costs after an initial decode.

`mwpm_corr`, `mwpmc`, and `mwpm3` select a correlation-adjusted MWPM experiment.

`uf`, `unionfind`, and `uf_e` select the union-find-with-erasures research path.

Greedy and OSD paths remain available. OSD polishing can also be enabled as an optional certificate stage. Because polishing can replace a sparse-blossom result, experiments using it should state that it was enabled.

## Detector error models

A detector error model and a detector shot are different objects. The model defines possible error mechanisms and detector/observable relationships. A shot supplies the observed detector bits.

Aegis enforces this distinction in `PyMatchingMWPMDecoder.decode_from_dem`: omitting the syndrome raises an error. `decode_dem_batch` supports multiple detector shots with one compiled matcher.

The older `a3d.stim_adapter` text parser projects a narrow subset of DEM text into an Aegis `DecodingGraph`. It cannot faithfully represent arbitrary Stim hyperedges, repeat structure, observables, or detector-shift semantics. Treat it as a compatibility helper, not as a general Stim parser.

## Validation surfaces

The test suite checks several independent properties of the default path. It verifies the backend identity string, detector-to-detector and detector-to-boundary corrections, batch reuse, mapping of PyMatching fault identifiers back to Aegis edges, and edge-level parity against PyMatching's independent `decode_to_edges_array` output.

For detector error models, the circuit-acceptance benchmark generates a noisy rotated surface-code memory circuit with Stim, samples detector events and logical observables, and decodes the same shots through raw PyMatching and the Aegis DEM bridge. The acceptance test requires the two prediction streams to match.

The controlled calibration experiment uses a small graph with exact residual-chain logical ground truth to test whether informative non-uniform weights can outperform a uniform baseline on the same sampled physical errors.

Structural sweeps serve a different purpose. They test software behavior using synthetic detector patterns and correction-chain checks. They are not physical threshold or logical-error-rate experiments.

## User interfaces

The `aegis` command is the main user entry point. `doctor` checks the environment and sparse-blossom backend, `demo` runs a deterministic decode, `benchmark` measures end-to-end latency, and `gui` launches the optional Streamlit workbench.

`aegis-bench` exposes specialized benchmark commands including `realtime`, `calibration-advantage`, `circuit-acceptance`, `sweep`, and `autobench`.

Older commands remain installed for compatibility with existing scripts.

## Where to go next

Read [Algorithms](ALGORITHMS.md) for decoder and graph details. Read [Benchmarking](BENCHMARKING.md) before interpreting performance or logical-failure numbers. The repository root [README](../README.md) is the quickest installation and first-use guide.
