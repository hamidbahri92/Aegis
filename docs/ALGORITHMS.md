# Aegis QEC algorithms

## Minimum-weight perfect matching

Aegis QEC uses PyMatching v2+ as its production MWPM engine. PyMatching v2 implements the sparse-blossom algorithm described by Oscar Higgott and Craig Gidney in *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025).

Aegis converts each non-boundary decoding-graph node into a PyMatching detector node and converts explicit Aegis boundary edges into PyMatching virtual-boundary edges. Every Aegis edge receives a unique PyMatching fault identifier, so the correction vector maps directly back to the original Aegis `Edge` objects. This preserves the correction path instead of returning only matched defect pairs.

The matcher is cached by graph topology and effective edge weights. `MWPMDecoder.decode_batch` reuses the compiled matcher and calls PyMatching's batched decoder.

The previously shipped NetworkX MWPM backend is intentionally not a silent fallback. If the sparse-blossom dependency is unavailable, installation should fail rather than quietly selecting a dramatically slower algorithm under the same decoder name.

## Edge costs

Aegis stores edge weights as negative log odds. Erasure probability is fused into the edge error probability and converted back to an effective negative-log-odds weight before matching.

## MWPM variants

`mwpm` runs exact sparse-blossom MWPM. `mwpm2` performs a first MWPM pass, applies a local correlation reweighting, and runs sparse-blossom MWPM again. `mwpm_corr` applies correlation-model or motif adjustments before calling the same sparse-blossom backend.

## Other decoders and reweighters

Aegis also includes union-find with erasures, greedy matching with OSD fallback, BP edge reweighting, and optional Transformer edge reweighting. These are separate experimental paths and should be benchmarked and validated independently of the MWPM backend.

## Performance claims

PyMatching's published surface-code benchmark reports more than a 100,000x speedup over NetworkX. Aegis should cite that result as a property of the referenced PyMatching benchmark, not as an unconditional end-to-end Aegis speedup. Aegis end-to-end timings include graph construction, reweighting, certificates, logging, and result reconstruction unless a benchmark explicitly excludes them.
