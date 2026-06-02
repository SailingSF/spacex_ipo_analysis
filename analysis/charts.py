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


def finish(fig=None, *, pad: float = 1.15, h_pad: float = 1.0, w_pad: float = 1.0,
           rect: tuple[float, float, float, float] | None = None) -> plt.Figure:
    """Apply ``tight_layout`` so titles, legends, and twin axes do not clip."""
    fig = fig or plt.gcf()
    try:
        fig.tight_layout(pad=pad, h_pad=h_pad, w_pad=w_pad, rect=rect)
    except Exception:
        pass
    return fig


def pad_ylim(ax, *, top: float = 0.12, bottom: float = 0.04) -> None:
    """Expand y-limits so bar/value labels and error bars clear the data."""
    lo, hi = ax.get_ylim()
    span = hi - lo if hi != lo else abs(hi) or 1.0
    ax.set_ylim(lo - span * bottom, hi + span * top)


def legend_panel(ax, *, loc: str = "upper left", ncol: int = 1, fontsize=None,
                 bbox_to_anchor=None, **kwargs):
    """In-axes legend for multi-panel figures (default ``upper left``)."""
    kw = dict(loc=loc, frameon=False, ncol=ncol, **kwargs)
    if bbox_to_anchor is not None:
        kw["bbox_to_anchor"] = bbox_to_anchor
    if fontsize is not None:
        kw["fontsize"] = fontsize
    return ax.legend(**kw)


def legend_twin_panel(ax, ax2, *, loc: str = "upper left", ncol: int = 1, fontsize=None,
                      handles=None, labels=None, bbox_to_anchor=None, **kwargs):
    """Merged legend for ``twinx`` kept inside one panel (default ``upper left``)."""
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    h = (handles if handles is not None else h1 + h2)
    lab = (labels if labels is not None else l1 + l2)
    kw = dict(handles=h, labels=lab, loc=loc, frameon=False, ncol=ncol, **kwargs)
    if fontsize is not None:
        kw["fontsize"] = fontsize
    if bbox_to_anchor is not None:
        kw["bbox_to_anchor"] = bbox_to_anchor
    return ax.legend(**kw)


def finish_pair(fig=None, *, wspace: float = 0.32, hspace: float = 0.35,
                  top: float = 0.92, bottom: float = 0.10) -> plt.Figure:
    """Layout pass for 1×N or 2×N subplot figures — only gap tuning, no right-margin squeeze."""
    fig = fig or plt.gcf()
    fig.subplots_adjust(wspace=wspace, hspace=hspace, top=top, bottom=bottom)
    return fig


def legend_outside(ax, *, loc: str = "upper left", ncol: int = 1, fontsize=None,
                   title: str | None = None, **kwargs):
    """Place legend just outside the right edge of the axes (single-panel figures)."""
    kw = dict(loc=loc, bbox_to_anchor=(1.02, 1), borderaxespad=0, frameon=False,
              ncol=ncol, **kwargs)
    if fontsize is not None:
        kw["fontsize"] = fontsize
    if title is not None:
        kw["title"] = title
    return ax.legend(**kw)


def legend_merged(ax, ax2, *, loc: str = "upper left", ncol: int = 1, fontsize=None,
                  bbox_to_anchor=(1.02, 1), **kwargs):
    """Single legend for a primary + twin (``twinx``) axes pair."""
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    kw = dict(handles=h1 + h2, labels=l1 + l2, loc=loc, bbox_to_anchor=bbox_to_anchor,
              borderaxespad=0, frameon=False, ncol=ncol, **kwargs)
    if fontsize is not None:
        kw["fontsize"] = fontsize
    return ax.legend(**kw)


_ANNO_BBOX = dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.88, edgecolor="none")


def annotate_clear(ax, *args, **kwargs):
    """``annotate`` with a light background so labels stay readable on busy plots."""
    kwargs.setdefault("bbox", _ANNO_BBOX)
    return ax.annotate(*args, **kwargs)


def save(fig, name: str, ext: str = "png", *, layout: bool = True,
         layout_rect: tuple[float, float, float, float] | None = None) -> str:
    """Save a figure to output/figures/<name>.<ext>; returns the path."""
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = os.path.join(FIGURES_DIR, f"{name}.{ext}")
    if layout:
        finish(fig, rect=layout_rect)
    fig.savefig(path)
    return path


# --- thin helpers (return an Axes; caller decides titles/saving) -------------

def line(df, ax=None, **kwargs):
    """Line chart of a wide DataFrame (index = x, columns = series)."""
    ax = ax or plt.gca()
    for col in df.columns:
        ax.plot(df.index.astype(str), df[col], marker="o",
                label=str(col), color=color_for(str(col)), **kwargs)
    ax.legend(loc="best", fontsize=mpl.rcParams["font.size"] - 0.5)
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
    ax.legend(loc="best", fontsize=mpl.rcParams["font.size"] - 0.5)
    return ax


def hbar_range(df, ax=None, low="low", high="high", label="method", point=None,
               flag="source_flag", external_flag="external", colors=None,
               height=0.62, **kwargs):
    """Horizontal range ("football field") bars: one low-high bar per row.

    Rows are valuation methods; ``low``/``high`` are the range columns (same units).
    An optional ``point`` column drops a diamond marker on each bar (e.g. a base or
    probability-weighted estimate). Rows whose ``flag`` column equals ``external_flag``
    are drawn **hatched + outlined** to mark non-S-1 (external) data; S-1 bars are
    solid — so provenance is never ambiguous. First row renders at the top. Returns
    the Axes (caller sets titles / axis labels / saves).
    """
    import numpy as np
    ax = ax or plt.gca()
    n = len(df)
    y = np.arange(n)
    labels = df[label].astype(str).tolist() if label in df.columns else [str(i) for i in df.index]
    los = df[low].to_numpy(dtype=float)
    his = df[high].to_numpy(dtype=float)
    flags = df[flag].astype(str).tolist() if (flag and flag in df.columns) else [""] * n
    if colors is None:
        colors = [PALETTE[i % len(PALETTE)] for i in range(n)]
    elif isinstance(colors, str):
        colors = [colors] * n
    pts = df[point].to_numpy(dtype=float) if (point and point in df.columns) else None
    for i in range(n):
        is_ext = flags[i] == external_flag
        ax.barh(y[i], his[i] - los[i], left=los[i], height=height,
                color=colors[i], alpha=0.45 if is_ext else 0.85,
                hatch="//" if is_ext else None,
                edgecolor=colors[i] if is_ext else "none",
                linewidth=1.6 if is_ext else 0, zorder=3, **kwargs)
        if pts is not None and np.isfinite(pts[i]):
            ax.scatter(pts[i], y[i], marker="D", s=42, color="#111",
                       zorder=5, edgecolor="white", linewidth=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # first row on top
    return ax
