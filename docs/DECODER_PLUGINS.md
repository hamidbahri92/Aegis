# Decoder Plug-in SDK

Aegis QEC is designed to let decoder researchers bring a new algorithm into the same experiment, campaign, comparison, and file-prediction workflows without modifying Aegis itself.

## Registration

Publish a Python package with an entry point in the `aegis_qec.decoders` group:

```toml
[project.entry-points."aegis_qec.decoders"]
my-decoder = "my_decoder.plugin:MyDecoder"
```

After installation:

```bash
aegis decoders
aegis validate-decoder my-decoder
```

The validation command is intended to be run in the plug-in's own CI before publishing a release.

## Two accepted implementation styles

A plug-in may implement either Sinter's compiled batch interface or its file interface.

The preferred high-throughput form is:

```python
class MyCompiledDecoder:
    def decode_shots_bit_packed(
        self,
        *,
        bit_packed_detection_event_data,
    ):
        # Return numpy uint8 with one row per shot.
        ...


class MyDecoder:
    def compile_decoder_for_dem(self, *, dem):
        return MyCompiledDecoder(...)
```

A file-oriented implementation may instead provide:

```python
class MyDecoder:
    def decode_via_files(
        self,
        *,
        num_shots,
        num_dets,
        num_obs,
        dem_path,
        dets_b8_in_path,
        obs_predictions_b8_out_path,
        tmp_dir,
    ):
        ...
```

Aegis normalizes either form into both contracts. A compiled-only decoder can therefore be used by `aegis predict`, and a file-only decoder can participate in exact shared-shot comparisons.

## Binary contract

Detector events and observable predictions use Sinter's bit-packed convention:

- NumPy dtype is `uint8`;
- bits are little-endian within each byte;
- detector input shape is `(shots, ceil(num_detectors / 8))`;
- observable output shape is `(shots, ceil(num_observables / 8))`;
- the number of output rows must exactly equal the number of input shots.

Aegis validates these conditions at the plug-in boundary.

## Multiprocessing

Sinter campaigns send decoder objects to worker processes. The normalized plug-in object therefore needs to be pickle-serializable.

Keep persistent decoder configuration as ordinary serializable Python data. Construct non-serializable runtime state inside `compile_decoder_for_dem` instead of storing it on the plug-in object itself.

## Conformance testing

Run:

```bash
aegis validate-decoder my-decoder
```

or machine-readable output:

```bash
aegis validate-decoder my-decoder --json
```

The v1 conformance suite checks:

- multiprocessing picklability;
- compiled batch decoding;
- expected `uint8` dtype and bit-packed output shape;
- a known-answer detector-to-logical-observable relation;
- file-interface round trip.

The test detector error model contains one error mechanism coupling detector D0 to logical observable L0. The test shots are deterministic.

Passing this suite means the decoder satisfies Aegis's interoperability contract. It does not establish decoder accuracy on general QEC workloads.

## Using a plug-in

Once installed and validated:

```bash
aegis campaign \
  --distance 3 5 7 \
  --p 0.003 0.006 0.01 \
  --decoder my-decoder \
  --workers auto
```

For paired comparison on exactly the same detector samples:

```bash
aegis compare \
  --decoder aegis-pymatching my-decoder \
  --distance 5 \
  --p 0.006 \
  --shots 100000 \
  --seed 1234
```

For external detector data:

```bash
aegis predict \
  --dem experiment.dem \
  --dets detector-shots.b8 \
  --decoder my-decoder \
  --out predictions.b8
```

## Python API

Aegis exposes the compatibility layer directly:

```python
from aegis_qec import (
    DecoderPluginAdapter,
    normalize_decoder_plugin,
    validate_decoder_plugin,
)
```

`normalize_decoder_plugin(name, decoder)` is also useful while developing a decoder before packaging it as an entry point.

## Versioning

The current interoperability identifier is:

```text
aegis_qec.decoders/sinter-bit-packed-v1
```

Future incompatible decoder contracts should use a new identifier instead of silently changing the meaning of v1.
