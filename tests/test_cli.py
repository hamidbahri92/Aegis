from __future__ import annotations

import json

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
