
# FILE: scripts/dem_cross_validate.py
from __future__ import annotations

import argparse


def main(dem_path: str) -> int:
    try:
        import pymatching as pm  # optional
    except Exception:
        print("PyMatching not installed; skipping cross-validation.")
        return 0
    from a3d.stim_adapter import graph_from_dem_file
    g = graph_from_dem_file(dem_path)
    # Build a simple Matching from DEM via PyMatching for comparison
    try:
        import stim
        dem = stim.DetectorErrorModel.open(dem_path)
        m = pm.Matching.from_detector_error_model(dem)
        print("PyMatching built a matching with", m.H.shape, "parity-check shape")
    except Exception as e:
        print("Stim not installed or failed to parse DEM:", e)
    # We could add structural comparison here (node/edge counts)
    print("Aegis graph:", len(g.nodes), "nodes,", len(g.edges), "edges.")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dem", help="Path to DEM file")
    args = parser.parse_args()
    raise SystemExit(main(args.dem))
