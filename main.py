# FILE: main.py
from __future__ import annotations
import numpy as np

from a3d.config import AegisConfig
from a3d.graph import RotatedSurfaceLayout
from a3d.noise_physical import generate_pauli_errors, syndromes_from_pauli_errors
from a3d.runtime import DecoderRuntime


def main():
    cfg = AegisConfig(distance=3, rounds=4)
    lay = RotatedSurfaceLayout(cfg.distance)
    rt = DecoderRuntime(cfg, lay)

    rng = np.random.default_rng(7)
    errs = generate_pauli_errors(lay, cfg.rounds, p_phys=1e-3, rng=rng)
    sX, sZ = syndromes_from_pauli_errors(lay, cfg.rounds, errs)

    resX, resZ = rt.decode_from_syndromes_uniform(sX, sZ)
    print(f"Decode complete. X(avg_cost)={resX.avg_cost:.3f}, Z(avg_cost)={resZ.avg_cost:.3f}")


if __name__ == "__main__":
    main()
