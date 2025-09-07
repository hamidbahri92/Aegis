# FILE: main_threshold.py
from __future__ import annotations
import os
import numpy as np
import matplotlib.pyplot as plt

from a3d.sweep import sweep_physical_p
from a3d.export import export_csv


def main():
    os.makedirs("out", exist_ok=True)
    distances = [3, 5, 7]
    rounds = 6
    p_values = np.geomspace(1e-4, 5e-2, 12)
    trials = 200

    rows = sweep_physical_p(distances, rounds, p_values, trials=trials, seed=7)
    export_csv("out/threshold.csv", rows)

    # Plot S-curves
    groups = {}
    for r in rows:
        groups.setdefault((r["distance"], r["p"]), []).append(r["success"])
    fig, ax = plt.subplots(figsize=(6.5,4.3))
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
    ax.set_title("Threshold-style sweep (success curves)")
    ax.grid(True, ls="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig("out/threshold.png", dpi=150)
    print("Wrote threshold plot to out/threshold.png")


if __name__ == "__main__":
    main()
