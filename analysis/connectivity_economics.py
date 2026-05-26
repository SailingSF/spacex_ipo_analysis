"""Connectivity (Starlink) — fundamental S-1 inputs for the analysis notebook.

This module is a thin DATA layer: it loads the validated S-1 CSVs (via analysis.data)
and assembles one tidy table of per-period fundamentals for the Connectivity segment.
It deliberately does NOT compute the economics — those formulas live, in the open, in
`connectivity.ipynb`, so a reader can see exactly how every number is derived.

Accounting note that drives the analysis (from the full S-1):
  SpaceX capitalizes Starlink launch costs INTO the Connectivity segment and depreciates
  them; they are not hidden in the Space segment.
    - MD&A p.81: "For launches dedicated to deploying our Starlink satellites, we capitalize
      the associated costs within our Connectivity segment and depreciate them over time,
      and we do not recognize revenue for those launches in our Space segment."
    - PP&E note F-14: satellites include "capitalized launch costs incurred by the Space
      segment ... include an allocation of the flight vehicle hardware costs."
  So reported Connectivity operating income already bears launch (via D&A, at internal cost).

EBITDA policy: the notebook computes GAAP EBITDA = operating income + D&A and builds FCF from
it. SpaceX's *Adjusted* EBITDA (which also adds back SBC, restructuring, and impairment) is
shown only for comparison/reconciliation, never used in a calculation. `adj_ebitda_reported`
below is provided solely so the notebook can reconcile to it.

Usage
-----
>>> from analysis.connectivity_economics import ConnectivityModel, PERIODS
>>> R = ConnectivityModel().raw()      # per-period fundamentals (index = period)
"""
from __future__ import annotations

import pandas as pd

from analysis import data

PERIODS = ["FY2023", "FY2024", "FY2025", "Q1-2026"]

# Only non-S-1 input: marginal internal cost of one reused Falcon 9 ($M).
# Web-corroborated (~$15-20M; NextBigFuture Feb-2026 ~25% of list; Musk ~$15M floor).
INTERNAL_LAUNCH_COST_M = 17.5

# Illustrative (NOT disclosed) split of the non-depreciation "cash COGS" bucket.
KIT_SHARE = 0.40

# Disclosed S-1 sensitivity: op-income impact of a +/-1yr change in satellite useful life.
SAT_LIFE_SENSITIVITY_M = {"FY2025": 480, "Q1-2026": 170}


class ConnectivityModel:
    def __init__(self):
        self._d = data.load_all()
        self._raw: pd.DataFrame | None = None

    def raw(self, periods: list[str] | None = None) -> pd.DataFrame:
        """Per-period Connectivity fundamentals straight from the S-1 CSVs (index = period).

        Columns are raw reported values ($M, except *launches and ls_pct):
          revenue, op_income, cogs, rnd, sga, da, sbc, restructuring, impairment, capex,
          adj_ebitda_reported (comparison only), space_revenue, ls_pct (Launch Services share
          of Space revenue), starlink_launches, customer_launches.

        `periods` defaults to the standard reporting set (PERIODS). Pass an explicit list
        (e.g. ["Q1-2025", "Q1-2026"]) to pull other periods — used by the notebook to build a
        year-over-year FY2026E projection in the open. The cached full-PERIODS frame is reused.
        """
        if periods is None:
            periods = PERIODS
            if self._raw is not None:
                return self._raw
        d = self._d

        def seg(df, item, segment, col="line_item"):
            return data.series(df, item, item_col=col, segment=segment).reindex(periods)

        pl, sup = d["segment_pl"], d["segment_supplemental"]
        ld, mix = d["launch_detail"], d["space_revenue_mix_pct"]

        def launches(cat):
            sub = ld[ld.category == cat].set_index("period")["value"]
            return sub.reindex(periods)

        ls = mix[mix.category == "Launch Services"].set_index("period")["value"].reindex(periods) / 100

        R = pd.DataFrame({
            "revenue": seg(pl, "Revenue", "Connectivity"),
            "op_income": seg(pl, "Income (loss) from operations", "Connectivity"),
            "cogs": seg(pl, "Cost of revenue", "Connectivity"),
            "rnd": seg(pl, "Research and development", "Connectivity"),
            "sga": seg(pl, "Selling general and administrative", "Connectivity"),
            "restructuring": seg(pl, "Restructuring charges", "Connectivity"),
            "impairment": seg(pl, "Impairment", "Connectivity"),
            "da": seg(sup, "Depreciation and amortization", "Connectivity", "metric"),
            "sbc": seg(sup, "Share-based compensation", "Connectivity", "metric"),
            "capex": seg(sup, "Capital expenditures", "Connectivity", "metric"),
            "adj_ebitda_reported": seg(d["segment_adjusted_ebitda"], "Segment Adjusted EBITDA", "Connectivity"),
            "space_revenue": seg(pl, "Revenue", "Space"),
            "ls_pct": ls,
            "starlink_launches": launches("Internal Starlink Falcon launches"),
            "customer_launches": launches("Customer Falcon launches"),
        })
        R.index.name = "period"
        if periods is PERIODS:
            self._raw = R
        return R


if __name__ == "__main__":
    pd.set_option("display.width", 160, "display.max_columns", 30)
    R = ConnectivityModel().raw()
    print("Fundamentals:\n", R.T)
    gaap_ebitda = R.op_income + R.da
    print("\nGAAP EBITDA (op income + D&A):\n", gaap_ebitda)
    print("\nFCF (GAAP EBITDA - capex):\n", gaap_ebitda - R.capex)
