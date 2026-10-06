from __future__ import annotations

from importlib import resources
import json
from pathlib import Path
from typing import Any


_TEMPLATE_METADATA: dict[str, dict[str, str]] = {
    "first-study": {
        "title": "First surface-code study",
        "level": "beginner",
        "audience": "students",
        "description": (
            "Measure logical error rates for small rotated surface codes with "
            "confidence intervals and reproducible artifacts."
        ),
    },
    "shot-explanation": {
        "title": "Explain one QEC shot",
        "level": "beginner",
        "audience": "students",
        "description": (
            "Inspect fired detectors, matching pairs, correction paths, and "
            "the logical outcome for one deterministic circuit-level shot."
        ),
    },
    "decoder-comparison": {
        "title": "Exact-shot decoder comparison",
        "level": "intermediate",
        "audience": "decoder researchers",
        "description": (
            "Compare standard and correlated PyMatching adapters on the exact "
            "same detector-shot matrix."
        ),
    },
    "scaling-campaign": {
        "title": "Resumable distance-scaling campaign",
        "level": "advanced",
        "audience": "researchers",
        "description": (
            "Collect a resumable Sinter campaign across distances and physical "
            "error rates for later finite-size scaling analysis."
        ),
    },
    "practitioner-regression": {
        "title": "Practitioner regression campaign",
        "level": "intermediate",
        "audience": "QEC engineering teams",
        "description": (
            "Run a compact deterministic campaign suitable for CI regression "
            "tracking of logical error rates and decoder behavior."
        ),
    },
}


def _template_resource(name: str):
    if name not in _TEMPLATE_METADATA:
        raise ValueError(
            f"Unknown experiment template {name!r}. Available: "
            + ", ".join(sorted(_TEMPLATE_METADATA))
        )
    return resources.files("aegis_qec").joinpath(
        "templates",
        f"{name}.json",
    )


def list_experiment_templates() -> list[dict[str, str]]:
    """Return metadata for experiment templates shipped in the wheel."""
    result = []
    for name in sorted(_TEMPLATE_METADATA):
        item = {"name": name}
        item.update(_TEMPLATE_METADATA[name])
        result.append(item)
    return result


def get_experiment_template(name: str) -> dict[str, Any]:
    """Load one packaged experiment manifest as a Python dictionary."""
    resource = _template_resource(name)
    with resource.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Packaged template {name!r} is not a JSON object.")
    return value


def write_experiment_template(
    name: str,
    output_path: str,
    *,
    overwrite: bool = False,
) -> str:
    """Materialize a packaged experiment template for editing or versioning."""
    destination = Path(output_path)
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"{destination} already exists. Use overwrite=True or --force "
            "to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    template = get_experiment_template(name)
    destination.write_text(
        json.dumps(template, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return str(destination)
