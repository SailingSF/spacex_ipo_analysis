"""Matplotlib styling and thin chart-helper wrappers for the SpaceX analysis.

This module sets up a consistent visual identity (segment colors, fonts, a clean
spine style) and provides small helpers for the common chart types we'll need in
the analyst report. It does NOT generate any charts on its own.

Design intent: the report targets a tech audience (AI / Space), so the default
palette is distinct per segment and the helpers favor clarity over financial-deck
density.

Example (later, when we actually build figures)
-----------------------------------------------
>>> from analysis import charts, data
>>> charts.apply_style()
>>> d = data.load_all()
>>> rev = data.wide(d["segment_pl"], "segment", filt={"line_item": "Revenue"})
>>> ax = charts.grouped_bar(rev)         # returns an Axes; caller saves
>>> charts.save(ax.figure, "segment_revenue")
"""
from __future__ import annotations

import os

import matplotlib as mpl
import matplotlib.pyplot as plt

FIGURES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "figures"))

# Segment color identity (reused across every figure for instant recognition).
SEGMENT_COLORS = {
    "Space": "#1b3a6b",        # deep blue
    "Connectivity": "#2e9e8f",  # teal
    "AI": "#e07a3f",            # warm orange
    "Total Reportable Segments": "#6b6b6b",
    "Consolidated": "#222222",
}

# Generic sequential palette for non-segment series.
PALETTE = ["#1b3a6b", "#2e9e8f", "#e07a3f", "#9b59b6", "#c0392b", "#7f8c8d"]


def apply_style() -> None:
    """Apply the house matplotlib rcParams. Call once before plotting."""
    mpl.rcParams.update({
        "figure.figsize": (9, 5),
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "axes.prop_cycle": mpl.cycler(color=PALETTE),
    })


def color_for(label: str) -> str:
    """Return the consistent color for a segment/series label."""
    return SEGMENT_COLORS.get(label, PALETTE[0])


def save(fig, name: str, ext: str = "png") -> str:
    """Save a figure to output/figures/<name>.<ext>; returns the path."""
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = os.path.join(FIGURES_DIR, f"{name}.{ext}")
    fig.savefig(path)
    return path


# --- thin helpers (return an Axes; caller decides titles/saving) -------------

def line(df, ax=None, **kwargs):
    """Line chart of a wide DataFrame (index = x, columns = series)."""
    ax = ax or plt.gca()
    for col in df.columns:
        ax.plot(df.index.astype(str), df[col], marker="o",
                label=str(col), color=color_for(str(col)), **kwargs)
    ax.legend()
    return ax


def grouped_bar(df, ax=None, width=0.8, **kwargs):
    """Grouped bar chart of a wide DataFrame (index = groups, columns = series)."""
    import numpy as np
    ax = ax or plt.gca()
    groups = list(df.index.astype(str))
    series = list(df.columns)
    x = np.arange(len(groups))
    n = len(series)
    bw = width / max(n, 1)
    for i, col in enumerate(series):
        ax.bar(x + i * bw - width / 2 + bw / 2, df[col].values, bw,
               label=str(col), color=color_for(str(col)), **kwargs)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.legend()
    return ax
