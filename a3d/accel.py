
# FILE: a3d/accel.py
from __future__ import annotations

ACCEL_OK = False
try:
    import numba  # type: ignore
    ACCEL_OK = True
except Exception:  # pragma: no cover
    numba = None  # type: ignore

def maybe_jit(fn):
    if ACCEL_OK:
        return numba.njit(cache=True)(fn)  # type: ignore[misc]
    return fn
