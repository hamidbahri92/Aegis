from __future__ import annotations

from importlib import metadata
from typing import Any

import numpy as np
import pymatching


class _CompiledPyMatchingDecoder:
    """Compiled Sinter decoder backed by PyMatching sparse blossom."""

    def __init__(self, dem: Any, *, enable_correlations: bool):
        self.enable_correlations = bool(enable_correlations)
        self.matching = pymatching.Matching.from_detector_error_model(
            dem,
            enable_correlations=self.enable_correlations,
        )

    def decode_shots_bit_packed(
        self,
        *,
        bit_packed_detection_event_data: np.ndarray,
    ) -> np.ndarray:
        return self.matching.decode_batch(
            bit_packed_detection_event_data,
            bit_packed_shots=True,
            bit_packed_predictions=True,
            enable_correlations=self.enable_correlations,
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
        """Implement Sinter's file decoder contract using the compiled path."""
        del tmp_dir
        try:
            import stim
        except ImportError as exc:
            raise RuntimeError(
                "File decoding requires Stim. Install with: "
                "python -m pip install -U 'aegis-qec[full]'"
            ) from exc

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
        )
        dets = dets.reshape((int(num_shots), num_det_bytes))
        compiled = self.compile_decoder_for_dem(dem=dem)
        predictions = compiled.decode_shots_bit_packed(
            bit_packed_detection_event_data=dets
        )

        expected_shape = (int(num_shots), (int(num_obs) + 7) // 8)
        if predictions.dtype != np.uint8 or predictions.shape != expected_shape:
            raise ValueError(
                f"Decoder returned dtype={predictions.dtype}, "
                f"shape={predictions.shape}; expected uint8 {expected_shape}."
            )
        predictions.tofile(obs_predictions_b8_out_path)


def builtin_custom_decoders() -> dict[str, Any]:
    """Return Aegis-provided Sinter custom decoders."""
    return {
        "aegis-pymatching": AegisPyMatchingSinterDecoder(
            enable_correlations=False
        ),
        "aegis-pymatching-correlated": AegisPyMatchingSinterDecoder(
            enable_correlations=True
        ),
    }


def _entry_points_for_group(group: str):
    points = metadata.entry_points()
    if hasattr(points, "select"):
        return list(points.select(group=group))
    return list(points.get(group, ()))


def external_decoder_plugins() -> dict[str, Any]:
    """Load third-party decoders from the aegis_qec.decoders entry point group."""
    result: dict[str, Any] = {}
    for entry_point in _entry_points_for_group("aegis_qec.decoders"):
        loaded = entry_point.load()
        candidate = loaded
        if isinstance(loaded, type):
            candidate = loaded()
        elif callable(loaded) and not hasattr(loaded, "compile_decoder_for_dem"):
            candidate = loaded()
        if not hasattr(candidate, "compile_decoder_for_dem") and not hasattr(
            candidate,
            "decode_via_files",
        ):
            raise TypeError(
                f"Decoder plugin {entry_point.name!r} does not implement the "
                "Sinter decoder contract."
            )
        result[entry_point.name] = candidate
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
