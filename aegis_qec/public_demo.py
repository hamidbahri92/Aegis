"""Small bounded, read-only public demonstration of existing Aegis QEC engines.

Unlike the complete research GUI, public demo functions never accept paths,
shell commands, uploaded data, or external workloads. They intentionally run
only small fixed teaching examples on shared free-tier CPU hosts.
"""

from __future__ import annotations

from typing import Any

ALLOWED_DISTANCES = (3, 5, 7)
ALLOWED_BASIS = ("x", "z")
ALLOWED_PROBABILITIES = (0.003, 0.006, 0.01)
ALLOWED_SEEDS = (1234, 1235, 1236)
ALLOWED_SHOTS = (100, 200, 400)
STUDY_DISTANCES = (3, 5)
STUDY_PROBABILITIES = (0.003, 0.006)


def require_choice(label: str, value: Any, allowed: tuple) -> None:
    """Fail closed even if a caller bypasses the graphical widgets."""
    if type(value) not in (str, int, float) or value not in allowed:
        raise ValueError(f"{label} must be one of {allowed!r}")


def explain_demo_shot(
    *, distance: int, basis: str, probability: float, seed: int
) -> dict[str, Any]:
    """Reuse the validated Stim/PyMatching explanation without disk writes."""
    require_choice("distance", distance, ALLOWED_DISTANCES)
    require_choice("basis", basis, ALLOWED_BASIS)
    require_choice("physical error probability", probability, ALLOWED_PROBABILITIES)
    require_choice("seed", seed, ALLOWED_SEEDS)

    from aegis_qec.explain import explain_surface_code_shot

    return explain_surface_code_shot(
        distance=distance,
        basis=basis,
        physical_error_rate=probability,
        seed=seed,
    )


def run_demo_study(*, basis: str, shots: int) -> dict[str, Any]:
    """Run four small experiment points; never write artifacts server-side."""
    require_choice("basis", basis, ALLOWED_BASIS)
    require_choice("shots", shots, ALLOWED_SHOTS)

    from aegis_qec.research import run_surface_code_study

    return run_surface_code_study(
        distances=STUDY_DISTANCES,
        physical_error_rates=STUDY_PROBABILITIES,
        basis=basis,
        shots=shots,
        seed=1234,
    )
