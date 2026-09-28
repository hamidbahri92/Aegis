from __future__ import annotations

import json

import aegis_qec.cli as cli
from aegis_qec.cli import main


def test_doctor_reports_sparse_blossom(capsys):
    code = main(["doctor", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert code == 0
    assert report["distribution"] == "aegis-qec"
    assert report["backend"] == "pymatching-sparse-blossom"
    assert report["self_test"] == "pass"


def test_demo_is_user_facing_and_deterministic(capsys):
    code = main(
        [
            "demo",
            "--decoder",
            "mwpm",
            "--distance",
            "3",
            "--rounds",
            "3",
            "--error-probability",
            "0",
        ]
    )
    output = capsys.readouterr().out

    assert code == 0
    assert "Aegis QEC demo" in output
    assert "pymatching-sparse-blossom" in output
    assert "Detection events: X=0, Z=0" in output



def test_doctor_returns_nonzero_when_core_health_check_fails(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "_doctor_report",
        lambda: {
            "name": "Aegis QEC",
            "distribution": "aegis-qec",
            "version": "test",
            "python": "3.12",
            "python_supported": True,
            "platform": "test",
            "backend": None,
            "pymatching": None,
            "stim": None,
            "streamlit": None,
            "self_test": "fail",
            "error": "simulated broken decoder environment",
        },
    )

    code = cli.main(["doctor", "--json"])
    report = json.loads(capsys.readouterr().out)

    assert code == 1
    assert report["self_test"] == "fail"
    assert report["backend"] is None
