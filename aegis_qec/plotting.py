from __future__ import annotations

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def new_agg_figure(
    *,
    figsize: tuple[float, float],
):
    """Create a display-independent Matplotlib figure and axes.

    Research artifact generation must work on headless Linux and Windows
    machines without selecting Tk, Qt, or another desktop GUI backend.
    """
    figure = Figure(figsize=figsize)
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    return figure, axes
