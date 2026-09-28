# Aegis QEC algorithms

## Production minimum-weight perfect matching

Aegis QEC 1.1 uses PyMatching 2.4 or newer as the production minimum-weight perfect-matching engine. PyMatching 2 implements the sparse-blossom algorithm described by Oscar Higgott and Craig Gidney in *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025).

`AegisConfig()` defaults to `decoder_type="mwpm"`. Experimental OSD polishing is disabled by default, so the ordinary default path does not silently replace a sparse-blossom result with a different decoder.

## Graph translation

Aegis decoding graphs contain stabilizer nodes, spatial and temporal edges, and explicit side-aware boundary nodes.

For sparse-blossom decoding, Aegis compacts non-boundary graph nodes into PyMatching detector indices. Ordinary Aegis edges are added with `Matching.add_edge`. Edges that connect a detector to an Aegis boundary node are represented with `Matching.add_boundary_edge`.

Every translated Aegis edge receives a unique PyMatching fault identifier. PyMatching can therefore return a correction vector that Aegis maps directly back to its original `Edge` objects. This preserves concrete correction paths instead of returning only paired defect identifiers.

The compiled matcher is cached by graph topology and effective edge weights. `MWPMDecoder.decode_batch` reuses one compiled PyMatching graph for multiple syndrome shots.

## Boundary handling

Aegis graph construction uses side-aware boundary nodes for west, east, north, and south boundaries at each time slice. The sparse-blossom adapter converts detector-to-boundary edges into PyMatching virtual-boundary edges.

Tests cover detector-to-detector correction paths and virtual-boundary corrections, including the mapping from a PyMatching fault vector back to the corresponding Aegis boundary edge.

## Edge costs

Aegis represents matching costs using negative log odds. Erasure information can modify effective edge probabilities before they are converted back into matching costs.

When comparing measurements across decoder variants, report how weights were constructed. A timing number without the graph and weight policy is not a complete decoder benchmark.

## Decoder families

`mwpm` is the validated production sparse-blossom path.

`mwpm2` performs a sparse-blossom pass, applies a local correlation-inspired reweighting, and performs a second sparse-blossom pass. It is experimental.

`mwpm_corr` applies motif-based or configured correlation adjustments before sparse-blossom matching. It is experimental.

`uf` selects the union-find-with-erasures research path. It is experimental.

Greedy, OSD, belief-propagation reweighting, and Transformer reweighting remain research paths and are not presented as equivalent in validation status to the production `mwpm` backend.

## Optional OSD polishing

Aegis retains an optional OSD polishing mechanism for experiments. It can compare an OSD-derived correction against an existing result and replace the result if its internal likelihood metric is lower.

This mechanism is disabled by default in version 1.1. Experiments that enable it should report that fact because the final correction is no longer guaranteed to be the direct sparse-blossom output.

## Detector error models

A detector error model is an error model, not an observed shot. Aegis therefore requires explicit observed detection-event bits when decoding a Stim DEM.

`PyMatchingMWPMDecoder.decode_from_dem` raises an error if the syndrome argument is omitted. This prevents the historical placeholder behavior in which a DEM could be treated as if it were observed detector data.

## Performance claims

The greater-than-100,000-times comparison against NetworkX is an upstream PyMatching benchmark for a specific surface-code workload. It is not an unconditional Aegis speedup.

Aegis end-to-end latency can include graph construction, reweighting, correction reconstruction, logging, certificates when explicitly enabled, and Python orchestration. Benchmark reports must identify what is inside the timed region.

See [BENCHMARKING.md](BENCHMARKING.md) for the benchmark taxonomy and reporting rules.
