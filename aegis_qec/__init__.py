"""Public package namespace for Aegis QEC.

The historical implementation package is named a3d. aegis_qec is the stable,
user-facing namespace and re-exports the supported top-level API while keeping
existing a3d imports compatible.
"""

from importlib.metadata import PackageNotFoundError, version

from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

from .campaign import run_campaign, write_campaign_summary
from .comparison import compare_decoders_exact_shots, write_comparison_json
from .decoder_plugins import available_decoders, custom_decoder_registry
from .experiment import (
    create_research_bundle,
    load_experiment_manifest,
    run_experiment_manifest,
    verify_research_bundle,
)
from .explain import explain_surface_code_shot, write_shot_explanation
from .io_decode import predict_observables_from_files
from .research import run_surface_code_study, wilson_interval, write_study_artifacts
from .scaling import fit_surface_code_scaling, load_campaign_json, write_scaling_artifacts

try:
    __version__ = version("aegis-qec")
except PackageNotFoundError:  # source checkout
    __version__ = "0+unknown"

__all__ = [
    "AegisConfig",
    "DecoderRuntime",
    "RotatedSurfaceLayout",
    "available_decoders",
    "compare_decoders_exact_shots",
    "create_research_bundle",
    "custom_decoder_registry",
    "explain_surface_code_shot",
    "fit_surface_code_scaling",
    "load_campaign_json",
    "load_experiment_manifest",
    "predict_observables_from_files",
    "run_campaign",
    "run_experiment_manifest",
    "run_surface_code_study",
    "wilson_interval",
    "write_campaign_summary",
    "write_comparison_json",
    "write_scaling_artifacts",
    "write_shot_explanation",
    "write_study_artifacts",
    "verify_research_bundle",
    "__version__",
]
