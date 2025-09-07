# FILE: tests/test_syndrome_locality.py
import numpy as np
from a3d.graph import RotatedSurfaceLayout
from a3d.noise_physical import syndromes_from_pauli_errors


def test_single_X_error_flips_two_Z_checks_interior():
    d = 3
    rounds = 2
    lay = RotatedSurfaceLayout(d)
    # Place a single X error at center data qubit at t=0
    dq = (1, 1)
    pauli_errors = { (dq, 0): "X" }

    sX, sZ = syndromes_from_pauli_errors(lay, rounds, pauli_errors, p_meas=0.0)
    # first-time-slice block length for Z stabilizers:
    nZ = len(lay.stabilizer_coords()["Z"])
    first_block = sZ[:nZ]
    # interior single X should flip exactly two Z checks at t=0
    assert sum(first_block) == 2
