from __future__ import annotations

import json

import pytest

from aegis_qec.experiment import load_experiment_manifest
from aegis_qec.template_catalog import (
    get_experiment_template,
    list_experiment_templates,
    write_experiment_template,
)


def test_catalog_lists_expected_learning_and_research_paths():
    templates = {item["name"]: item for item in list_experiment_templates()}
    assert {
        "first-study",
        "shot-explanation",
        "decoder-comparison",
        "scaling-campaign",
        "practitioner-regression",
    } <= set(templates)
    assert templates["first-study"]["level"] == "beginner"
    assert templates["scaling-campaign"]["level"] == "advanced"


@pytest.mark.parametrize(
    "name",
    [
        "first-study",
        "shot-explanation",
        "decoder-comparison",
        "scaling-campaign",
        "practitioner-regression",
    ],
)
def test_every_packaged_template_is_a_valid_experiment_manifest(tmp_path, name):
    value = get_experiment_template(name)
    assert value["schema_version"] == 1

    output = tmp_path / f"{name}.json"
    write_experiment_template(name, str(output))
    loaded = load_experiment_manifest(str(output))
    assert loaded["operation"] == value["operation"]


def test_template_materialization_is_stable_json(tmp_path):
    output = tmp_path / "experiment.json"
    write_experiment_template("shot-explanation", str(output))
    value = json.loads(output.read_text(encoding="utf-8"))
    assert value["name"] == "explain-one-surface-code-shot"
    assert value["operation"] == "explain"


def test_template_does_not_overwrite_without_explicit_force(tmp_path):
    output = tmp_path / "experiment.json"
    output.write_text("keep-me", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_experiment_template("first-study", str(output))

    assert output.read_text(encoding="utf-8") == "keep-me"

    write_experiment_template(
        "first-study",
        str(output),
        overwrite=True,
    )
    assert json.loads(output.read_text(encoding="utf-8"))["operation"] == "study"


def test_unknown_template_has_discoverable_error():
    with pytest.raises(ValueError, match="Available"):
        get_experiment_template("does-not-exist")
