from __future__ import annotations

import json

import numpy as np
import pytest

stim = pytest.importorskip("stim")

from aegis_qec.dataset import (
    evaluate_decoders_on_dataset,
    import_qec_dataset,
    inspect_qec_dataset,
)


def _write_dem(path):
    path.write_text("error(0.1) D0 L0\n", encoding="utf-8")


def _expected_rows():
    detectors = np.asarray(
        [[0], [1], [1], [0], [1], [0]],
        dtype=np.bool_,
    )
    observables = detectors.copy()
    return detectors, observables


def test_import_combined_dets_and_evaluate_decoder(tmp_path):
    dem_path = tmp_path / "model.dem"
    shots_path = tmp_path / "shots.dets"
    out_path = tmp_path / "dataset.h5"
    _write_dem(dem_path)

    shots_path.write_text(
        "\n".join(
            [
                "shot",
                "shot D0 L0",
                "shot D0 L0",
                "shot",
                "shot D0 L0",
                "shot",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = import_qec_dataset(
        str(out_path),
        dem_path=str(dem_path),
        detector_data_path=str(shots_path),
        data_format="dets",
        seed=7,
        chunk_size=2,
    )
    assert report["written_shots"] == 6
    assert report["source_format"] == "dets"

    inspection = inspect_qec_dataset(str(out_path))
    assert inspection["valid"] is True
    assert inspection["source_type"] == "imported-shot-data"
    assert inspection["source_format"] == "dets"
    assert inspection["source_detector_data_sha256"]

    evaluation = evaluate_decoders_on_dataset(
        str(out_path),
        decoders=["aegis-pymatching"],
        split_name="all",
        include_external_plugins=False,
    )
    assert evaluation["dataset"]["selected_shots"] == 6
    assert evaluation["rows"][0]["errors"] == 0


def test_import_combined_b8_streaming_matches_original_rows(tmp_path):
    dem_path = tmp_path / "model.dem"
    shots_path = tmp_path / "shots.b8"
    out_path = tmp_path / "dataset.h5"
    _write_dem(dem_path)

    detectors, observables = _expected_rows()
    combined = np.concatenate([detectors, observables], axis=1)
    packed = np.packbits(combined, axis=1, bitorder="little")
    packed.tofile(shots_path)

    import_qec_dataset(
        str(out_path),
        dem_path=str(dem_path),
        detector_data_path=str(shots_path),
        data_format="b8",
        seed=12,
        chunk_size=2,
    )

    import h5py

    with h5py.File(out_path, "r") as handle:
        np.testing.assert_array_equal(handle["syndromes"][:], detectors)
        np.testing.assert_array_equal(handle["observables"][:], observables)


def test_import_separate_b8_streams(tmp_path):
    dem_path = tmp_path / "model.dem"
    det_path = tmp_path / "detectors.b8"
    obs_path = tmp_path / "observables.b8"
    out_path = tmp_path / "dataset.h5"
    _write_dem(dem_path)

    detectors, observables = _expected_rows()
    np.packbits(
        detectors,
        axis=1,
        bitorder="little",
    ).tofile(det_path)
    np.packbits(
        observables,
        axis=1,
        bitorder="little",
    ).tofile(obs_path)

    report = import_qec_dataset(
        str(out_path),
        dem_path=str(dem_path),
        detector_data_path=str(det_path),
        observable_data_path=str(obs_path),
        data_format="b8",
        seed=99,
        chunk_size=4,
    )
    assert report["written_shots"] == len(detectors)
    assert report["source_observable_data_sha256"]

    inspection = inspect_qec_dataset(str(out_path))
    assert inspection["valid"] is True
    assert inspection["source_observable_data_sha256"]


def test_import_rejects_mismatched_separate_b8_counts(tmp_path):
    dem_path = tmp_path / "model.dem"
    det_path = tmp_path / "detectors.b8"
    obs_path = tmp_path / "observables.b8"
    _write_dem(dem_path)

    np.asarray([1, 0, 1], dtype=np.uint8).tofile(det_path)
    np.asarray([1, 0], dtype=np.uint8).tofile(obs_path)

    with pytest.raises(ValueError, match="different shot counts"):
        import_qec_dataset(
            str(tmp_path / "dataset.h5"),
            dem_path=str(dem_path),
            detector_data_path=str(det_path),
            observable_data_path=str(obs_path),
            data_format="b8",
        )


def test_import_is_immutable_and_does_not_overwrite(tmp_path):
    dem_path = tmp_path / "model.dem"
    shots_path = tmp_path / "shots.dets"
    out_path = tmp_path / "dataset.h5"
    _write_dem(dem_path)
    shots_path.write_text("shot\nshot D0 L0\n", encoding="utf-8")

    import_qec_dataset(
        str(out_path),
        dem_path=str(dem_path),
        detector_data_path=str(shots_path),
        data_format="dets",
    )
    first_hash = inspect_qec_dataset(str(out_path))["file_sha256"]

    with pytest.raises(FileExistsError):
        import_qec_dataset(
            str(out_path),
            dem_path=str(dem_path),
            detector_data_path=str(shots_path),
            data_format="dets",
        )

    assert inspect_qec_dataset(str(out_path))["file_sha256"] == first_hash


def test_import_report_is_json_serializable(tmp_path):
    dem_path = tmp_path / "model.dem"
    shots_path = tmp_path / "shots.dets"
    out_path = tmp_path / "dataset.h5"
    _write_dem(dem_path)
    shots_path.write_text("shot\nshot D0 L0\n", encoding="utf-8")

    report = import_qec_dataset(
        str(out_path),
        dem_path=str(dem_path),
        detector_data_path=str(shots_path),
        data_format="dets",
    )
    json.dumps(report, sort_keys=True)
