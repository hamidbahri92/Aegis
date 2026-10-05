from __future__ import annotations

import json

import numpy as np
import pytest

stim = pytest.importorskip("stim")
pytest.importorskip("sinter")

from aegis_qec.io_decode import predict_observables_from_files


def test_predict_observables_from_standard_files(tmp_path):
    dem = stim.DetectorErrorModel(
        """
        error(0.1) D0 L0
        """
    )
    dem_path = tmp_path / "model.dem"
    dets_path = tmp_path / "shots.b8"
    out_path = tmp_path / "predictions.b8"
    provenance_path = tmp_path / "provenance.json"

    dem.to_file(dem_path)
    dets = np.array([[0], [1], [1], [0]], dtype=np.uint8)
    stim.write_shot_data_file(
        data=dets,
        path=str(dets_path),
        format="b8",
        num_detectors=1,
        num_observables=0,
    )

    result = predict_observables_from_files(
        dem_path=str(dem_path),
        dets_path=str(dets_path),
        dets_format="b8",
        output_path=str(out_path),
        output_format="b8",
        decoder="aegis-pymatching",
        provenance_json=str(provenance_path),
        include_external_plugins=False,
    )

    predictions = stim.read_shot_data_file(
        path=str(out_path),
        format="b8",
        bit_pack=True,
        num_detectors=0,
        num_observables=1,
    )

    np.testing.assert_array_equal(predictions, dets)
    assert len(result["dem_sha256"]) == 64
    assert len(result["dets_sha256"]) == 64
    assert len(result["output_sha256"]) == 64

    loaded = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert loaded["decoder"] == "aegis-pymatching"
    assert loaded["num_detectors"] == 1
    assert loaded["num_observables"] == 1
