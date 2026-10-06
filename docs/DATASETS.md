# Reusable QEC datasets

Aegis QEC can generate reusable HDF5 syndrome datasets for decoder benchmarking, machine-learning experiments, coursework, and team regression studies.

The goal is simple: sample an experiment once, preserve enough provenance to understand exactly what was sampled, and let many decoder implementations evaluate the same evidence.

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

## Python API

```python
from aegis_qec import generate_qec_dataset, inspect_qec_dataset

report = generate_qec_dataset(
    "surface-d5.h5",
    shots=100000,
    distance=5,
    physical_error_rate=0.006,
    seed=1234,
)

inspection = inspect_qec_dataset("surface-d5.h5")
assert inspection["valid"]
```

The lower-level `extract_dem_mechanisms` function is public for researchers who want Aegis's sparse raw-DEM incidence representation without generating samples.

## Interpretation boundary

A valid dataset proves that the stored sample arrays are internally consistent with their recorded hashes and metadata. It does not prove that a selected physical noise model is a faithful model of a particular quantum device, nor that a decoder trained on the dataset generalizes outside the sampled distribution.

For published comparisons, preserve the HDF5 dataset, Aegis version or commit, and the decoder versions evaluated against it.
