from __future__ import annotations

import pytest

from a3d.hardware_interface import IBMQuantumInterface, QuantumHardwareInterface


def test_explicit_simulator_is_labeled_synthetic():
    result = QuantumHardwareInterface().get_real_noise_parameters()
    assert result["source"] == "synthetic-simulator"
    assert result["synthetic"] is True
    assert result["backend_name"] == "simulator"


def test_ibm_interface_fails_closed_when_backend_is_unavailable(monkeypatch):
    interface = IBMQuantumInterface("missing-backend")
    monkeypatch.setattr(interface, "_init_ibm_connection", lambda: None)

    with pytest.raises(RuntimeError, match="Synthetic data was not substituted"):
        interface.get_real_noise_parameters()


def test_ibm_synthetic_fallback_requires_explicit_opt_in(monkeypatch):
    interface = IBMQuantumInterface(
        "missing-backend",
        allow_synthetic_fallback=True,
    )
    monkeypatch.setattr(interface, "_init_ibm_connection", lambda: None)

    result = interface.get_real_noise_parameters()
    assert result["synthetic"] is True
    assert result["source"] == "synthetic-simulator"
    assert "explicit IBM fallback" in result["provenance_reason"]
