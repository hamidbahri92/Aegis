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
    results: List[Tuple[float, float]] = []
    latency_samples: List[float] = []

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

            if result_x.avg_cost <= 0 and sum(syndrome_x) > 0:
                failures += 1
            if result_z.avg_cost <= 0 and sum(syndrome_z) > 0:
                failures += 1

        results.append((physical_p, failures / max(1, 2 * trials)))

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
            writer.writerow(["p", "logical_rate"])
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
        writer.writerow(["decoder", "p", "logical_rate"])
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
        if "p" in row and "logical_rate" in row:
            xs.append(float(row["p"]))
            ys.append(float(row["logical_rate"]))

    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("p")
    plt.ylabel("logical error rate")

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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-bench",
        description="Benchmark Aegis QEC decoders and latency.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sweep_parser = sub.add_parser("sweep", help="Run a logical-rate sweep.")
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
    return parser


def main(argv: List[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.cmd == "sweep":
        sweep(
            args.decoder,
            args.p,
            distance=args.distance,
            rounds=args.rounds,
            trials=args.trials,
            out_csv=args.out,
            corr_params=args.corr_params,
            latency_out=args.latency_out,
        )
    elif args.cmd == "autobench":
        autobench(
            distance=args.distance,
            rounds=args.rounds,
            trials=args.trials,
            out_csv=args.out,
        )
    elif args.cmd == "plot":
        plot(args.csv, args.out)
    elif args.cmd == "realtime":
        realtime(
            decoder=args.decoder,
            distance=args.distance,
            rounds=args.rounds,
            steps=args.steps,
            out_csv=args.out,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
