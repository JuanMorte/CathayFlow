"""One chart style for the research notebooks (matplotlib), so every figure can go on a slide as it is.

Light surface, thin marks, hairline grid, text in ink (never in the series colour). The colours are a
fixed order checked for colour-blind separation between neighbours; use them in this order.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
LIGHT_BLUE = "#b7d3f6"       # a band or a de-emphasised mark of the blue series
GREY = "#898781"             # reference lines, baselines for comparison
INK, SECOND_INK, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def use_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
        "font.family": "sans-serif", "font.size": 10.5,
        "text.color": INK, "axes.labelcolor": SECOND_INK, "xtick.color": GREY, "ytick.color": GREY,
        "xtick.labelcolor": SECOND_INK, "ytick.labelcolor": SECOND_INK,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "xtick.major.size": 0, "ytick.major.size": 0,
        "lines.linewidth": 2, "lines.markersize": 7,
        "legend.frameon": False, "legend.fontsize": 9.5,
        "axes.prop_cycle": plt.cycler(color=[BLUE, ORANGE, AQUA, YELLOW]),
    })


def title(ax, text: str, note: str | None = None) -> None:
    """A left-aligned title that states the finding, with a smaller line for what is plotted."""
    ax.set_title(text, loc="left", fontsize=12.5, fontweight="bold", color=INK, pad=22 if note else 10)
    if note:
        ax.text(0, 1.03, note, transform=ax.transAxes, fontsize=9.5, color=SECOND_INK, va="bottom")
