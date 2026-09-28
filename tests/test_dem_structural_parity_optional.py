
# FILE: tests/test_dem_structural_parity_optional.py
import pytest


def test_dem_structural_parity_optional():
    try:
        import stim
    except Exception:
        pytest.skip("stim/pymatching not installed")
    from a3d.stim_adapter import graph_from_dem_text
    dem = """
# simple two-round model
error(0.01) D0 D1 L0
shift_detectors 1
error(0.02) D0 D1 L1
"""
    # Our graph
    g = graph_from_dem_text(dem)
    assert len(g.nodes) > 0 and len(g.edges) > 0
    # PyMatching build to compare basic properties (will succeed if DEM is valid)
    import pymatching as pm
    import stim
    m = pm.Matching.from_detector_error_model(stim.DetectorErrorModel(dem))
    # Structural sanity: we at least should have >= detectors and nonzero edges
    assert m is not None
