from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .decoder_plugins import custom_decoder_registry


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def predict_observables_from_files(
    *,
    dem_path: str,
    dets_path: str,
    dets_format: str,
    output_path: str,
    output_format: str,
    decoder: str = "aegis-pymatching",
    provenance_json: str | None = None,
    include_external_plugins: bool = True,
) -> dict[str, Any]:
    """Decode standard Stim detector-shot files and preserve provenance."""

    try:
        import sinter
        import stim
    except ImportError as exc:
        raise RuntimeError(
            "File prediction requires Stim/Sinter. Install with: "
            "python -m pip install -U 'aegis-qec[full]'"
        ) from exc

    dem_file = Path(dem_path)
    dets_file = Path(dets_path)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    dem = stim.DetectorErrorModel.from_file(dem_file)
    registry = custom_decoder_registry(
        include_external=include_external_plugins
    )

    sinter.predict_on_disk(
        decoder=decoder,
        dem_path=dem_file,
        dets_path=dets_file,
        dets_format=dets_format,
        obs_out_path=out_file,
        obs_out_format=output_format,
        custom_decoders=registry,
    )

    result = {
        "schema_version": 1,
        "operation": "decode_detector_shot_file",
        "decoder": decoder,
        "dem_path": str(dem_file),
        "dets_path": str(dets_file),
        "dets_format": dets_format,
        "output_path": str(out_file),
        "output_format": output_format,
        "num_detectors": int(dem.num_detectors),
        "num_observables": int(dem.num_observables),
        "dem_sha256": _sha256_file(dem_file),
        "dets_sha256": _sha256_file(dets_file),
        "output_sha256": _sha256_file(out_file),
        "dets_bytes": int(os.path.getsize(dets_file)),
        "output_bytes": int(os.path.getsize(out_file)),
    }

    if provenance_json:
        provenance_path = Path(provenance_json)
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        with provenance_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")

    return result
