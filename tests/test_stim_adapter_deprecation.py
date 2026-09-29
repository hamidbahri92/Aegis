from __future__ import annotations

import pytest

from a3d.stim_adapter import graph_from_dem_text


def test_legacy_dem_projection_warns_before_lossy_conversion():
    with pytest.warns(DeprecationWarning, match="approximate legacy projection"):
        graph = graph_from_dem_text("error(0.01) D0 D1")

    assert graph.nodes
    assert graph.edges
