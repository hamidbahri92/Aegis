"""Public package namespace for Aegis QEC.

The historical implementation package is named a3d. aegis_qec is the stable,
user-facing namespace and re-exports the supported top-level API while keeping
existing a3d imports compatible.
"""

from importlib.metadata import PackageNotFoundError, version

from a3d import AegisConfig, DecoderRuntime, RotatedSurfaceLayout

from .research import run_surface_code_study, wilson_interval, write_study_artifacts

try:
    __version__ = version("aegis-qec")
except PackageNotFoundError:  # source checkout
    __version__ = "0+unknown"

__all__ = [
    "AegisConfig",
    "DecoderRuntime",
    "RotatedSurfaceLayout",
    "run_surface_code_study",
    "wilson_interval",
    "write_study_artifacts",
    "__version__",
]
