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
            writer.writerow(["p", "validation_failure_rate"])
            writer.writerows(results)

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
        writer.writerow(["decoder", "p", "validation_failure_rate"])
        writer.writerows(rows)
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
        rate_key = "validation_failure_rate" if "validation_failure_rate" in row else "logical_rate"
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
            print(f"p={physical_p:.6g} validation_failure_rate={logical_rate:.6g}")
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
