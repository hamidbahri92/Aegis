# Aegis QEC Platform

Aegis QEC now separates three research modes so users can choose the right evidence model instead of treating every experiment as equivalent.

## Deterministic studies

Use `aegis study` when you want a compact, deterministic circuit-level experiment with a fixed seed and a complete JSON, CSV, and plot artifact set.

This path is useful for teaching, notebooks, regression tests, and small reproducible studies.

## Resumable campaigns

Use `aegis campaign` when you need large Monte Carlo campaigns across many code distances, error rates, or decoder implementations.

The campaign engine delegates sampling and worker scheduling to Sinter. This gives Aegis:

- multiprocessing across CPU cores;
- per-task cryptographic strong IDs;
- incremental durable CSV results;
- automatic resume after interruption;
- global shot limits;
- error-count stopping conditions;
- detection-event accounting;
- adaptive batch sizing;
- built-in Sinter decoders plus Aegis and third-party decoders.

Example:

```bash
aegis campaign \
  --distance 3 5 7 \
  --p 0.003 0.006 0.01 \
  --decoder pymatching aegis-pymatching \
  --workers auto \
  --max-shots 1000000 \
  --max-errors 1000 \
  --resume research_out/campaign.csv
```

Running the same command again with the same resume file continues from the durable statistics already present in the CSV.

A campaign can also use an existing Stim circuit:

```bash
aegis campaign \
  --circuit my_experiment.stim \
  --decoder pymatching aegis-pymatching \
  --workers auto \
  --max-shots 1000000 \
  --max-errors 1000
```

Generated tasks include circuit and detector-error-model SHA-256 hashes in their metadata.

## Exact shared-shot decoder comparison

Large Sinter campaigns compare statistical populations. They do not promise that two decoder rows saw the same random shots.

When a paired comparison matters, use `aegis compare`:

```bash
aegis compare \
  --decoder aegis-pymatching aegis-pymatching-correlated \
  --distance 5 \
  --p 0.006 \
  --shots 100000 \
  --seed 1234
```

Every decoder receives the exact same bit-packed detector-shot matrix. The result records:

- logical errors and confidence intervals for each decoder;
- throughput for each decoder;
- pairwise prediction disagreement counts;
- circuit and detector-error-model hashes;
- detector-sample and observable-sample hashes.

This makes decoder differences paired and directly inspectable.

## Decoder plug-ins

Aegis exposes decoder extension through the Python entry-point group:

```text
aegis_qec.decoders
```

A plug-in may provide a Sinter-compatible decoder instance, decoder class, or zero-argument factory. The object must implement `compile_decoder_for_dem` or the legacy Sinter `decode_via_files` contract.

A minimal package can declare:

```toml
[project.entry-points."aegis_qec.decoders"]
my-decoder = "my_package.decoder:MyDecoder"
```

The decoder can then appear in:

```bash
aegis decoders
```

and can be selected by name in `aegis campaign` or `aegis compare`.

For efficient exact-shot and Sinter use, implement a compiled decoder with:

```python
class MyCompiledDecoder:
    def decode_shots_bit_packed(
        self,
        *,
        bit_packed_detection_event_data,
    ):
        ...
```

and a factory object with:

```python
class MyDecoder:
    def compile_decoder_for_dem(self, *, dem):
        return MyCompiledDecoder(...)
```

Detection-event input and observable predictions follow Sinter's little-endian bit-packed contract.

## Statistical scaling analysis

Campaign collection and threshold-like interpretation are separate operations. After collecting a sufficiently dense campaign, use:

```bash
aegis scaling --campaign research_out/campaign.json --decoder pymatching
```

Aegis fits the aggregated binomial logical-failure counts to a first-order finite-size scaling model and profiles the critical physical-error probability over the scaling exponent. It also compares the scaling model with a distance-independent logistic trend using AIC.

The analysis fails on obviously underdetermined inputs, requires at least three code distances and four physical-error points, and warns when fitted parameters or confidence intervals reach the sampled/search boundaries.

This does not turn simulated evidence into hardware evidence. The provenance of the campaign still determines what kind of claim the fit can support.

## External detector-shot data

Aegis can decode standard Stim detector-event files without generating the circuit itself:

```bash
aegis predict \
  --dem experiment.dem \
  --dets detector_shots.b8 \
  --dets-format b8 \
  --decoder aegis-pymatching \
  --out observable_predictions.b8 \
  --out-format b8
```

The prediction provenance artifact hashes the detector error model, detector-shot input, and observable-prediction output. This is the intended bridge for external simulators and hardware pipelines that already produce detector events.

Stim-supported result formats can be selected with `--dets-format` and `--out-format`.

## Hardware provenance

Hardware-derived research must never silently become simulated research.

`IBMQuantumInterface` therefore fails closed when an IBM backend cannot be reached or its calibration cannot be parsed. Synthetic fallback is available only when `allow_synthetic_fallback=True` is explicitly requested.

Every returned calibration object identifies its source, backend name, and whether it is synthetic. Cached real calibration is also marked as cached.

The generic `QuantumHardwareInterface` remains an explicitly synthetic simulator.

## Repository discovery settings

The desired public GitHub settings are stored in:

```text
.github/repository-settings.json
```

This file is intentionally declarative because repository name, Topics, homepage, and Discussions are GitHub administration state and cannot be changed by a pull request.

The intended automation path is to have an authenticated browser or repository-administration integration read that file and apply it. This avoids maintaining those values manually in multiple places.

## Experiment manifests and evidence bundles

The platform layer also provides a versioned JSON experiment contract. This separates experiment intent from an interactive shell command and gives teams a stable unit for code review and CI.

`aegis experiment` dispatches the manifest to the existing study, campaign, comparison, prediction, scaling, or explanation engines. It records input and output hashes plus environment metadata and emits a tamper-evident research bundle.

`aegis verify-bundle` validates that bundle without extracting it.

See [Experiments](EXPERIMENTS.md) for the full contract.

## Trust boundaries

Aegis owns experiment definition, provenance, plug-in discovery, comparison semantics, artifact generation, and user-facing workflows.

Stim owns stabilizer-circuit simulation and detector-event generation.

Sinter owns high-throughput local Monte Carlo collection and worker scheduling.

PyMatching owns sparse-blossom MWPM.

Aegis should integrate these projects rather than hide or reimplement their strongest components.
