from __future__ import annotations

import pytest

from aegis_qec.dataset import (
    evaluate_decoders_on_dataset,
    generate_qec_dataset,
)


def test_fixed_dataset_evaluation_is_reproducible(tmp_path):
    path = tmp_path / "dataset.h5"
    generate_qec_dataset(
        str(path),
        shots=48,
        seed=20261006,
        chunk_size=16,
        distance=3,
        physical_error_rate=0.02,
        basis="x",
    )

    first = evaluate_decoders_on_dataset(
        str(path),
        decoders=[
            "aegis-pymatching",
            "aegis-pymatching-correlated",
        ],
        split_name="all",
        batch_size=13,
        include_external_plugins=False,
    )
    second = evaluate_decoders_on_dataset(
        str(path),
        decoders=[
            "aegis-pymatching",
            "aegis-pymatching-correlated",
        ],
        split_name="all",
        batch_size=13,
        include_external_plugins=False,
    )

    assert first["dataset"]["selected_shots"] == 48
    assert first["dataset"]["selected_syndromes_sha256"] == second["dataset"]["selected_syndromes_sha256"]
    assert first["dataset"]["selected_observables_sha256"] == second["dataset"]["selected_observables_sha256"]
    assert [row["errors"] for row in first["rows"]] == [row["errors"] for row in second["rows"]]
    assert first["pairwise_disagreements"] == second["pairwise_disagreements"]


def test_fixed_dataset_evaluation_respects_max_shots(tmp_path):
    path = tmp_path / "dataset.h5"
    generate_qec_dataset(
        str(path),
        shots=32,
        seed=17,
        chunk_size=8,
        train_fraction=1.0,
        validation_fraction=0.0,
        distance=3,
        physical_error_rate=0.02,
    )

    result = evaluate_decoders_on_dataset(
        str(path),
        decoders=["aegis-pymatching"],
        split_name="train",
        max_shots=9,
        batch_size=7,
        include_external_plugins=False,
    )
    assert result["dataset"]["selected_shots"] == 9


def test_fixed_dataset_evaluation_rejects_empty_split(tmp_path):
    path = tmp_path / "dataset.h5"
    generate_qec_dataset(
        str(path),
        shots=16,
        seed=4,
        chunk_size=8,
        train_fraction=1.0,
        validation_fraction=0.0,
        distance=3,
        physical_error_rate=0.02,
    )

    with pytest.raises(ValueError, match="contains no selected shots"):
        evaluate_decoders_on_dataset(
            str(path),
            decoders=["aegis-pymatching"],
            split_name="test",
            include_external_plugins=False,
        )
