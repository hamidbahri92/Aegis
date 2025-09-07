# FILE: main_export_header.py
from __future__ import annotations
import os
from a3d.analog_lut import GKPLUTBuilder
from a3d.export import export_fixed_point_header


def main():
    os.makedirs("out", exist_ok=True)
    lut = GKPLUTBuilder().build_lut()
    arrays = {"x": lut["x"], "Lq": lut["Lq"], "Lp": lut["Lp"]}
    scales = {"x": 1e-3, "Lq": 1e-2, "Lp": 1e-2}
    meta = {"note": "toy LUT export"}
    export_fixed_point_header("out/gkp_lut.h", arrays, scales, meta)
    print("Wrote out/gkp_lut.h")


if __name__ == "__main__":
    main()
