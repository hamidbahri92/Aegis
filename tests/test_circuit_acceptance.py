from __future__ import annotations

import pytest

pytest.importorskip("stim")

from bench.cli import circuit_acceptance


def test_stim_circuit_acceptance_matches_raw_pymatching():
    result = circuit_acceptance(
        distance=3,
        rounds=3,
        shots=256,
        physical_error_rate=0.02,
        seed=20260928,
    )

    assert result["shots"] == 256
    assert result["adapter_mismatch_count"] == 0
    assert result["aegis_logical_failures"] == result["raw_logical_failures"]
    assert result["aegis_logical_error_rate"] == result["raw_logical_error_rate"]
