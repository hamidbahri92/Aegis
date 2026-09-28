import pytest


def test_decode_from_dem_requires_detection_events():
    pytest.importorskip("stim")
    from a3d.decoder_mwpm_pm import PyMatchingMWPMDecoder

    decoder = PyMatchingMWPMDecoder()
    dem = "error(0.01) D0 D1\n"
    with pytest.raises(ValueError, match="observed syndrome"):
        decoder.decode_from_dem(dem)


def test_decode_from_dem_accepts_explicit_syndrome():
    pytest.importorskip("stim")
    from a3d.decoder_mwpm_pm import PyMatchingMWPMDecoder

    decoder = PyMatchingMWPMDecoder()
    dem = "error(0.01) D0 D1\n"
    prediction = decoder.decode_from_dem(dem, [1, 1])
    assert prediction is not None
