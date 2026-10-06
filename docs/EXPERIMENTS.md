# Version-controlled experiments and research bundles

Aegis QEC experiment manifests turn an interactive command into a file that can be reviewed, committed to Git, rerun in CI, and handed to another researcher.

A manifest is JSON with a schema version, an operation, parameters, and optional output names.

## Start from a packaged template

A normal PyPI installation includes curated experiment manifests. List them with:

```bash
aegis templates
```

Create an editable copy:

```bash
aegis init-experiment first-study --out experiment.json
aegis experiment experiment.json
```

The catalog includes beginner learning paths, an exact-shot decoder comparison, a resumable finite-size-scaling campaign, and a compact practitioner regression campaign. Templates are ordinary version-1 manifests after materialization, so they can be edited, committed, reviewed, and bundled like any other experiment.

The template files are packaged inside the `aegis-qec` wheel; cloning the GitHub repository is not required.

## Small circuit study

```json
{
  "$schema": "../schemas/experiment-v1.schema.json",
  "schema_version": 1,
  "name": "surface-code-class-project",
  "operation": "study",
  "parameters": {
    "distances": [3, 5, 7],
    "physical_error_rates": [0.003, 0.006, 0.01],
    "shots": 5000,
    "basis": "x",
    "seed": 1234
  }
}
```

Run it with:

```bash
aegis experiment examples/experiment-study.json
```

Aegis writes the normal study artifacts, an `aegis-run.json` record, and a `.aegis.zip` research bundle.

## Supported operations

Manifest version 1 supports:

- `study` for deterministic local circuit studies;
- `campaign` for resumable Sinter Monte Carlo campaigns;
- `compare` for exact shared-shot decoder comparisons;
- `predict` for DEM plus detector-shot file decoding;
- `scaling` for finite-size scaling analysis of campaign JSON;
- `explain` for one-shot educational and debugging explanations.

Relative input paths are resolved relative to the manifest file. Relative output paths are resolved inside the experiment output directory.

## Run record

Every manifest execution creates `aegis-run.json`. It records:

- the manifest SHA-256;
- operation and experiment name;
- Python and platform information;
- Aegis, Stim, Sinter, PyMatching, NumPy, SciPy, and Matplotlib versions when installed;
- GitHub commit SHA when available in CI;
- hashes and sizes of local input artifacts;
- hashes and sizes of generated artifacts;
- the machine-readable operation result.

This creates a durable link between the reviewed experiment definition and the evidence it produced.

## Research bundle

The generated `.aegis.zip` bundle contains the exact manifest, exact on-disk run record, local input files used by the manifest, generated result artifacts, and `BUNDLE_MANIFEST.json`.

Every payload entry has a SHA-256 and byte count.

Verify a received bundle without extracting it:

```bash
aegis verify-bundle surface-code-class-project.aegis.zip
```

Verification fails if a listed file is missing, its size or hash changed, an unsafe path is present, or an unexpected file was inserted.

The bundle is an evidence container, not a claim that the scientific interpretation is correct. A valid bundle proves internal integrity of the packaged experiment files; it does not independently validate the model, decoder, hardware source, or statistical assumptions.

## Team workflow

A useful team pattern is:

1. commit the experiment JSON beside the analysis code;
2. review changes to parameters in a pull request;
3. run `aegis experiment` in CI or on a workstation;
4. archive the resulting `.aegis.zip` bundle;
5. verify the bundle before analysis or publication;
6. cite the Aegis version and preserve the bundle with the project record.

This makes research configuration reviewable in the same way source code is reviewable.

## Python API

```python
from aegis_qec import (
    create_research_bundle,
    run_experiment_manifest,
    verify_research_bundle,
)

run = run_experiment_manifest(
    "experiment.json",
    output_dir="research_out/my-run",
)

bundle = create_research_bundle(
    manifest_path="experiment.json",
    run_record=run,
    bundle_path="research_out/my-run.aegis.zip",
)

assert verify_research_bundle(bundle["path"])["valid"]
```
