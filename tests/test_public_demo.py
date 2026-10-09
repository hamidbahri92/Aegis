"""Public demonstration refuses unsafe workloads and reuses production engines."""

from __future__ import annotations

import pytest

from aegis_qec import public_demo as demo


@pytest.mark.parametrize(
    ("name", "value", "allowed"),
    [
        ("distance", 9, demo.ALLOWED_DISTANCES),
        ("distance", True, demo.ALLOWED_DISTANCES),
        ("distance", 3.0, demo.ALLOWED_DISTANCES),
        ("basis", "y", demo.ALLOWED_BASIS),
        ("p", 0.49, demo.ALLOWED_PROBABILITIES),
        ("seed", -1, demo.ALLOWED_SEEDS),
        ("shots", 50000, demo.ALLOWED_SHOTS),
        ("shots", 400.0, demo.ALLOWED_SHOTS),
    ],
)
def test_public_demo_denies_out_of_scope_workloads(name, value, allowed):
    with pytest.raises(ValueError):
        demo.require_choice(name, value, allowed)


def test_study_is_bounded_to_exactly_four_points(monkeypatch):
    import aegis_qec.research as research

    observed = {}

    def fake_run(**kwargs):
        observed.update(kwargs)
        return {"example": "validated"}

    monkeypatch.setattr(research, "run_surface_code_study", fake_run)

    record = demo.run_demo_study(basis="x", shots=200)
    assert record == {"example": "validated"}
    assert observed == {
        "distances": (3, 5),
        "physical_error_rates": (0.003, 0.006),
        "basis": "x",
        "shots": 200,
        "seed": 1234,
    }


def test_shot_uses_existing_explainer_without_filesystem(monkeypatch):
    import aegis_qec.explain as explain

    observed = {}

    def fake_explain(**kwargs):
        observed.update(kwargs)
        return {"example": "reproducible shot"}

    monkeypatch.setattr(explain, "explain_surface_code_shot", fake_explain)
    result = demo.explain_demo_shot(
        distance=5, basis="z", probability=0.006, seed=1234
    )
    assert result == {"example": "reproducible shot"}
    assert observed == {
        "distance": 5,
        "basis": "z",
        "physical_error_rate": 0.006,
        "seed": 1234,
    }


def test_excessive_study_request_does_not_call_engine(monkeypatch):
    import aegis_qec.research as research

    def unexpected_call(**kwargs):
        raise AssertionError("Research engine should not execute")

    monkeypatch.setattr(research, "run_surface_code_study", unexpected_call)
    with pytest.raises(ValueError):
        demo.run_demo_study(basis="x", shots=1000000)
