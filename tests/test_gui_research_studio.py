from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_research_studio_renders_headlessly():
    app_path = Path(__file__).parents[1] / "gui" / "app.py"
    app = AppTest.from_file(app_path, default_timeout=15).run()

    assert not app.exception
    assert app.title[0].value == "Aegis QEC"

    headers = [item.value for item in app.header]
    assert "Research Studio" in headers
    assert "Decoder and circuit lab" in headers

    button_keys = {
        button.key
        for button in app.button
        if button.key is not None
    }
    assert {
        "studio_create_project",
        "studio_run_discovery",
        "studio_audit_project",
        "studio_build_submission",
    } <= button_keys
