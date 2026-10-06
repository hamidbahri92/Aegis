from __future__ import annotations

import pickle
import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
import pymatching


def _require_stim():
    try:
        import stim
    except ImportError as exc:
        raise RuntimeError(
            "Decoder plug-in interoperability requires Stim. Install with: "
            "python -m pip install -U 'aegis-qec[full]'"
        ) from exc
    return stim


def _validate_predictions(
    predictions: Any,
    *,
    num_shots: int,
    num_observables: int,
    decoder_name: str,
) -> np.ndarray:
    array = np.asarray(predictions)
    expected_shape = (int(num_shots), (int(num_observables) + 7) // 8)
    if array.dtype != np.uint8:
        raise ValueError(
            f"Decoder {decoder_name!r} returned dtype={array.dtype}; "
            "bit-packed predictions must use numpy.uint8."
        )
    if array.shape != expected_shape:
        raise ValueError(
            f"Decoder {decoder_name!r} returned shape={array.shape}; "
            f"expected {expected_shape}."
        )
    return np.ascontiguousarray(array)


class _CompiledPyMatchingDecoder:
    """Compiled Sinter decoder backed by PyMatching sparse blossom."""

    def __init__(self, dem: Any, *, enable_correlations: bool):
        self.enable_correlations = bool(enable_correlations)
        self.num_observables = int(dem.num_observables)
        self.matching = pymatching.Matching.from_detector_error_model(
            dem,
            enable_correlations=self.enable_correlations,
        )

    def decode_shots_bit_packed(
        self,
        *,
        bit_packed_detection_event_data: np.ndarray,
    ) -> np.ndarray:
        result = self.matching.decode_batch(
            bit_packed_detection_event_data,
            bit_packed_shots=True,
            bit_packed_predictions=True,
            enable_correlations=self.enable_correlations,
        )
        return _validate_predictions(
            result,
            num_shots=bit_packed_detection_event_data.shape[0],
            num_observables=self.num_observables,
            decoder_name="aegis-pymatching",
        )


class AegisPyMatchingSinterDecoder:
    """Sinter-compatible decoder used by Aegis campaigns and file prediction."""

    def __init__(self, *, enable_correlations: bool = False):
        self.enable_correlations = bool(enable_correlations)

    def compile_decoder_for_dem(self, *, dem: Any) -> _CompiledPyMatchingDecoder:
        return _CompiledPyMatchingDecoder(
            dem,
            enable_correlations=self.enable_correlations,
        )

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
        del tmp_dir
        dem = _require_stim().DetectorErrorModel.from_file(dem_path)
        if int(dem.num_detectors) != int(num_dets):
            raise ValueError(
                f"DEM has {dem.num_detectors} detectors, expected {num_dets}."
            )
        if int(dem.num_observables) != int(num_obs):
            raise ValueError(
                f"DEM has {dem.num_observables} observables, expected {num_obs}."
            )

        num_det_bytes = (int(num_dets) + 7) // 8
        dets = np.fromfile(
            dets_b8_in_path,
            dtype=np.uint8,
            count=int(num_shots) * num_det_bytes,
        )
        dets = dets.reshape((int(num_shots), num_det_bytes))
        predictions = self.compile_decoder_for_dem(
            dem=dem
        ).decode_shots_bit_packed(
            bit_packed_detection_event_data=dets
        )
        predictions.tofile(obs_predictions_b8_out_path)


class _ValidatedCompiledDecoder:
    """Checks a third-party compiled decoder at the Aegis boundary."""

    def __init__(
        self,
        compiled: Any,
        *,
        decoder_name: str,
        num_observables: int,
    ):
        self.compiled = compiled
        self.decoder_name = str(decoder_name)
        self.num_observables = int(num_observables)

    def decode_shots_bit_packed(
        self,
        *,
        bit_packed_detection_event_data: np.ndarray,
    ) -> np.ndarray:
        dets = np.asarray(bit_packed_detection_event_data, dtype=np.uint8)
        result = self.compiled.decode_shots_bit_packed(
            bit_packed_detection_event_data=dets
        )
        return _validate_predictions(
            result,
            num_shots=dets.shape[0],
            num_observables=self.num_observables,
            decoder_name=self.decoder_name,
        )


class _FileBackedCompiledDecoder:
    """Expose a file-only Sinter decoder through the compiled batch contract."""

    def __init__(
        self,
        decoder: Any,
        *,
        decoder_name: str,
        dem_text: str,
        num_detectors: int,
        num_observables: int,
    ):
        self.decoder = decoder
        self.decoder_name = str(decoder_name)
        self.dem_text = str(dem_text)
        self.num_detectors = int(num_detectors)
        self.num_observables = int(num_observables)

    def decode_shots_bit_packed(
        self,
        *,
        bit_packed_detection_event_data: np.ndarray,
    ) -> np.ndarray:
        dets = np.asarray(bit_packed_detection_event_data, dtype=np.uint8)
        expected_det_bytes = (self.num_detectors + 7) // 8
        if dets.ndim != 2 or dets.shape[1] != expected_det_bytes:
            raise ValueError(
                f"Decoder {self.decoder_name!r} received detector data with "
                f"shape={dets.shape}; expected (*, {expected_det_bytes})."
            )

        num_shots = int(dets.shape[0])
        num_obs_bytes = (self.num_observables + 7) // 8
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_dir = Path(raw_tmp)
            dem_path = tmp_dir / "model.dem"
            dets_path = tmp_dir / "dets.b8"
            obs_path = tmp_dir / "predictions.b8"
            dem_path.write_text(self.dem_text, encoding="utf-8")
            dets.tofile(dets_path)

            self.decoder.decode_via_files(
                num_shots=num_shots,
                num_dets=self.num_detectors,
                num_obs=self.num_observables,
                dem_path=dem_path,
                dets_b8_in_path=dets_path,
                obs_predictions_b8_out_path=obs_path,
                tmp_dir=tmp_dir,
            )
            predictions = np.fromfile(
                obs_path,
                dtype=np.uint8,
                count=num_shots * num_obs_bytes,
            ).reshape((num_shots, num_obs_bytes))

        return _validate_predictions(
            predictions,
            num_shots=num_shots,
            num_observables=self.num_observables,
            decoder_name=self.decoder_name,
        )


class DecoderPluginAdapter:
    """Normalize third-party Sinter decoders across all Aegis workflows."""

    def __init__(self, name: str, decoder: Any):
        self.name = str(name)
        self.decoder = decoder
        self.has_compile = callable(
            getattr(decoder, "compile_decoder_for_dem", None)
        )
        self.has_file = callable(getattr(decoder, "decode_via_files", None))
        if not self.has_compile and not self.has_file:
            raise TypeError(
                f"Decoder plugin {self.name!r} must implement "
                "compile_decoder_for_dem or decode_via_files."
            )

    def compile_decoder_for_dem(self, *, dem: Any):
        if self.has_compile:
            try:
                compiled = self.decoder.compile_decoder_for_dem(dem=dem)
            except NotImplementedError:
                compiled = None
            if compiled is not None:
                if not callable(
                    getattr(compiled, "decode_shots_bit_packed", None)
                ):
                    raise TypeError(
                        f"Decoder plugin {self.name!r} returned a compiled object "
                        "without decode_shots_bit_packed."
                    )
                return _ValidatedCompiledDecoder(
                    compiled,
                    decoder_name=self.name,
                    num_observables=int(dem.num_observables),
                )

        if not self.has_file:
            raise NotImplementedError(
                f"Decoder plugin {self.name!r} has no usable compiled or file decoder."
            )

        return _FileBackedCompiledDecoder(
            self.decoder,
            decoder_name=self.name,
            dem_text=str(dem),
            num_detectors=int(dem.num_detectors),
            num_observables=int(dem.num_observables),
        )

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
        if self.has_file:
            self.decoder.decode_via_files(
                num_shots=num_shots,
                num_dets=num_dets,
                num_obs=num_obs,
                dem_path=dem_path,
                dets_b8_in_path=dets_b8_in_path,
                obs_predictions_b8_out_path=obs_predictions_b8_out_path,
                tmp_dir=tmp_dir,
            )
            expected_bytes = int(num_shots) * ((int(num_obs) + 7) // 8)
            actual_bytes = Path(obs_predictions_b8_out_path).stat().st_size
            if actual_bytes != expected_bytes:
                raise ValueError(
                    f"Decoder plugin {self.name!r} wrote {actual_bytes} "
                    f"prediction bytes; expected {expected_bytes}."
                )
            return

        stim = _require_stim()
        dem = stim.DetectorErrorModel.from_file(dem_path)
        if int(dem.num_detectors) != int(num_dets):
            raise ValueError(
                f"DEM has {dem.num_detectors} detectors, expected {num_dets}."
            )
        if int(dem.num_observables) != int(num_obs):
            raise ValueError(
                f"DEM has {dem.num_observables} observables, expected {num_obs}."
            )
        num_det_bytes = (int(num_dets) + 7) // 8
        dets = np.fromfile(
            dets_b8_in_path,
            dtype=np.uint8,
            count=int(num_shots) * num_det_bytes,
        ).reshape((int(num_shots), num_det_bytes))
        predictions = self.compile_decoder_for_dem(
            dem=dem
        ).decode_shots_bit_packed(
            bit_packed_detection_event_data=dets
        )
        predictions.tofile(obs_predictions_b8_out_path)


def normalize_decoder_plugin(name: str, decoder: Any) -> DecoderPluginAdapter:
    """Return one decoder object that works across all Aegis research paths."""
    if isinstance(decoder, DecoderPluginAdapter):
        return decoder
    return DecoderPluginAdapter(name, decoder)


def builtin_custom_decoders() -> dict[str, Any]:
    """Return Aegis-provided Sinter custom decoders."""
    return {
        "aegis-pymatching": normalize_decoder_plugin(
            "aegis-pymatching",
            AegisPyMatchingSinterDecoder(enable_correlations=False),
        ),
        "aegis-pymatching-correlated": normalize_decoder_plugin(
            "aegis-pymatching-correlated",
            AegisPyMatchingSinterDecoder(enable_correlations=True),
        ),
    }


def _entry_points_for_group(group: str):
    points = metadata.entry_points()
    if hasattr(points, "select"):
        return list(points.select(group=group))
    return list(points.get(group, ()))


def external_decoder_plugins() -> dict[str, Any]:
    """Load and normalize third-party decoders from aegis_qec.decoders."""
    result: dict[str, Any] = {}
    for entry_point in _entry_points_for_group("aegis_qec.decoders"):
        loaded = entry_point.load()
        candidate = loaded
        if isinstance(loaded, type):
            candidate = loaded()
        elif callable(loaded) and not hasattr(
            loaded,
            "compile_decoder_for_dem",
        ) and not hasattr(loaded, "decode_via_files"):
            candidate = loaded()
        result[entry_point.name] = normalize_decoder_plugin(
            entry_point.name,
            candidate,
        )
    return result


def custom_decoder_registry(*, include_external: bool = True) -> dict[str, Any]:
    """Return built-in and installed third-party custom decoders."""
    result = builtin_custom_decoders()
    if include_external:
        for name, decoder in external_decoder_plugins().items():
            if name in result:
                raise ValueError(
                    f"Decoder plugin name {name!r} conflicts with an Aegis decoder."
                )
            result[name] = decoder
    return result


def available_decoders(*, include_external: bool = True) -> list[str]:
    """List Aegis custom decoder names usable by the campaign engine."""
    return sorted(custom_decoder_registry(include_external=include_external))


def validate_decoder_plugin(
    name: str,
    *,
    include_external: bool = True,
) -> dict[str, Any]:
    """Exercise the Aegis/Sinter decoder contract on a known-answer DEM."""

    stim = _require_stim()
    registry = custom_decoder_registry(
        include_external=include_external,
    )
    if name not in registry:
        raise ValueError(
            f"Unknown decoder plugin {name!r}. Available: "
            + ", ".join(sorted(registry))
        )

    decoder = registry[name]
    dem = stim.DetectorErrorModel(
        """
        error(0.1) D0 L0
        """
    )
    dets = np.asarray([[0], [1], [1], [0]], dtype=np.uint8)
    expected = dets.copy()

    checks: dict[str, dict[str, Any]] = {}

    try:
        pickle.dumps(decoder)
        checks["multiprocessing_pickle"] = {"passed": True}
    except Exception as exc:
        checks["multiprocessing_pickle"] = {
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        compiled = decoder.compile_decoder_for_dem(dem=dem)
        predicted = compiled.decode_shots_bit_packed(
            bit_packed_detection_event_data=dets
        )
        checks["compiled_batch"] = {
            "passed": bool(np.array_equal(predicted, expected)),
            "dtype": str(predicted.dtype),
            "shape": list(predicted.shape),
        }
    except Exception as exc:
        checks["compiled_batch"] = {
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_dir = Path(raw_tmp)
            dem_path = tmp_dir / "model.dem"
            dets_path = tmp_dir / "dets.b8"
            obs_path = tmp_dir / "obs.b8"
            dem.to_file(dem_path)
            dets.tofile(dets_path)
            decoder.decode_via_files(
                num_shots=dets.shape[0],
                num_dets=int(dem.num_detectors),
                num_obs=int(dem.num_observables),
                dem_path=dem_path,
                dets_b8_in_path=dets_path,
                obs_predictions_b8_out_path=obs_path,
                tmp_dir=tmp_dir,
            )
            file_predictions = np.fromfile(
                obs_path,
                dtype=np.uint8,
            ).reshape(expected.shape)
        checks["file_roundtrip"] = {
            "passed": bool(np.array_equal(file_predictions, expected)),
            "bytes": int(file_predictions.nbytes),
        }
    except Exception as exc:
        checks["file_roundtrip"] = {
            "passed": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    passed = all(check.get("passed", False) for check in checks.values())
    return {
        "schema_version": 1,
        "decoder": name,
        "contract": "aegis_qec.decoders/sinter-bit-packed-v1",
        "passed": passed,
        "checks": checks,
        "requirements": {
            "detector_input_dtype": "uint8",
            "observable_output_dtype": "uint8",
            "bit_order": "little",
            "multiprocessing_picklable": True,
        },
    }
