from a3d.config import AegisConfig


def test_default_configuration_uses_sparse_blossom_without_experimental_polish():
    cfg = AegisConfig()

    assert cfg.decoder_type == "mwpm"
    assert cfg.run_certificate is False
