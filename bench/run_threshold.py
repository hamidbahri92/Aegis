
# FILE: bench/run_threshold.py
from __future__ import annotations

import csv
from typing import List, Tuple

from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout


def sweep_threshold(distances: List[int], rounds: int, ps: List[float], decoder: str) -> List[Tuple[int,float,float]]:
    results = []
    for d in distances:
        cfg = AegisConfig(distance=d, rounds=rounds, decoder_type=decoder)
        lay = RotatedSurfaceLayout(cfg.distance)
        rt = DecoderRuntime(cfg, lay)
        nX = len(rt.builder.node_order("X"))
        nZ = len(rt.builder.node_order("Z"))
        import random
        random.seed(42)
        for p in ps:
            bad = 0; trials = 200
            for _ in range(trials):
                sX = [1 if random.random()<p else 0 for _ in range(nX)]
                sZ = [1 if random.random()<p else 0 for _ in range(nZ)]
                resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
                if resX.avg_cost<=0 and sum(sX)>0: bad+=1
                if resZ.avg_cost<=0 and sum(sZ)>0: bad+=1
            results.append((d, p, bad/max(1,2*trials)))
    return results

def main():
    data = sweep_threshold([3,5], rounds=3, ps=[0.02,0.05,0.08], decoder="mwpm")
    with open("threshold_results.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(["distance","p","logical_rate"])
        for row in data: w.writerow(row)
    print("Wrote threshold_results.csv")

if __name__ == "__main__":
    main()
