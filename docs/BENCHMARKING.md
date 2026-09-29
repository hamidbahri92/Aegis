# Benchmarking Aegis QEC

Aegis QEC exposes several benchmarks that answer different questions. Keeping those questions separate is the easiest way to avoid misleading performance or error-correction claims.

## One rule to remember

A decoder-kernel benchmark, an Aegis end-to-end latency measurement, a structural software stress test, and a circuit-level logical-error experiment are not interchangeable.

Always name the workload and the measurement boundary.

## Aegis end-to-end latency

Use either:

```bash
aegis benchmark --decoder mwpm --distance 5 --rounds 6 --steps 1000
```

or:

```bash
aegis-bench realtime --decoder mwpm --distance 5 --rounds 6 --steps 1000
```

The benchmark generates deterministic synthetic detector-bit inputs, runs the selected Aegis runtime path, and reports p50, p95, and p99 latency.

This is an Aegis end-to-end measurement. Depending on configuration, the timed path can include graph handling, cost transformation, PyMatching decoding, correction reconstruction, optional reweighting, and Python orchestration.

For a result intended for comparison or publication, record the Aegis version, PyMatching version, Python version, operating system, processor, decoder, code distance, number of rounds, sample count, weight policy, optional reweighter or polishing settings, and whether graphs or matchers were reused.

## Upstream PyMatching performance

Aegis QEC uses PyMatching's sparse-blossom implementation for default MWPM. Higgott and Gidney report sub-microsecond-per-round decoding for a distance-17 surface-code workload at 0.1 percent circuit-level depolarizing noise on one CPU core, and the paper reports extremely large improvements over older matching implementations, including a greater-than-one-hundred-thousand-times comparison with a NetworkX implementation at large code distance.

Those are upstream PyMatching results under the paper's workload and hardware. They are not universal Aegis end-to-end speedups.

Reference: Oscar Higgott and Craig Gidney, *Sparse Blossom: correcting a million errors per core second with minimum-weight matching*, Quantum 9, 1600 (2025), DOI 10.22331/q-2025-01-20-1600.

## Circuit-level DEM acceptance

Run:

```bash
aegis-bench circuit-acceptance --distance 3 --rounds 3 --shots 1000 --p 0.01 --seed 1234
```

Aegis generates a noisy rotated surface-code memory circuit with Stim, samples detector events together with logical observables, and decodes the same detector shots in two ways: directly through raw PyMatching and through `PyMatchingMWPMDecoder.decode_dem_batch`.

The command reports adapter mismatches and the logical-error rate of each prediction stream against the sampled logical observables.

A zero adapter-mismatch count is strong evidence for the DEM bridge on the sampled workload because both paths receive the same detector shots and must return the same observable predictions. It does not validate Aegis's custom graph builder because the DEM path delegates graph construction to PyMatching.

## Controlled calibration-advantage experiment

Run:

```bash
aegis-bench calibration-advantage \
  --shots 10000 \
  --seed 20260928 \
  --out-json bench_out/calibration.json \
  --plot bench_out/calibration.png
```

This experiment uses a deliberately small graph where two distinct physical error chains can produce the same detector syndrome but differ by a boundary-to-boundary logical path. That lets the benchmark evaluate the residual chain, physical error XOR correction, against exact logical ground truth for the model.

The uniform decoder receives one global probability on every edge. The calibrated decoder receives the actual non-uniform edge probabilities. Both decode exactly the same sampled physical error chains.

The output includes failure counts, graph-level logical-failure rates, Wilson ninety-five-percent confidence intervals, paired discordant failure counts, an exact paired-binomial p-value, analytically expected rates, relative reduction, and the uniform-to-calibrated failure ratio.

This demonstrates the behavior of Aegis's non-uniform weight plumbing when the supplied probabilities are informative. It is not evidence that arbitrary real-device calibration records are already converted into physically correct surface-code graph weights.

## Structural correction-chain sweep

Run:

```bash
aegis-bench sweep --decoder mwpm --p 0.01 0.02 0.04 --distance 5 --rounds 6 --trials 200
```

The sweep generates synthetic detector-bit patterns and checks whether proposed correction edges annihilate detector defects and whether the correction chain itself has problematic boundary topology.

The check does not receive a sampled physical error chain and cannot form the physical residual error. It therefore is not a circuit-level logical-error-rate measurement and is not a threshold estimator.

The historical `aegis-threshold` command uses related structural machinery. Its name remains for compatibility, but its output should be described as a structural stress result.

## Custom graph-adapter acceptance

The unit suite also cross-checks Aegis's custom graph adapter against PyMatching's independent `decode_to_edges_array` result. It normalizes both outputs into detector-edge pairs, including virtual-boundary edges, and compares them.

This specifically tests the mapping between PyMatching fault identifiers and Aegis `Edge` objects. It catches bugs where the matching result is correct but the reconstructed Aegis correction path is wrong.

## Reproducibility checklist

For any benchmark you plan to share, preserve the command line or API call, random seed, dependency versions, Aegis commit or release, input generation procedure, machine information, graph and weight policy, optional decoder settings, and raw output artifacts.

When comparing two decoders, feed them equivalent inputs and define the timed region before interpreting a speed ratio.

When reporting logical failure, state what supplied the physical errors, detector events, and logical ground truth.

When quoting sparse-blossom speedups, cite the upstream paper rather than presenting those numbers as measurements made by Aegis.
