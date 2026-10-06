# Reusable QEC datasets

Aegis QEC can generate reusable HDF5 syndrome datasets for decoder benchmarking, machine-learning experiments, coursework, and team regression studies.

The goal is simple: sample an experiment once, preserve enough provenance to understand exactly what was sampled, and let many decoder implementations evaluate the same evidence.

## Import hardware or external shot data

Aegis can ingest existing Stim-compatible detector and logical-observable shot data into the same HDF5 evidence format used by generated datasets.

For a single `dets` file containing detector and logical-observable records:

```bash
aegis dataset import \
  --dem experiment.dem \
  --shots hardware-shots.dets \
  --format dets \
  --out research_out/hardware.h5
```

For separate bit-packed detector and observable streams:

```bash
aegis dataset import \
  --dem experiment.dem \
  --shots detectors.b8 \
  --observables observables.b8 \
  --format b8 \
  --out research_out/hardware.h5
```

The imported HDF5 records SHA-256 values for the source DEM and shot files, the imported shot format, deterministic train/validation/test labels, the DEM mechanism representation, and the same scientific-content hashes used by generated datasets.

Bit-packed `b8` import is streamed in bounded chunks instead of materializing the entire shot corpus in memory. Other Stim shot formats are parsed through Stim's own shot-data reader.

Imported dataset files are immutable: Aegis refuses to overwrite an existing output path.

The provided DEM must describe the detector and logical-observable indexing used by the shot data. Aegis verifies structural consistency and file integrity, but it cannot infer whether a hardware calibration, detector mapping, or experimental labeling convention is scientifically correct.

After import, the ordinary evaluator works unchanged:

```bash
aegis dataset inspect research_out/hardware.h5
aegis dataset evaluate research_out/hardware.h5 \
  --decoder aegis-pymatching my-decoder \
  --split test
```

This is the preferred path for bringing device-derived or external-simulator evidence into the Aegis comparison and publication pipeline.

## Generate a dataset

```bash
aegis dataset generate \
  --out research_out/surface-d5-p006.h5 \
  --distance 5 \
  --p 0.006 \
  --basis x \
  --shots 1000000 \
  --seed 1234 \
  --chunk-size 50000
```

For a user-supplied Stim circuit:

```bash
aegis dataset generate \
  --out research_out/hardware-model.h5 \
  --circuit experiment.stim \
  --shots 1000000 \
  --seed 1234
```

Inspect and verify a completed file:

```bash
aegis dataset inspect research_out/surface-d5-p006.h5
```

Use `--json` on either command for machine-readable output.

## Durable resume

Dataset generation is chunked. To deliberately bound one invocation:

```bash
aegis dataset generate \
  --out research_out/large.h5 \
  --distance 7 \
  --p 0.006 \
  --shots 100000000 \
  --chunk-size 100000 \
  --max-chunks-per-run 10
```

Run the same command again to continue.

The dataset identity binds the circuit, raw detector error model, target shot count, seed, chunk size, and split fractions. A resume request with a different identity is rejected instead of silently appending incompatible samples.

Each sampling chunk has a deterministic seed derived from the dataset seed and chunk index. A fully resumed dataset therefore produces the same syndrome, observable, and split hashes as a one-shot generation with the same configuration.

If a process dies after creating inconsistent HDF5 row counts, Aegis refuses to continue rather than guessing how to repair the file.

## Train, validation, and test splits

Every row receives a deterministic split label:

- zero is training;
- one is validation;
- two is test.

The defaults are eighty percent training, ten percent validation, and ten percent test.

The split assignment is independent of detector values and is deterministic for a fixed dataset seed and chunk index. Aegis stores and verifies a SHA-256 over the complete split vector when generation finishes.

## HDF5 structure

The v1 format identifier is:

```text
aegis-qec-dataset-v1
```

Core datasets are:

```text
syndromes
observables
split
circuit
detector_error_model
decoding_detector_error_model
metadata_json
priors
error_mechanisms/probabilities
error_mechanisms/detector_indices
error_mechanisms/detector_indptr
error_mechanisms/observable_indices
error_mechanisms/observable_indptr
```

When the dense matrices fit under the configured cell limit, Aegis also writes:

```text
check_matrix
obs_matrix
```

The core field names `syndromes`, `observables`, `check_matrix`, `obs_matrix`, `priors`, and `circuit` intentionally follow conventions already used by decoder-research dataset tooling. Aegis does not claim that every third-party HDF5 dataset is schema-compatible; consumers should inspect metadata and matrix semantics before assuming interchangeability.

## Error-mechanism representation

The raw Stim detector error model is preserved verbatim and hashed.

For every raw DEM error instruction, Aegis stores:

- the error probability;
- detector indices toggled by the mechanism;
- logical observable indices toggled by the mechanism.

The sparse representation uses CSR-style `indices` and `indptr` arrays. It preserves arbitrary detector hyperedges instead of assuming that every mechanism is graphlike.

Separator targets in a decomposed DEM are decomposition hints. The v1 mechanism export records the XOR effect of the complete error instruction.

Aegis also tries to preserve a decomposed detector error model for matching-oriented consumers. If Stim cannot decompose the model, the raw model remains authoritative and the decomposed-model field is empty.

## Dense matrices

When enabled, `check_matrix` has shape:

```text
number of detectors by number of error mechanisms
```

`obs_matrix` has shape:

```text
number of logical observables by number of error mechanisms
```

A one means that the corresponding error mechanism toggles that detector or logical observable.

Large experiments can disable dense matrices:

```bash
aegis dataset generate \
  --out research_out/large.h5 \
  --dense-matrix-max-cells 0 \
  ...
```

The sparse mechanism arrays remain available.

## Integrity

A completed dataset stores SHA-256 values over canonical little-endian bit-packed syndrome rows, observable rows, and split labels.

`aegis dataset inspect` recomputes these hashes in bounded-memory chunks and reports any mismatch.

The HDF5 file itself is also hashed in command output, but the internal sample hashes are the stable evidence identifiers for the sampled arrays. HDF5 container bytes can differ because of metadata or layout even when scientific content is identical.

## Evaluate decoders on a fixed dataset

Once a dataset exists, compare decoders without resampling the experiment:

```bash
aegis dataset evaluate research_out/surface-d5-p006.h5 \
  --decoder aegis-pymatching aegis-pymatching-correlated \
  --split test \
  --out-json research_out/dataset-evaluation.json
```

Every decoder receives the identical selected rows in the identical order. The evaluation artifact records SHA-256 values for the exact selected detector and observable rows, logical-error rates with Wilson intervals, decode throughput, and pairwise prediction disagreement.

For every decoder pair, Aegis also records the four paired logical-outcome cells: both succeed, left-only failure, right-only failure, and both fail. From those counts it reports the left-minus-right logical-error-rate difference with a normal-approximation 95 percent interval and a continuity-corrected asymptotic McNemar p-value.

A negative left-minus-right difference means the left decoder failed on fewer of the shared shots. McNemar tests only the discordant failure outcomes and is appropriate because both decoders are evaluated on the same observations.

The risk-difference interval and McNemar p-value are inferential summaries, not proof of superiority outside the sampled dataset. Report the dataset identity, selected-row hashes, split, decoder versions, effect size, and uncertainty together.

Use `--split train`, `--split validation`, `--split test`, or `--split all`. `--max-shots` can bound a quick comparison without changing which rows are selected first from that split.

By default Aegis verifies a completed dataset before evaluation. `--no-verify` skips that full preflight when the dataset has already been verified in the surrounding workflow.

This workflow is especially useful when benchmarking new decoder plug-ins: differences cannot be attributed to independent Monte Carlo samples because the detector rows are fixed.

## Python API

```python
from aegis_qec import (
    evaluate_decoders_on_dataset,
    generate_qec_dataset,
    inspect_qec_dataset,
)

report = generate_qec_dataset(
    "surface-d5.h5",
    shots=100000,
    distance=5,
    physical_error_rate=0.006,
    seed=1234,
)

inspection = inspect_qec_dataset("surface-d5.h5")
assert inspection["valid"]

comparison = evaluate_decoders_on_dataset(
    "surface-d5.h5",
    decoders=["aegis-pymatching"],
    split_name="test",
)
```

The lower-level `extract_dem_mechanisms` function is public for researchers who want Aegis's sparse raw-DEM incidence representation without generating samples.

## Interpretation boundary

A valid dataset proves that the stored sample arrays are internally consistent with their recorded hashes and metadata. It does not prove that a selected physical noise model is a faithful model of a particular quantum device, nor that a decoder trained on the dataset generalizes outside the sampled distribution.

For published comparisons, preserve the HDF5 dataset, Aegis version or commit, and the decoder versions evaluated against it.
