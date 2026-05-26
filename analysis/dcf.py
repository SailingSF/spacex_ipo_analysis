"""Scaffolding for the SpaceX segment-level DCF valuation model.

This is a STRUCTURE ONLY. No forecast assumptions are baked in yet and nothing
runs on import. The intent is to fix the shape of the model so the analyst report
and the code agree on terminology before we start tuning numbers.

Approach (to be filled in):
  1. Forecast revenue per segment (Space / Connectivity / AI) off the FY2023-FY2025
     actuals + Q1-2026 run-rate in csv/.
  2. Apply segment margin assumptions -> EBIT -> NOPAT.
  3. Build unlevered free cash flow:  NOPAT + D&A - capex - delta NWC.
  4. Discount at WACC; add a terminal value (Gordon growth or exit multiple).
  5. Enterprise value -> equity value (net debt from debt_schedule.csv,
     preferred conversion from capitalization.csv) -> implied per-share.
  6. Sensitivity grid: terminal growth x WACC.

Everything below is a placeholder skeleton; replace the `...` / NotImplementedError
bodies when we begin the actual modeling step.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Forecast horizon for the explicit period (years). Tune later.
FORECAST_YEARS = 7
BASE_YEAR = 2025  # last full actual fiscal year in the dataset


@dataclass
class SegmentAssumptions:
    """Per-segment forecast drivers. All values are placeholders (None = TBD)."""
    name: str
    revenue_cagr: float | None = None          # explicit-period revenue growth
    terminal_growth: float | None = None       # perpetuity growth rate
    target_ebit_margin: float | None = None     # steady-state EBIT margin
    capex_pct_revenue: float | None = None       # capex as % of revenue
    da_pct_revenue: float | None = None          # D&A as % of revenue
    nwc_pct_revenue: float | None = None          # net working capital as % of revenue


@dataclass
class ModelAssumptions:
    """Top-level valuation assumptions. Placeholders until we calibrate."""
    wacc: float | None = None                  # discount rate
    tax_rate: float | None = None              # cash tax rate on EBIT
    terminal_method: str = "gordon"            # "gordon" | "exit_multiple"
    exit_ev_ebitda: float | None = None        # used if terminal_method == exit_multiple
    forecast_years: int = FORECAST_YEARS
    base_year: int = BASE_YEAR
    segments: dict[str, SegmentAssumptions] = field(default_factory=dict)


def default_assumptions() -> ModelAssumptions:
    """Return an assumptions object with the three segments stubbed in (no numbers)."""
    return ModelAssumptions(segments={
        "Space": SegmentAssumptions("Space"),
        "Connectivity": SegmentAssumptions("Connectivity"),
        "AI": SegmentAssumptions("AI"),
    })


# --- model steps (to implement) ---------------------------------------------

def forecast_segment_revenue(assumptions: ModelAssumptions):  # -> pd.DataFrame
    """Project revenue by segment across the forecast horizon."""
    raise NotImplementedError("Revenue forecast not implemented yet.")


def unlevered_fcf(assumptions: ModelAssumptions):  # -> pd.DataFrame
    """Build unlevered FCF by year from forecast revenue + margin assumptions."""
    raise NotImplementedError("FCF build not implemented yet.")


def enterprise_value(assumptions: ModelAssumptions) -> float:
    """Discount FCF + terminal value to an enterprise value."""
    raise NotImplementedError("EV calc not implemented yet.")


def equity_value_per_share(assumptions: ModelAssumptions) -> float:
    """Bridge EV -> equity value (net debt, preferred) -> per-share."""
    raise NotImplementedError("Equity bridge not implemented yet.")


def sensitivity_grid(assumptions: ModelAssumptions):  # -> pd.DataFrame
    """Per-share value across a terminal-growth x WACC grid."""
    raise NotImplementedError("Sensitivity grid not implemented yet.")
