# Benchmarking Aegis QEC

Aegis QEC uses several kinds of performance evidence. They answer different questions and must not be quoted as if they were interchangeable.

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

When publishing or comparing these measurements, report at least the Aegis version, PyMatching version, Python version, operating system, CPU, decoder, code distance, number of rounds, sample count, and whether any optional reweighting or polishing was enabled.

These timings should be described as **Aegis end-to-end latency**, not as a reproduction of PyMatching's NetworkX comparison.

## Correction-validation sweep

`aegis-bench sweep` generates deterministic synthetic detection-event patterns and checks whether the produced correction satisfies Aegis's correction-validation rules.

Its CSV column is named `validation_failure_rate`.

This experiment is useful for software regression testing and comparing decoder behavior under a controlled synthetic input generator. It is **not** a circuit-level logical-error-rate measurement because the synthetic event generator does not model a complete quantum circuit, decoded observables, and residual physical error chain.

Example:

```bash
aegis-bench sweep --decoder mwpm --p 0.01 0.02 0.04 --distance 5 --rounds 6 --trials 200
```

## Circuit-level logical-error studies

A publishable circuit-level logical-error-rate study should define a physical circuit or detector error model, sample observed detector events and logical observables, decode those observations, and compare predicted observables against ground truth.

Aegis already includes Stim/DEM interoperability, but the current convenience sweep command is deliberately not labeled as this stronger experiment.

## Reproducibility rules

Performance reports should keep the following boundaries explicit.

Do not use the upstream greater-than-100,000-times result as an Aegis end-to-end number.

Do not call the correction-validation sweep a circuit-level logical-error-rate benchmark.

Do not compare two latency numbers without identifying the workload and timed region.

Do record dependency versions and hardware.

Do preserve the random seed or input corpus when a benchmark uses generated data.

These rules are part of the Aegis QEC evidence policy, not merely documentation style.
