from importlib.metadata import version

import aegis_qec


def test_public_namespace_matches_distribution_name():
    assert aegis_qec.AegisConfig is not None
    assert aegis_qec.DecoderRuntime is not None
    assert aegis_qec.RotatedSurfaceLayout is not None
    assert version("aegis-qec") == "1.1.0"
    assert aegis_qec.__version__ == "1.1.0"
