
# FILE: scripts/train_correlations.py
from __future__ import annotations

import csv
import statistics

from a3d.correlation_model import CorrelationParams


def main(in_csv: str = "logs/decoding_events.csv", out_json: str = "corr_params.json") -> int:
    try:
        counts = []
        with open(in_csv, "r", encoding="utf-8") as f:
            r = csv.reader(f)
            for row in r:
                if len(row) >= 3:
                    try:
                        counts.append(int(row[2]))
                    except Exception:
                        pass
        if counts:
            # heuristic: more edges → raise neighbor bonus slightly; bound ranges
            med = statistics.median(counts)
            params = CorrelationParams(neighbor_bonus=min(0.3, 0.05 + 0.01*med), boundary_penalty=0.05, time_space_bonus=0.05)
        else:
            params = CorrelationParams()
        params.to_json(out_json)
        print("Wrote", out_json)
        return 0
    except Exception as e:
        print("Training failed:", e)
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
