from __future__ import annotations

from bench.cli import calibration_advantage, write_calibration_artifacts


def test_calibrated_weights_reduce_failures_under_nonuniform_noise(tmp_path):
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
    assert float(result["paired_exact_p_value"]) < 1e-4

    json_path = tmp_path / "calibration.json"
    plot_path = tmp_path / "calibration.png"
    write_calibration_artifacts(
        result,
        json_path=str(json_path),
        plot_path=str(plot_path),
    )
    assert json_path.exists() and json_path.stat().st_size > 0
    assert plot_path.exists() and plot_path.stat().st_size > 0
