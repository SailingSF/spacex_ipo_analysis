"""Load the extracted SpaceX S-1 CSVs into tidy pandas DataFrames.

The CSVs (see ../csv and ../MANIFEST.md) are long/tidy format. This module is a
thin, dependable loader layer: it reads each file, applies consistent dtypes and
an ordered categorical for `period`, and offers a couple of reshaping helpers.

No analysis is performed here.

Example
-------
>>> from analysis import data
>>> d = data.load_all()
>>> d["income_statement"].head()
>>> data.wide(d["segment_pl"], index="line_item", columns="period",
...           filt={"segment": "Connectivity"})
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd

CSV_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "csv"))

# Canonical period ordering (oldest -> newest), used for sorting/plotting.
PERIOD_ORDER = ["FY2023", "FY2024", "FY2025", "Q1-2025", "Q1-2026"]
# Chronological ordering that interleaves quarters with years, if ever needed.
PERIOD_ORDER_CHRONO = ["FY2023", "FY2024", "Q1-2025", "FY2025", "Q1-2026"]

SEGMENTS = ["Space", "Connectivity", "AI"]

# Every CSV in csv/ that is data (README/validate excluded).
DATASETS = [
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "comprehensive_income",
    "segment_pl",
    "segment_supplemental",
    "segment_kpi",
    "segment_adjusted_ebitda",
    "adjusted_ebitda_consolidated",
    "revenue_disaggregation",
    "revenue_geography",
    "debt_schedule",
    "capitalization",
    "inventory_detail",
    "ppe_detail",
    "restructuring_rollforward",
    "space_revenue_mix_pct",
    "other_metrics",
    "launch_detail",  # internal (Starlink) vs customer Falcon launch split, from S-1 footnote
]


def _path(name: str) -> str:
    return os.path.join(CSV_DIR, f"{name}.csv")


def load(name: str) -> pd.DataFrame:
    """Load a single dataset by name (without .csv), with period ordered if present."""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset {name!r}. Options: {', '.join(DATASETS)}")
    df = pd.read_csv(_path(name))
    if "period" in df.columns:
        df["period"] = pd.Categorical(df["period"], categories=PERIOD_ORDER, ordered=True)
    return df


@lru_cache(maxsize=1)
def load_all() -> dict[str, pd.DataFrame]:
    """Load every dataset into a dict keyed by dataset name (cached)."""
    return {name: load(name) for name in DATASETS}


def wide(df: pd.DataFrame, index: str, columns: str = "period",
         values: str = "value", filt: dict | None = None) -> pd.DataFrame:
    """Pivot a tidy frame to wide (statement-style) form.

    Parameters
    ----------
    index   : column to use as row labels (e.g. "line_item").
    columns : column to spread across (default "period").
    values  : value column (default "value").
    filt    : optional {column: value} equality filters applied first
              (e.g. {"segment": "Connectivity"}).
    """
    sub = df
    if filt:
        for col, val in filt.items():
            sub = sub[sub[col] == val]
    out = sub.pivot_table(index=index, columns=columns, values=values,
                          aggfunc="first", observed=True)
    if columns == "period":
        ordered = [p for p in PERIOD_ORDER if p in out.columns]
        out = out[ordered]
    return out


def series(df: pd.DataFrame, line_item: str, item_col: str = "line_item",
           segment: str | None = None) -> pd.Series:
    """Return a single line item as a period-indexed Series (ordered)."""
    sub = df[df[item_col] == line_item]
    if segment is not None and "segment" in df.columns:
        sub = sub[sub["segment"] == segment]
    s = sub.set_index("period")["value"].sort_index()
    return s
