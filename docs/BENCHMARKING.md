# Benchmarking Aegis QEC

Aegis QEC uses several kinds of evidence. They answer different questions and must not be quoted as if they were interchangeable.

## Upstream PyMatching benchmark

PyMatching's sparse-blossom documentation and paper report a greater-than-100,000-times speedup over NetworkX for their named surface-code benchmark. That result belongs to PyMatching and should be attributed to Higgott and Gidney.

Aegis uses the same PyMatching sparse-blossom engine for its production MWPM path, but Aegis does not claim that every end-to-end Aegis workload is more than 100,000 times faster than an older Aegis workload.

Reference: Oscar Higgott and Craig Gidney, *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025), DOI 10.22331/q-2025-01-20-1600.

## Aegis end-to-end latency

`aegis benchmark` and `aegis-bench realtime` measure Aegis end-to-end decoder latency for deterministic synthetic syndrome inputs.

Example:

```bash
aegis benchmark --decoder mwpm --distance 5 --rounds 6 --steps 1000
```

The command reports p50, p95, and p99 latency and writes the raw summary to CSV.

When publishing or comparing these measurements, report at least the Aegis version, PyMatching version, Python version, operating system, CPU, decoder, code distance, number of rounds, sample count, and whether optional reweighting or polishing was enabled.

These timings should be described as **Aegis end-to-end latency**, not as a reproduction of PyMatching's NetworkX comparison.

## Structural correction-chain stress sweep

`aegis-bench sweep` generates deterministic synthetic detector-bit patterns and runs the selected Aegis decoder.

The structural check has exactly two parts. First, it applies the proposed correction edges to the supplied syndrome and requires all detector defects to be annihilated. Second, it checks whether the **correction chain itself** contains a spatial component touching opposite side-aware boundaries in one time slice.

That second check is not the homology of the physical residual error. The function does not receive the sampled physical error chain, so it cannot form error-plus-correction and cannot determine logical success. The synthetic detector bits are also not sampled from a complete quantum circuit.

For compatibility, CSV output retains `validation_failure_rate`. New output also includes the explicit name `structural_validation_failure_rate`.

This sweep is useful as a software stress test for graph construction, decoder behavior, syndrome annihilation, and correction mapping. It is **not** a circuit-level logical-error-rate measurement and it is **not** a threshold estimate.

Example:

```bash
aegis-bench sweep --decoder mwpm --p 0.01 0.02 0.04 --distance 5 --rounds 6 --trials 200
```

The historical `aegis-threshold` command uses related structural machinery. Its name is retained for compatibility, but its output must not be cited as a QEC threshold.

## Circuit-level DEM acceptance

`aegis-bench circuit-acceptance` generates a noisy rotated surface-code memory circuit with Stim, samples detector events and the corresponding logical observables, and decodes the exact same detector shots through two paths:

1. a raw `pymatching.Matching` constructed directly from the Stim detector error model;
2. Aegis's `PyMatchingMWPMDecoder` DEM bridge.

Example:

```bash
aegis-bench circuit-acceptance --distance 3 --rounds 3 --shots 1000 --p 0.01
```

The acceptance check reports the number of shot-by-shot prediction mismatches between Aegis and raw PyMatching and reports each path's logical-error rate against Stim's sampled logical observables.

A zero adapter-mismatch count establishes that Aegis's DEM input/output plumbing preserves PyMatching's predictions for that sampled circuit and workload. It does **not** validate Aegis's custom decoding-graph builder because the DEM path delegates graph construction to PyMatching.

## Custom graph-adapter acceptance

The unit suite separately cross-checks the Aegis graph adapter against PyMatching's independent `decode_to_edges_array` output. Aegis's fault-ID-derived correction edges are normalized back into detector-edge pairs and compared with PyMatching's decoded edge solution, including virtual-boundary edges.

This test is designed to catch a class of bugs where sparse blossom finds the right matching but Aegis maps returned fault IDs back to the wrong Aegis `Edge` objects.

## Controlled calibration-advantage experiment

`aegis-bench calibration-advantage` is a deliberately small graph-level experiment designed to answer one narrow question: does supplying correct non-uniform edge probabilities change the logical outcome when the noise is genuinely non-uniform?

The model contains two detector nodes between opposite boundaries. A single middle-edge error and a pair of boundary-edge errors produce the same detector syndrome, but the two physical error chains differ by a boundary-to-boundary logical path. This makes the residual chain, physical error XOR correction, an exact ground-truth logical test for this model.

The default experiment uses boundary-edge error probabilities of 0.18 and a middle-edge probability of 0.01. The uniform baseline receives the global average probability on every edge. The calibrated decoder receives the actual edge probabilities. Both decoders process exactly the same sampled physical error chains.

Example:

```bash
aegis-bench calibration-advantage --shots 10000 --seed 20260928
```

The command reports graph-level logical failure rates, paired discordant failure counts, relative reduction, and the uniform-to-calibrated failure ratio. The implementation also reports the analytically expected failure rates for this three-edge model so the Monte Carlo result can be checked against a closed-form reference.

This experiment proves that Aegis's non-uniform graph-weight plumbing can improve decoding when the supplied calibration is informative. It does **not** prove that Aegis currently converts IBM or other device calibration records into correct surface-code edge probabilities. The current hardware interface can acquire calibration-like arrays, while the production runtime still requires graph weights to be supplied through its weight dictionaries. Building and validating that calibration-to-decoding-graph mapping remains separate work.

## What is still missing

The controlled graph experiment now demonstrates that correct non-uniform weights can beat a uniform baseline in a model with exact residual-chain ground truth. What is still missing is the stronger hardware claim: a validated mapping from real device calibration or a realistic circuit-level non-uniform noise model into Aegis graph weights, followed by logical-observable comparisons against an appropriate baseline.

Until that end-to-end calibration mapping is validated, IBM calibration ingestion, leakage handling, learned reweighting, and related research paths should be treated as capabilities under evaluation rather than demonstrated device-level improvements over plain Stim plus PyMatching.

## Reproducibility rules

Do not use the upstream greater-than-100,000-times result as an Aegis end-to-end number.

Do not call the structural stress sweep a circuit-level logical-error-rate benchmark or a threshold estimate.

Do not compare two latency numbers without identifying the workload and timed region.

Do record dependency versions, random seeds, circuit parameters, and hardware.

Do preserve the input corpus or generation procedure when a benchmark uses generated data.

These rules are part of the Aegis QEC evidence policy, not merely documentation style.
