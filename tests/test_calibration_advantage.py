from __future__ import annotations

from bench.cli import calibration_advantage


def test_calibrated_weights_reduce_failures_under_nonuniform_noise():
    result = calibration_advantage(
        shots=12000,
        seed=20260928,
        p_left=0.18,
        p_middle=0.01,
        p_right=0.18,
    )

    uniform_rate = float(result["uniform_graph_logical_failure_rate"])
    calibrated_rate = float(result["calibrated_graph_logical_failure_rate"])

    assert calibrated_rate < uniform_rate
    assert float(result["improvement_factor"]) > 3.0
    assert int(result["uniform_only_failures"]) > int(
        result["calibrated_only_failures"]
    )
    assert abs(uniform_rate - float(result["expected_uniform_rate"])) < 0.01
    assert abs(calibrated_rate - float(result["expected_calibrated_rate"])) < 0.005
