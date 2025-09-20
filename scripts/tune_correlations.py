
# FILE: scripts/tune_correlations.py
from __future__ import annotations

import argparse
import itertools
import json

from bench.cli import sweep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--distance", type=int, default=3)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--p", nargs="+", type=float, default=[0.02,0.06])
    ap.add_argument("--out", default="corr_params.json")
    args = ap.parse_args()

    best = None
    grid = {
        "neighbor_bonus": [0.05, 0.10, 0.15],
        "boundary_penalty": [0.03, 0.05, 0.08],
        "time_space_bonus": [0.03, 0.05, 0.08],
    }
    for nb, bp, ts in itertools.product(*grid.values()):
        params = {"neighbor_bonus": nb, "boundary_penalty": bp, "time_space_bonus": ts}
        # Write a temp json
        tmp = "_tmp_corr.json"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(params, f)
        # Evaluate MWPM-Corr with these params
        data = sweep("mwpm_corr", args.p, distance=args.distance, rounds=args.rounds, trials=args.trials, corr_params=tmp)
        # Objective: mean logical rate
        score = sum(r for _, r in data) / max(1, len(data))
        if best is None or score < best[0]:
            best = (score, params.copy())
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(best[1], f, indent=2)
    print("Wrote", args.out, "score=", best[0])

if __name__ == "__main__":
    main()
