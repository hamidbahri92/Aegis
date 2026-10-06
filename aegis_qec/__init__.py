"""Public package namespace for Aegis QEC.

The historical implementation package is named a3d. aegis_qec is the stable,
user-facing namespace and re-exports the supported top-level API while keeping
existing a3d imports compatible.
"""

from importlib.metadata import PackageNotFoundError, version

from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

from .campaign import run_campaign, write_campaign_summary
from .comparison import compare_decoders_exact_shots, write_comparison_json
from .dataset import (
    evaluate_decoders_on_dataset,
    extract_dem_mechanisms,
    generate_qec_dataset,
    inspect_qec_dataset,
    write_dataset_evaluation_json,
)
from .decoder_plugins import (
    DecoderPluginAdapter,
    available_decoders,
    custom_decoder_registry,
    normalize_decoder_plugin,
    validate_decoder_plugin,
)
from .discovery import (
    load_discovery_manifest,
    pareto_front,
    run_discovery,
    write_discovery_starter,
    write_discovery_template,
)
from .experiment import (
    create_research_bundle,
    load_experiment_manifest,
    run_experiment_manifest,
    verify_research_bundle,
)
from .explain import explain_surface_code_shot, write_shot_explanation
from .io_decode import predict_observables_from_files
from .paper import build_submission_package, verify_submission_package
from .project import (
    audit_research_project,
    freeze_research_protocol,
    load_research_project,
    run_research_project,
    verify_protocol_lock,
    write_research_project_template,
)
from .research import run_surface_code_study, wilson_interval, write_study_artifacts
from .scaling import fit_surface_code_scaling, load_campaign_json, write_scaling_artifacts
from .template_catalog import (
    get_experiment_template,
    list_experiment_templates,
    write_experiment_template,
)

try:
    __version__ = version("aegis-qec")
except PackageNotFoundError:  # source checkout
    __version__ = "0+unknown"

__all__ = [
    "AegisConfig",
    "DecoderPluginAdapter",
    "DecoderRuntime",
    "RotatedSurfaceLayout",
    "audit_research_project",
    "available_decoders",
    "build_submission_package",
    "compare_decoders_exact_shots",
    "create_research_bundle",
    "custom_decoder_registry",
    "evaluate_decoders_on_dataset",
    "extract_dem_mechanisms",
    "explain_surface_code_shot",
    "fit_surface_code_scaling",
    "freeze_research_protocol",
    "generate_qec_dataset",
    "get_experiment_template",
    "inspect_qec_dataset",
    "list_experiment_templates",
    "load_discovery_manifest",
    "load_campaign_json",
    "load_experiment_manifest",
    "load_research_project",
    "normalize_decoder_plugin",
    "pareto_front",
    "predict_observables_from_files",
    "run_campaign",
    "run_discovery",
    "run_experiment_manifest",
    "run_research_project",
    "run_surface_code_study",
    "validate_decoder_plugin",
    "wilson_interval",
    "write_campaign_summary",
    "write_comparison_json",
    "write_dataset_evaluation_json",
    "write_discovery_starter",
    "write_discovery_template",
    "write_scaling_artifacts",
    "write_shot_explanation",
    "write_study_artifacts",
    "write_experiment_template",
    "verify_protocol_lock",
    "verify_research_bundle",
    "verify_submission_package",
    "write_research_project_template",
    "__version__",
]
