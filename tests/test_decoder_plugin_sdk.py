from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from aegis_qec.decoder_plugins import (
    normalize_decoder_plugin,
    validate_decoder_plugin,
)

stim = pytest.importorskip("stim")


class _CompileOnlyCompiled:
    def __init__(self, num_observables: int):
        self.num_observables = int(num_observables)

    def decode_shots_bit_packed(
        self,
        *,
        bit_packed_detection_event_data: np.ndarray,
    ) -> np.ndarray:
        return np.asarray(
            bit_packed_detection_event_data[:, :1],
            dtype=np.uint8,
        )


class _CompileOnlyDecoder:
    def compile_decoder_for_dem(self, *, dem):
        return _CompileOnlyCompiled(dem.num_observables)


class _FileOnlyDecoder:
    def decode_via_files(
        self,
        *,
        num_shots: int,
        num_dets: int,
        num_obs: int,
        dem_path,
        dets_b8_in_path,
        obs_predictions_b8_out_path,
        tmp_dir,
    ) -> None:
        del num_dets, num_obs, dem_path, tmp_dir
        dets = np.fromfile(
            dets_b8_in_path,
            dtype=np.uint8,
            count=int(num_shots),
        ).reshape((int(num_shots), 1))
        dets.tofile(obs_predictions_b8_out_path)


def _known_dem():
    return stim.DetectorErrorModel(
        """
        error(0.1) D0 L0
        """
    )


def test_compile_only_plugin_gains_file_contract(tmp_path):
    decoder = normalize_decoder_plugin(
        "compile-only",
        _CompileOnlyDecoder(),
    )
    dem = _known_dem()
    dets = np.asarray([[0], [1], [1], [0]], dtype=np.uint8)

    dem_path = tmp_path / "model.dem"
    dets_path = tmp_path / "dets.b8"
    obs_path = tmp_path / "obs.b8"
    dem.to_file(dem_path)
    dets.tofile(dets_path)

    decoder.decode_via_files(
        num_shots=4,
        num_dets=1,
        num_obs=1,
        dem_path=dem_path,
        dets_b8_in_path=dets_path,
        obs_predictions_b8_out_path=obs_path,
        tmp_dir=tmp_path,
    )

    predictions = np.fromfile(obs_path, dtype=np.uint8).reshape((4, 1))
    np.testing.assert_array_equal(predictions, dets)


def test_file_only_plugin_gains_compiled_contract():
    decoder = normalize_decoder_plugin(
        "file-only",
        _FileOnlyDecoder(),
    )
    dem = _known_dem()
    dets = np.asarray([[0], [1], [0], [1]], dtype=np.uint8)

    compiled = decoder.compile_decoder_for_dem(dem=dem)
    predictions = compiled.decode_shots_bit_packed(
        bit_packed_detection_event_data=dets
    )
    np.testing.assert_array_equal(predictions, dets)


def test_adapter_rejects_wrong_compiled_dtype():
    class BadCompiled:
        def decode_shots_bit_packed(
            self,
            *,
            bit_packed_detection_event_data,
        ):
            return np.zeros(
                (bit_packed_detection_event_data.shape[0], 1),
                dtype=np.int64,
            )

    class BadDecoder:
        def compile_decoder_for_dem(self, *, dem):
            del dem
            return BadCompiled()

    decoder = normalize_decoder_plugin("bad", BadDecoder())
    with pytest.raises(ValueError, match="numpy.uint8"):
        decoder.compile_decoder_for_dem(
            dem=_known_dem()
        ).decode_shots_bit_packed(
            bit_packed_detection_event_data=np.zeros(
                (2, 1),
                dtype=np.uint8,
            )
        )


def test_adapter_rejects_wrong_file_output_size(tmp_path):
    class BadFileDecoder:
        def decode_via_files(self, **kwargs):
            Path(kwargs["obs_predictions_b8_out_path"]).write_bytes(b"")

    decoder = normalize_decoder_plugin("bad-file", BadFileDecoder())
    dem = _known_dem()
    dem_path = tmp_path / "model.dem"
    dets_path = tmp_path / "dets.b8"
    out_path = tmp_path / "out.b8"
    dem.to_file(dem_path)
    np.asarray([[0], [1]], dtype=np.uint8).tofile(dets_path)

    with pytest.raises(ValueError, match="prediction bytes"):
        decoder.decode_via_files(
            num_shots=2,
            num_dets=1,
            num_obs=1,
            dem_path=dem_path,
            dets_b8_in_path=dets_path,
            obs_predictions_b8_out_path=out_path,
            tmp_dir=tmp_path,
        )


def test_builtin_decoder_passes_conformance_suite():
    result = validate_decoder_plugin(
        "aegis-pymatching",
        include_external=False,
    )
    assert result["passed"] is True
    assert result["checks"]["compiled_batch"]["passed"] is True
    assert result["checks"]["file_roundtrip"]["passed"] is True
    assert result["checks"]["multiprocessing_pickle"]["passed"] is True


def test_inherited_unimplemented_compile_falls_back_to_file_contract():
    class FileDecoderWithStub(_FileOnlyDecoder):
        def compile_decoder_for_dem(self, *, dem):
            del dem
            raise NotImplementedError

    decoder = normalize_decoder_plugin(
        "file-with-stub",
        FileDecoderWithStub(),
    )
    dets = np.asarray([[0], [1], [1], [0]], dtype=np.uint8)
    predictions = decoder.compile_decoder_for_dem(
        dem=_known_dem()
    ).decode_shots_bit_packed(
        bit_packed_detection_event_data=dets
    )
    np.testing.assert_array_equal(predictions, dets)
