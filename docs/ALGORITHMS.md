# Algorithms in Aegis QEC

Aegis QEC contains one default decoding path with the strongest validation coverage and several experimental alternatives. This page explains what each path actually does so benchmark results can be interpreted correctly.

## Sparse-blossom MWPM

`AegisConfig()` defaults to `decoder_type="mwpm"`. The implementation lives in `a3d.decoder_mwpm.MWPMDecoder` and uses PyMatching 2.4 or newer.

Aegis does not implement a second hidden matching engine for this path. It builds an Aegis `DecodingGraph`, translates that graph into `pymatching.Matching`, calls PyMatching, and reconstructs Aegis correction edges from the returned fault vector.

The backend string is `pymatching-sparse-blossom`.

### Graph translation

Boundary nodes in an Aegis graph are explicit nodes whose role begins with `boundary`. During compilation, ordinary detector-to-detector edges become PyMatching edges. Detector-to-boundary edges become PyMatching virtual-boundary edges.

Each translated Aegis edge receives its graph index as a PyMatching fault identifier. After decoding, nonzero fault identifiers are mapped directly back to the original Aegis `Edge` objects.

This design matters because Aegis needs concrete correction paths for validation and downstream experiments, not merely a list of paired defects.

### Cached and batch decoding

The matcher cache key includes detector nodes, edge endpoints, effective weights, and boundary status. Repeated decodes on an unchanged graph reuse the compiled matcher.

`MWPMDecoder.decode_batch` compiles once, stacks detector shots into a NumPy array, and uses PyMatching's batch decoder.

## Costs and erasures

Aegis graph edges carry a weight and optional erasure probability. Effective costs are computed before matching.

The calibrated runtime path derives spatial and temporal weights from configured data and measurement probabilities using negative log odds. The uniform path assigns constant spatial and temporal weights and is useful for controlled comparisons.

Erasure-aware behavior is available in the graph cost model and in the union-find research path. When publishing results, state how weights and erasure probabilities were produced.

## Direct Stim DEM decoding

`a3d.decoder_mwpm_pm.PyMatchingMWPMDecoder` is the direct detector-error-model bridge.

`matching_from_dem` parses the DEM with Stim and creates a `pymatching.Matching` from it. `decode_dem` and `decode_dem_batch` then consume explicit detector-event bits.

A detector error model is not an observed shot. Accordingly, `decode_from_dem` raises a `ValueError` when no syndrome is supplied.

The circuit-acceptance test checks this bridge against raw PyMatching on the same Stim-generated detector samples and logical observables.

## The legacy DEM graph projection

`a3d.stim_adapter` contains a historical helper that projects a narrow subset of DEM text into an Aegis graph. That projection is not a complete Stim parser.

In particular, an ordinary `DecodingGraph` cannot faithfully recover arbitrary DEM hyperedges, repeat blocks, observable structure, or the full semantics of detector shifts from the helper's simplified representation. Use the direct `PyMatchingMWPMDecoder` DEM path when fidelity to a Stim detector error model matters.

## Experimental decoder paths

The following paths are intentionally available for research but should not be described as having the same validation status as default sparse-blossom MWPM.

**Pipelined MWPM.** `mwpm2`, `pipelined_mwpm`, and `pmwpm` perform a first sparse-blossom decode, lower selected local edge costs near the first correction, run sparse blossom again, and keep the result favored by the implementation's likelihood and average-cost comparison.

**Correlation-aware MWPM.** `mwpm_corr`, `mwpmc`, and `mwpm3` adjust edge costs using configured correlation parameters or local structural motifs before invoking sparse blossom.

**Union find with erasures.** `uf`, `unionfind`, and `uf_e` use an erasure-aware pre-peeling stage followed by a union-find-style growth process ordered by effective edge cost.

**Greedy and OSD.** The greedy decoder and OSD decoder remain available as research and compatibility paths. OSD can also be enabled as a post-decode polishing stage.

**Belief-propagation reweighting.** The BP module builds an adjacency graph over decoding edges and iteratively adjusts effective costs from local support.

**Transformer reweighting.** Optional Torch-backed reweighters generate per-edge cost adjustments from graph-derived features. These paths depend on model weights and experiment configuration and are not part of the default installation contract.

## What the tests establish

The default MWPM tests establish that Aegis uses the sparse-blossom backend, reconstructs ordinary and virtual-boundary correction edges, reuses a matcher for batch decoding, and agrees with PyMatching's independent decoded-edge oracle for representative syndromes.

The DEM tests establish that observed detector bits are required and that the Aegis direct DEM bridge can reproduce raw PyMatching predictions on sampled Stim circuits.

Those tests validate the adapter and integration contracts they exercise. They do not convert every experimental decoder or hardware-facing module into a validated physical-QEC result.

## Sparse-blossom reference

Oscar Higgott and Craig Gidney, *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025), DOI 10.22331/q-2025-01-20-1600.

The paper's performance results belong to the sparse-blossom implementation and benchmark described by the authors. See [Benchmarking](BENCHMARKING.md) for how Aegis separates upstream results from its own measurements.
