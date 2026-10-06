from __future__ import annotations

from matplotlib.backends.backend_agg import FigureCanvasAgg

from aegis_qec.plotting import new_agg_figure


def test_research_figures_use_display_independent_agg_canvas():
    figure, axes = new_agg_figure(figsize=(4.0, 3.0))
    assert isinstance(figure.canvas, FigureCanvasAgg)
    axes.plot([0, 1], [0, 1])
    figure.canvas.draw()
    figure.clear()
