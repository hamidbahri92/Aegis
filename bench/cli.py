from __future__ import annotations

import argparse
import csv
import os
import random
import time
from typing import List, Sequence, Tuple


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(fraction * len(ordered)) - 1))
    return float(ordered[index])


def sweep(
    decoder: str,
    ps: List[float],
    distance: int = 3,
    rounds: int = 3,
    trials: int = 100,
    out_csv: str | None = None,
    corr_params: str | None = None,
    latency_out: str | None = None,
) -> List[Tuple[float, float]]:
    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

    cfg = AegisConfig(distance=distance, rounds=rounds, decoder_type=decoder)
    if corr_params:
        cfg.correlation_params = corr_params

    runtime = DecoderRuntime(cfg, RotatedSurfaceLayout(cfg.distance))
    n_x = len(runtime.builder.node_order("X"))
    n_z = len(runtime.builder.node_order("Z"))
    from a3d.metrics import correction_chain_is_structurally_valid

    results: List[Tuple[float, float]] = []
    latency_samples: List[float] = []

    order_x = runtime.builder.node_order("X")
    order_z = runtime.builder.node_order("Z")
    last_round = rounds - 1
    graph_x = runtime.builder.build(
        "X",
        {(coord, t): 1.0 for coord, t in order_x},
        {(coord, t): 1.0 for coord, t in order_x if t < last_round},
        {(coord, t): 0.0 for coord, t in order_x if t < last_round},
    )
    graph_z = runtime.builder.build(
        "Z",
        {(coord, t): 1.0 for coord, t in order_z},
        {(coord, t): 1.0 for coord, t in order_z if t < last_round},
        {(coord, t): 0.0 for coord, t in order_z if t < last_round},
    )

    for physical_p in ps:
        failures = 0
        rng = random.Random(42)
        for _ in range(trials):
            syndrome_x = [int(rng.random() < physical_p) for _ in range(n_x)]
            syndrome_z = [int(rng.random() < physical_p) for _ in range(n_z)]

            started = time.perf_counter()
            result_x, result_z = runtime.decode_from_syndromes_uniform(
                syndrome_x, syndrome_z
            )
            latency_samples.append(time.perf_counter() - started)

            valid = correction_chain_is_structurally_valid(
                graph_x,
                graph_z,
                syndrome_x,
                syndrome_z,
                result_x.corrections,
                result_z.corrections,
            )
            failures += int(not valid)

        results.append((physical_p, failures / max(1, trials)))

    if latency_out and latency_samples:
        os.makedirs(os.path.dirname(latency_out) or ".", exist_ok=True)
        with open(latency_out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["p50_s", "p95_s", "p99_s", "samples"])
            writer.writerow(
                [
                    _percentile(latency_samples, 0.50),
                    _percentile(latency_samples, 0.95),
                    _percentile(latency_samples, 0.99),
                    len(latency_samples),
                ]
            )

    if out_csv:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        with open(out_csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "p",
                    "structural_validation_failure_rate",
                    "validation_failure_rate",
                ]
            )
            writer.writerows(
                (physical_p, rate, rate) for physical_p, rate in results
            )

    return results


def autobench(
    ps: Sequence[float] | None = None,
    decoders: Sequence[str] | None = None,
    distance: int = 3,
    rounds: int = 3,
    trials: int = 50,
    out_csv: str = "bench_out/summary.csv",
) -> str:
    if ps is None:
        ps = (0.01, 0.02, 0.04)
    if decoders is None:
        decoders = ("mwpm", "mwpm2", "mwpm_corr", "uf")

    rows = []
    for decoder in decoders:
        data = sweep(
            decoder,
            list(ps),
            distance=distance,
            rounds=rounds,
            trials=trials,
        )
        rows.extend((decoder, physical_p, rate) for physical_p, rate in data)

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "decoder",
                "p",
                "structural_validation_failure_rate",
                "validation_failure_rate",
            ]
        )
        writer.writerows(
            (decoder, physical_p, rate, rate)
            for decoder, physical_p, rate in rows
        )
    return out_csv


def plot(in_csv: str, out_png: str | None = None) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return ""

    xs = []
    ys = []
    with open(in_csv, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if rows and "decoder" in rows[0]:
        first_decoder = rows[0]["decoder"]
        rows = [row for row in rows if row["decoder"] == first_decoder]

    for row in rows:
        if "structural_validation_failure_rate" in row:
            rate_key = "structural_validation_failure_rate"
        elif "validation_failure_rate" in row:
            rate_key = "validation_failure_rate"
        else:
            rate_key = "logical_rate"
        if "p" in row and rate_key in row:
            xs.append(float(row["p"]))
            ys.append(float(row[rate_key]))

    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("p")
    plt.ylabel("correction validation failure rate")

    if not out_png:
        out_png = os.path.splitext(in_csv)[0] + ".png"
    plt.savefig(out_png, dpi=160, bbox_inches="tight")
    return out_png


def realtime(
    decoder: str = "mwpm",
    distance: int = 3,
    rounds: int = 3,
    steps: int = 200,
    out_csv: str = "bench_out/realtime_latency.csv",
) -> str:
    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

    cfg = AegisConfig(distance=distance, rounds=rounds, decoder_type=decoder)
    runtime = DecoderRuntime(cfg, RotatedSurfaceLayout(cfg.distance))
    n_x = len(runtime.builder.node_order("X"))
    n_z = len(runtime.builder.node_order("Z"))
    rng = random.Random(7)
    latencies = []

    for _ in range(steps):
        syndrome_x = [rng.randint(0, 1) for _ in range(n_x)]
        syndrome_z = [rng.randint(0, 1) for _ in range(n_z)]
        started = time.perf_counter()
        runtime.decode_from_syndromes_uniform(syndrome_x, syndrome_z)
        latencies.append(time.perf_counter() - started)

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "seconds"])
        writer.writerow(["p50", _percentile(latencies, 0.50)])
        writer.writerow(["p95", _percentile(latencies, 0.95)])
        writer.writerow(["p99", _percentile(latencies, 0.99)])
    return out_csv


def calibration_advantage(
    shots: int = 10000,
    seed: int = 20260928,
    p_left: float = 0.18,
    p_middle: float = 0.01,
    p_right: float = 0.18,
) -> dict[str, float | int]:
    """Measure the value of correct non-uniform weights in a controlled graph model.

    The graph has two detector nodes between opposite boundaries. Two different
    physical error chains can produce the same two-detector syndrome: a single
    middle edge, or the pair of boundary edges. Those chains differ by a
    boundary-to-boundary logical path.

    The uniform decoder receives one global average error rate for all edges.
    The calibrated decoder receives the true edge probabilities. Both decode
    exactly the same sampled physical error chains. Logical failure is measured
    from the homology of physical-error XOR correction, not from syndrome
    annihilation alone.

    This is a graph-level calibration experiment. It does not claim that current
    hardware-interface calibration arrays are automatically mapped into these
    weights.
    """
    from a3d.decoder_mwpm import MWPMDecoder
    from a3d.graph import DecodingGraph, Edge
    from a3d.metrics import _correction_spans_opposite_boundaries
    from a3d.stats import logodds_from_p

    probabilities = (float(p_left), float(p_middle), float(p_right))
    if any(not 0.0 < p < 0.5 for p in probabilities):
        raise ValueError("edge probabilities must satisfy 0 < p < 0.5")
    if shots < 1:
        raise ValueError("shots must be positive")

    left_boundary = 2
    right_boundary = 3
    node_meta = {
        0: ("X", None, 0, "stab"),
        1: ("X", None, 0, "stab"),
        left_boundary: ("X", None, 0, "boundary-H-W"),
        right_boundary: ("X", None, 0, "boundary-H-E"),
    }

    def make_graph(weights):
        return DecodingGraph(
            nodes=[0, 1, left_boundary, right_boundary],
            edges=[
                Edge(0, left_boundary, weights[0], "boundary"),
                Edge(0, 1, weights[1], "space"),
                Edge(1, right_boundary, weights[2], "boundary"),
            ],
            node_meta=node_meta,
        )

    calibrated_graph = make_graph(tuple(logodds_from_p(p) for p in probabilities))
    global_p = sum(probabilities) / len(probabilities)
    uniform_weight = logodds_from_p(global_p)
    uniform_graph = make_graph((uniform_weight, uniform_weight, uniform_weight))

    rng = random.Random(seed)
    physical_errors: list[tuple[bool, bool, bool]] = []
    syndromes: list[list[int]] = []
    for _ in range(shots):
        error = tuple(rng.random() < p for p in probabilities)
        physical_errors.append(error)
        left_error, middle_error, right_error = error
        syndromes.append(
            [
                int(left_error) ^ int(middle_error),
                int(middle_error) ^ int(right_error),
            ]
        )

    decoder = MWPMDecoder()
    uniform_results = decoder.decode_batch(uniform_graph, syndromes)
    calibrated_results = decoder.decode_batch(calibrated_graph, syndromes)

    uniform_index = {id(edge): index for index, edge in enumerate(uniform_graph.edges)}
    calibrated_index = {
        id(edge): index for index, edge in enumerate(calibrated_graph.edges)
    }

    def logical_failure(error, result, index_by_id):
        correction_indices = {index_by_id[id(edge)] for edge in result.corrections}
        residual_indices = {
            index
            for index, active in enumerate(error)
            if bool(active) ^ (index in correction_indices)
        }
        residual_edges = [
            calibrated_graph.edges[index] for index in sorted(residual_indices)
        ]
        horizontal_span, vertical_span = _correction_spans_opposite_boundaries(
            calibrated_graph,
            residual_edges,
        )
        return horizontal_span or vertical_span

    uniform_failures = []
    calibrated_failures = []
    for error, uniform_result, calibrated_result in zip(
        physical_errors,
        uniform_results,
        calibrated_results,
        strict=True,
    ):
        uniform_failures.append(
            logical_failure(error, uniform_result, uniform_index)
        )
        calibrated_failures.append(
            logical_failure(error, calibrated_result, calibrated_index)
        )

    uniform_count = sum(uniform_failures)
    calibrated_count = sum(calibrated_failures)
    uniform_rate = uniform_count / shots
    calibrated_rate = calibrated_count / shots
    uniform_only = sum(
        u and not k
        for u, k in zip(uniform_failures, calibrated_failures, strict=True)
    )
    calibrated_only = sum(
        k and not u
        for u, k in zip(uniform_failures, calibrated_failures, strict=True)
    )
    both = sum(
        u and k
        for u, k in zip(uniform_failures, calibrated_failures, strict=True)
    )

    expected_uniform = p_left * p_right
    expected_calibrated = p_middle * (
        (1.0 - p_left) * (1.0 - p_right) + p_left * p_right
    )

    return {
        "shots": int(shots),
        "seed": int(seed),
        "p_left": float(p_left),
        "p_middle": float(p_middle),
        "p_right": float(p_right),
        "uniform_global_p": float(global_p),
        "uniform_failures": int(uniform_count),
        "calibrated_failures": int(calibrated_count),
        "uniform_only_failures": int(uniform_only),
        "calibrated_only_failures": int(calibrated_only),
        "both_failures": int(both),
        "uniform_graph_logical_failure_rate": float(uniform_rate),
        "calibrated_graph_logical_failure_rate": float(calibrated_rate),
        "expected_uniform_rate": float(expected_uniform),
        "expected_calibrated_rate": float(expected_calibrated),
        "relative_reduction": (
            float(1.0 - calibrated_rate / uniform_rate)
            if uniform_rate > 0.0
            else 0.0
        ),
        "improvement_factor": (
            float(uniform_rate / calibrated_rate)
            if calibrated_rate > 0.0
            else float("inf")
        ),
    }


def circuit_acceptance(
    distance: int = 3,
    rounds: int = 3,
    shots: int = 512,
    physical_error_rate: float = 0.01,
    seed: int = 1234,
) -> dict[str, float | int]:
    """Compare Aegis DEM predictions with raw PyMatching on sampled Stim circuits.

    This is a circuit-level acceptance check for the DEM bridge. It validates
    detector/observable plumbing and reports logical failures against Stim's
    sampled observables. It does not validate Aegis's custom graph builder.
    """
    try:
        import stim
    except ImportError as exc:
        raise RuntimeError(
            "Circuit acceptance requires Stim: pip install 'aegis-qec[full]'"
        ) from exc

    import numpy as np
    import pymatching

    from a3d.decoder_mwpm_pm import PyMatchingMWPMDecoder

    circuit = stim.Circuit.generated(
        "surface_code:rotated_memory_x",
        distance=distance,
        rounds=rounds,
        after_clifford_depolarization=physical_error_rate,
        before_measure_flip_probability=physical_error_rate,
        after_reset_flip_probability=physical_error_rate,
    )
    dem = circuit.detector_error_model(decompose_errors=True)
    detector_samples, actual_observables = circuit.compile_detector_sampler(
        seed=seed
    ).sample(
        shots=shots,
        separate_observables=True,
    )

    raw_matching = pymatching.Matching.from_detector_error_model(dem)
    raw_predictions = raw_matching.decode_batch(detector_samples)
    aegis_predictions = PyMatchingMWPMDecoder().decode_dem_batch(
        str(dem),
        detector_samples,
    )

    adapter_mismatches = np.any(raw_predictions != aegis_predictions, axis=1)
    raw_failures = np.any(raw_predictions != actual_observables, axis=1)
    aegis_failures = np.any(aegis_predictions != actual_observables, axis=1)

    return {
        "shots": int(shots),
        "adapter_mismatch_count": int(np.sum(adapter_mismatches)),
        "raw_logical_failures": int(np.sum(raw_failures)),
        "aegis_logical_failures": int(np.sum(aegis_failures)),
        "raw_logical_error_rate": float(np.mean(raw_failures)),
        "aegis_logical_error_rate": float(np.mean(aegis_failures)),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-bench",
        description="Benchmark Aegis QEC decoders and latency.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sweep_parser = sub.add_parser("sweep", help="Run a structural correction-chain stress sweep.")
    sweep_parser.add_argument("--decoder", default="mwpm")
    sweep_parser.add_argument("--p", nargs="+", type=float, default=[0.02, 0.06])
    sweep_parser.add_argument("--distance", type=int, default=3)
    sweep_parser.add_argument("--rounds", type=int, default=3)
    sweep_parser.add_argument("--trials", type=int, default=50)
    sweep_parser.add_argument("--out", default="bench_out/sweep.csv")
    sweep_parser.add_argument("--corr-params")
    sweep_parser.add_argument("--latency-out", default="bench_out/latency.csv")

    auto_parser = sub.add_parser("autobench", help="Compare standard decoders.")
    auto_parser.add_argument("--distance", type=int, default=3)
    auto_parser.add_argument("--rounds", type=int, default=3)
    auto_parser.add_argument("--trials", type=int, default=50)
    auto_parser.add_argument("--out", default="bench_out/summary.csv")

    plot_parser = sub.add_parser("plot", help="Plot a benchmark CSV.")
    plot_parser.add_argument("csv")
    plot_parser.add_argument("--out")

    realtime_parser = sub.add_parser(
        "realtime",
        help="Measure end-to-end decoder latency percentiles.",
    )
    realtime_parser.add_argument("--decoder", default="mwpm")
    realtime_parser.add_argument("--distance", type=int, default=3)
    realtime_parser.add_argument("--rounds", type=int, default=3)
    realtime_parser.add_argument("--steps", type=int, default=200)
    realtime_parser.add_argument("--out", default="bench_out/realtime_latency.csv")

    calibration_parser = sub.add_parser(
        "calibration-advantage",
        help=(
            "Compare uniform and correctly calibrated MWPM weights on the same "
            "non-uniform graph-level error samples."
        ),
    )
    calibration_parser.add_argument("--shots", type=int, default=10000)
    calibration_parser.add_argument("--seed", type=int, default=20260928)
    calibration_parser.add_argument("--p-left", type=float, default=0.18)
    calibration_parser.add_argument("--p-middle", type=float, default=0.01)
    calibration_parser.add_argument("--p-right", type=float, default=0.18)

    acceptance_parser = sub.add_parser(
        "circuit-acceptance",
        help="Compare Aegis DEM decoding with raw PyMatching on a Stim surface-code circuit.",
    )
    acceptance_parser.add_argument("--distance", type=int, default=3)
    acceptance_parser.add_argument("--rounds", type=int, default=3)
    acceptance_parser.add_argument("--shots", type=int, default=512)
    acceptance_parser.add_argument("--p", type=float, default=0.01)
    acceptance_parser.add_argument("--seed", type=int, default=1234)
    return parser


def main(argv: List[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.cmd == "sweep":
        results = sweep(
            args.decoder,
            args.p,
            distance=args.distance,
            rounds=args.rounds,
            trials=args.trials,
            out_csv=args.out,
            corr_params=args.corr_params,
            latency_out=args.latency_out,
        )
        print(f"Aegis QEC sweep complete with {len(results)} probability points.")
        for physical_p, logical_rate in results:
            print(f"p={physical_p:.6g} structural_validation_failure_rate={logical_rate:.6g}")
        print(f"Results: {args.out}")
        print(f"Latency summary: {args.latency_out}")
    elif args.cmd == "autobench":
        out_path = autobench(
            distance=args.distance,
            rounds=args.rounds,
            trials=args.trials,
            out_csv=args.out,
        )
        print(f"Aegis QEC decoder comparison complete. Results: {out_path}")
    elif args.cmd == "plot":
        out_path = plot(args.csv, args.out)
        if not out_path:
            print("Plotting requires matplotlib.")
            return 2
        print(f"Plot written to: {out_path}")
    elif args.cmd == "realtime":
        out_path = realtime(
            decoder=args.decoder,
            distance=args.distance,
            rounds=args.rounds,
            steps=args.steps,
            out_csv=args.out,
        )
        with open(out_path, "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        print("Aegis QEC end-to-end latency")
        for row in rows:
            print(f"{row['metric']}: {float(row['seconds']) * 1000.0:.3f} ms")
        print(f"Results: {out_path}")
        print("This is an Aegis end-to-end measurement, not the upstream PyMatching-vs-NetworkX benchmark.")
    elif args.cmd == "calibration-advantage":
        result = calibration_advantage(
            shots=args.shots,
            seed=args.seed,
            p_left=args.p_left,
            p_middle=args.p_middle,
            p_right=args.p_right,
        )
        print("Aegis QEC controlled calibration-advantage experiment")
        print(f"Shots: {result['shots']}")
        print(
            "Uniform graph logical failure rate: "
            f"{float(result['uniform_graph_logical_failure_rate']):.6g}"
        )
        print(
            "Calibrated graph logical failure rate: "
            f"{float(result['calibrated_graph_logical_failure_rate']):.6g}"
        )
        print(
            "Relative failure reduction: "
            f"{100.0 * float(result['relative_reduction']):.2f}%"
        )
        print(
            "Uniform/calibrated failure ratio: "
            f"{float(result['improvement_factor']):.3f}x"
        )
        print(
            "Paired discordant failures, uniform-only vs calibrated-only: "
            f"{result['uniform_only_failures']} vs "
            f"{result['calibrated_only_failures']}"
        )
        print(
            "This is a controlled graph-level calibration experiment, "
            "not a hardware-device benchmark."
        )
    elif args.cmd == "circuit-acceptance":
        result = circuit_acceptance(
            distance=args.distance,
            rounds=args.rounds,
            shots=args.shots,
            physical_error_rate=args.p,
            seed=args.seed,
        )
        print("Aegis QEC circuit-level DEM acceptance")
        print(f"Shots: {result['shots']}")
        print(f"Adapter mismatches vs raw PyMatching: {result['adapter_mismatch_count']}")
        print(
            "Raw PyMatching logical error rate: "
            f"{float(result['raw_logical_error_rate']):.6g}"
        )
        print(
            "Aegis DEM logical error rate: "
            f"{float(result['aegis_logical_error_rate']):.6g}"
        )
        return 0 if result["adapter_mismatch_count"] == 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
