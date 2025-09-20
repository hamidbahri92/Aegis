
# FILE: bench/cli.py
from __future__ import annotations

import argparse
import csv
import os
from typing import List, Tuple


def sweep(decoder: str, ps: List[float], distance: int=3, rounds: int=3, trials: int=100, out_csv: str|None=None, corr_params: str|None=None, latency_out: str|None=None) -> List[Tuple[float,float]]:
    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
    cfg = AegisConfig(distance=distance, rounds=rounds, decoder_type=decoder)
    if corr_params:
        cfg.correlation_params = corr_params
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    import random
    nX = len(rt.builder.node_order("X"))
    nZ = len(rt.builder.node_order("Z"))
    results = []
    lat_samples = []
    for p in ps:
        bad = 0
        random.seed(42)
        for _ in range(trials):
            sX = [1 if random.random()<p else 0 for _ in range(nX)]
            sZ = [1 if random.random()<p else 0 for _ in range(nZ)]
            import time
            t0 = time.perf_counter()
            resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
            t1 = time.perf_counter()
            lat_samples.append(t1 - t0)
            if resX.avg_cost<=0 and sum(sX)>0: bad += 1
            if resZ.avg_cost<=0 and sum(sZ)>0: bad += 1
        results.append((p, bad/max(1,2*trials)))
    if latency_out and lat_samples:
        def _pct(a, q):
            a = sorted(a); idx = int(q*len(a)); idx = min(max(idx,0),len(a)-1); return float(a[idx])
        p50 = _pct(lat_samples, 0.50); p95 = _pct(lat_samples, 0.95); p99 = _pct(lat_samples, 0.99)
        os.makedirs(os.path.dirname(latency_out) or ".", exist_ok=True)
        with open(latency_out, "w", newline="") as f:
            import csv as _csv
            w = _csv.writer(f); w.writerow(["p50_s","p95_s","p99_s","samples"]); w.writerow([p50,p95,p99,len(lat_samples)])
    if out_csv:
        os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
        with open(out_csv, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["p","logical_rate"]); w.writerows(results)
    return results

def autobench(ps = [0.01,0.02,0.04], decoders = ["mwpm","mwpm2","mwpm_corr","uf"], distance=3, rounds=3, trials=50, out_csv="bench_out/summary.csv"):
    rows = []
    for d in decoders:
        data = sweep(d, ps, distance=distance, rounds=rounds, trials=trials)
        for p, r in data:
            rows.append((d, p, r))
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w=csv.writer(f); w.writerow(["decoder","p","logical_rate"]); w.writerows(rows)
    return out_csv

def plot(in_csv: str, out_png: str|None=None) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    xs, ys = [], []
    import csv
    with open(in_csv, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if "p" in r.fieldnames and "logical_rate" in r.fieldnames:
            for row in r:
                xs.append(float(row["p"])); ys.append(float(row["logical_rate"]))
        elif "decoder" in r.fieldnames:
            dec = None
            rows = list(r)
            if rows:
                dec = rows[0]["decoder"]
                for row in rows:
                    if row["decoder"] != dec: continue
                    xs.append(float(row["p"])); ys.append(float(row["logical_rate"]))
    plt.figure(); plt.plot(xs, ys, marker="o"); plt.xlabel("p"); plt.ylabel("logical error rate")
    if not out_png:
        out_png = os.path.splitext(in_csv)[0] + ".png"
    plt.savefig(out_png, dpi=160, bbox_inches="tight")
    return out_png

def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aegis-bench", description="Unified benchmarking CLI for Aegis")
    sub = p.add_subparsers(dest="cmd", required=True)
    psweep = sub.add_parser("sweep"); psweep.add_argument("--decoder", default="mwpm"); psweep.add_argument("--p", nargs="+", type=float, default=[0.02,0.06]); psweep.add_argument("--distance", type=int, default=3); psweep.add_argument("--rounds", type=int, default=3); psweep.add_argument("--trials", type=int, default=50); psweep.add_argument("--out", default="bench_out/sweep.csv"); psweep.add_argument("--corr-params"); psweep.add_argument("--latency-out", default="bench_out/latency.csv")
    pauto = sub.add_parser("autobench"); pauto.add_argument("--distance", type=int, default=3); pauto.add_argument("--rounds", type=int, default=3); pauto.add_argument("--trials", type=int, default=50); pauto.add_argument("--out", default="bench_out/summary.csv")
    pplot = sub.add_parser("plot"); pplot.add_argument("csv"); pplot.add_argument("--out")
    preal = sub.add_parser("realtime"); preal.add_argument("--decoder", default="mwpm"); preal.add_argument("--distance", type=int, default=3); preal.add_argument("--rounds", type=int, default=3); preal.add_argument("--steps", type=int, default=200); preal.add_argument("--out", default="bench_out/realtime_latency.csv")
    args = p.parse_args(argv)
    if args.cmd == "sweep":
        sweep(args.decoder, args.p, distance=args.distance, rounds=args.rounds, trials=args.trials, out_csv=args.out); return 0
    if args.cmd == "autobench":
        autobench(distance=args.distance, rounds=args.rounds, trials=args.trials, out_csv=args.out); return 0
    if args.cmd == "plot":
        plot(args.csv, args.out); return 0
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


def realtime(decoder: str = "mwpm", distance: int=3, rounds: int=3, steps: int=200, out_csv: str="bench_out/realtime_latency.csv"):
    import csv
    import os
    import random
    import time

    from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout
    cfg = AegisConfig(distance=distance, rounds=rounds, decoder_type=decoder)
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)
    nX = len(rt.builder.node_order("X")); nZ = len(rt.builder.node_order("Z"))
    lat = []
    random.seed(7)
    for _ in range(steps):
        sX = [random.randint(0,1) for _ in range(nX)]
        sZ = [random.randint(0,1) for _ in range(nZ)]
        t0 = time.perf_counter()
        _ = rt.decode_from_syndromes_uniform(sX, sZ)
        t1 = time.perf_counter()
        lat.append(t1-t0)
    lat.sort()
    p50 = lat[int(0.50*len(lat))-1]; p95 = lat[int(0.95*len(lat))-1]; p99 = lat[int(0.99*len(lat))-1]
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["metric","seconds"])
        for k,v in (("p50",p50),("p95",p95),("p99",p99)):
            w.writerow([k, v])
    return out_csv
