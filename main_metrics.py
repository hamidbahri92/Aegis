# FILE: main_metrics.py
from __future__ import annotations
import os
import numpy as np
import matplotlib.pyplot as plt

from a3d.sweep import sweep_physical_p
from a3d.export import export_csv, export_parquet


def main():
    os.makedirs("out", exist_ok=True)
    distances = [3, 5]
    rounds = 5
    p_values = np.geomspace(1e-4, 5e-2, 8)
    trials = 200

    rows = sweep_physical_p(distances, rounds, p_values, trials=trials, seed=42)

    export_csv("out/metrics.csv", rows)
    try:
        export_parquet("out/metrics.parquet", rows)
    except Exception as e:
        print(f"Parquet export skipped: {e}")

    # Simple plot: success rate vs p for each distance
    groups = {}
    for r in rows:
        groups.setdefault((r["distance"], r["p"]), []).append(r["success"])
    fig, ax = plt.subplots(figsize=(6,4))
    for d in distances:
        xs = []
        ys = []
        for p in p_values:
            xs.append(p)
            succ = groups.get((d, float(p)), [])
            ys.append(np.mean(succ) if succ else 0.0)
        ax.plot(xs, ys, marker="o", label=f"d={d}")
    ax.set_xscale("log")
    ax.set_xlabel("physical error rate p")
    ax.set_ylabel("success rate")
    ax.set_title("Aegis metrics (success rate)")
    ax.grid(True, ls="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig("out/metrics.png", dpi=150)
    print("Wrote metrics to out/metrics.csv and out/metrics.png")


if __name__ == "__main__":
    main()
