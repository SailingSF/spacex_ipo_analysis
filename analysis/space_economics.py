"""Space (launch) segment — fundamental S-1 inputs for the analysis notebook.

Sibling of `connectivity_economics.py`: a thin DATA layer that loads the validated
S-1 CSVs (via analysis.data) and assembles one tidy per-period table of Space-segment
fundamentals. Historical fundamentals load here; the **FY2026–FY2030 forward path** (revenue,
R&D commercialization, FCF) is canonical in :func:`project_space_forward` — mirrored
in `space.ipynb` §6–§7 and consumed by `analysis/dcf.py`.

Accounting notes that drive the analysis (from the full S-1 MD&A, pp. 98-99, 75-76, 80):
  * Space revenue reflects ONLY customer launches and customer activities. Launches
    dedicated to Starlink are capitalized into the Connectivity segment (and, in future,
    AI) and earn NO inter-segment revenue in Space. So the Space P&L understates the
    economic value of SpaceX's launch monopoly — most of the cadence is flown for free,
    internally. (MD&A p.98; see also connectivity_economics.py.)
  * Space revenue splits into two recognition buckets:
      - Launch Services  — point-in-time, recognized at launch/deployment (Falcon 9 /
        Heavy / Dragon missions for commercial & government customers).
      - Launch & Development — over-time (cost-to-cost), long-term government contracts
        (development programs, crew/cargo). The S-1 expects this to grow as a share.
  * Starship is in the DEVELOPMENT stage: "A majority of Starship costs are currently
    expensed to Research and development as incurred. Raptor engines are expensed when
    used in test flights." The S-1 states the 2024->2025 Space R&D jump ($1,835M ->
    $3,004M) was driven by accelerating the Starship timeline. THE KEY ACCOUNTING HINGE:
    "At commercialization, Starship costs generally will be capitalized and then
    depreciated in cost of revenue of the segment associated with the payload delivered."
    So today's Space operating loss is essentially a Starship development invoice, and at
    commercialization the R&D drag converts into capitalized assets (MD&A p.99).

Usage
-----
>>> from analysis.space_economics import SpaceModel, PERIODS
>>> R = SpaceModel().raw()      # per-period Space fundamentals (index = period)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis import data
from analysis.connectivity_economics import INTERNAL_LAUNCH_COST_M  # one number, two valuations

PERIODS = ["FY2023", "FY2024", "FY2025", "Q1-2026"]

# --- Disclosed launch-vehicle payload capacity to LEO (metric tons), S-1 business section ---
#   Falcon 9 ~23t; Falcon Heavy ~64t; Starship V3 designed for 100t fully reusable
#   (future generations up to ~200t). Used to translate cadence -> mass and to size Starship.
PAYLOAD_T_LEO = {"Falcon 9": 23, "Falcon Heavy": 64, "Starship V3": 100, "Starship V4": 200}

# --- NASA-cited launch cost per kilogram to orbit (the S-1's own cost-curve, $/kg) ---
#   Historical average $18,500; Falcon 9 (2010) ~$2,700 (-85%); Falcon Heavy (2018)
#   ~$1,400 (-92%); Starship target: ">=99% reduction vs historical" -> ~$185 or less.
COST_PER_KG = {"Historical avg": 18_500, "Falcon 9": 2_700, "Falcon Heavy": 1_400,
               "Starship (target)": 185}

# Share of Space R&D attributable to Starship development (ASSUMPTION, not disclosed).
#   Floor is anchored: the S-1 attributes the entire $1,169M FY2024->FY2025 R&D increase
#   to accelerating Starship; "a majority of Starship costs are expensed to R&D" and Falcon
#   is a mature program, so the realistic share of the $3,004M FY2025 line is well above that.
STARSHIP_RND_SHARE = 0.75               # base case
STARSHIP_RND_SHARE_BAND = (0.55, 0.90)  # sensitivity band carried in the notebook

# --- Forward scenario engine (FY2026–FY2030; Bear / Base / Bull) -----------------
FORECAST_YEARS = [2026, 2027, 2028, 2029, 2030]
SS_YEAR = {"Bear": 2029, "Base": 2028, "Bull": 2027}   # first year Starship flies paying payloads
SS_RAMP = np.array([3, 6, 11, 18, 28])                 # external missions in yrs 0,1,2,... post-commercial
RND_MAINT_M = 1_200                                    # Falcon-sustaining + residual R&D once Starship capitalizes
DA_GROWTH = 0.12                                       # legacy fleet D&A growth until Starship book builds
CAP_SS_DA_FRAC = 0.45                                  # annual D&A on capitalized Starship dev. (y >= SS+1)

SPACE_SCENARIOS: dict[str, dict] = {
    "Bear": dict(commercial_year=2029, ramp_scale=0.5, ss_price=70,
                cust_g=0.01, ld_g=0.05, cxg=0.08),
    "Base": dict(commercial_year=2028, ramp_scale=1.0, ss_price=90,
                cust_g=0.03, ld_g=0.08, cxg=0.11),
    "Bull": dict(commercial_year=2027, ramp_scale=1.0, ss_price=110,
                cust_g=0.05, ld_g=0.10, cxg=0.13),
}


def project_space_forward(scenario: str, R: pd.DataFrame | None = None) -> pd.DataFrame:
    """FY2026–FY2030 Space segment path: franchise revenue + modest external Starship + R&D reversal → FCF.

    FCF = operating income + D&A + SBC − capex (same unlevered definition as Connectivity / ``dcf.py``).
    Starship commercialization glides R&D from the Q1-2026 run-rate peak to ``RND_MAINT_M``; capitalized
    Starship development adds to D&A from the year after commercialization. External Starship revenue
    follows ``SS_RAMP`` × scenario price — deliberately modest vs internal flywheel value in Connectivity.

    Returns a DataFrame indexed by calendar year with columns used by the notebook and DCF.
    """
    if scenario not in SPACE_SCENARIOS:
        raise KeyError(f"Unknown scenario {scenario!r}; expected one of {list(SPACE_SCENARIOS)}")
    if R is None:
        R = SpaceModel().raw()
    p = SPACE_SCENARIOS[scenario]
    cy = p["commercial_year"]

    cust_rev0 = float(R.launch_services["FY2025"])
    ld_rev0 = float(R.launch_dev["FY2025"])
    cogs_ratio = float(R.cogs["FY2025"] / R.revenue["FY2025"])
    sga0 = float(R.sga["FY2025"])
    rnd_peak = float(R.rnd["Q1-2026"] * 4)
    capex0 = float(R.capex["FY2025"])
    da0 = float(R.da["FY2025"])
    sbc_pct = float(R.sbc["FY2025"] / R.revenue["FY2025"])

    rows = []
    for i, yr in enumerate(FORECAST_YEARS):
        cust = cust_rev0 * (1 + p["cust_g"]) ** (i + 1)
        ld = ld_rev0 * (1 + p["ld_g"]) ** (i + 1)
        si = yr - cy
        ss_launches = float(SS_RAMP[si] * p["ramp_scale"]) if 0 <= si < len(SS_RAMP) else 0.0
        ss_rev = ss_launches * p["ss_price"]
        rev = cust + ld + ss_rev
        if yr < cy:
            rnd = rnd_peak
        else:
            rnd = rnd_peak + (RND_MAINT_M - rnd_peak) * (min(si, 2) / 2)
        op = rev - cogs_ratio * rev - sga0 - rnd
        da = da0 * (1 + DA_GROWTH) ** (i + 1)
        if yr >= cy + 1:
            da += rnd_peak * STARSHIP_RND_SHARE * CAP_SS_DA_FRAC
        capex = capex0 * (1 + p["cxg"]) ** (i + 1)
        sbc = rev * sbc_pct
        fcf = op + da + sbc - capex
        rows.append(dict(
            cust_rev=cust, ld_rev=ld, ss_launches=ss_launches, ss_rev=ss_rev,
            revenue=rev, rnd=rnd, op_income=op, op_margin=op / rev if rev else np.nan,
            da=da, sbc=sbc, capex=capex, fcf=fcf, fcf_margin=fcf / rev if rev else np.nan,
        ))
    out = pd.DataFrame(rows, index=FORECAST_YEARS)
    out.index.name = "year"
    return out


class SpaceModel:
    def __init__(self):
        self._d = data.load_all()
        self._raw: pd.DataFrame | None = None

    def raw(self, periods: list[str] | None = None) -> pd.DataFrame:
        """Per-period Space fundamentals straight from the S-1 CSVs (index = period).

        Columns ($M unless noted):
          revenue, op_income, cogs, rnd, sga, impairment, da, sbc, capex,
          adj_ebitda_reported (comparison only),
          launch_services, launch_dev (revenue recognition buckets), ls_pct,
          customer_launches, starlink_launches, total_falcon (counts),
          kpi_launches (count, incl. Starship test flights), mass_to_orbit (metric tons).

        `periods` defaults to the standard set (PERIODS); pass an explicit list to pull
        others (e.g. the Q1-2025/Q1-2026 pair). The cached full-PERIODS frame is reused.
        """
        if periods is None:
            periods = PERIODS
            if self._raw is not None:
                return self._raw
        d = self._d

        def seg(df, item, col="line_item", segment="Space"):
            return data.series(df, item, item_col=col, segment=segment).reindex(periods)

        pl, sup = d["segment_pl"], d["segment_supplemental"]
        kpi, ld = d["segment_kpi"], d["launch_detail"]
        disagg = d["revenue_disaggregation"]

        def rev_type(category):
            sub = disagg[(disagg.breakdown == "by_type_segment") &
                         (disagg.segment == "Space") & (disagg.category == category)]
            return sub.set_index("period")["value"].reindex(periods)

        def launches(cat):
            sub = ld[ld.category == cat].set_index("period")["value"]
            return sub.reindex(periods)

        def kpi_metric(metric):
            sub = kpi[(kpi.segment == "Space") & (kpi.metric == metric)]
            return sub.set_index("period")["value"].reindex(periods)

        ls = rev_type("Launch Services")
        ld_rev = rev_type("Launch & Development")

        R = pd.DataFrame({
            "revenue": seg(pl, "Revenue"),
            "op_income": seg(pl, "Income (loss) from operations"),
            "cogs": seg(pl, "Cost of revenue"),
            "rnd": seg(pl, "Research and development"),
            "sga": seg(pl, "Selling general and administrative"),
            "impairment": seg(pl, "Impairment"),
            "da": seg(sup, "Depreciation and amortization", "metric"),
            "sbc": seg(sup, "Share-based compensation", "metric"),
            "capex": seg(sup, "Capital expenditures", "metric"),
            "adj_ebitda_reported": seg(d["segment_adjusted_ebitda"], "Segment Adjusted EBITDA"),
            "launch_services": ls,
            "launch_dev": ld_rev,
            "ls_pct": ls / (ls + ld_rev),
            "customer_launches": launches("Customer Falcon launches"),
            "starlink_launches": launches("Internal Starlink Falcon launches"),
            "total_falcon": launches("Falcon launches total"),
            "kpi_launches": kpi_metric("Launches"),
            "mass_to_orbit": kpi_metric("Mass to Orbit"),
        })
        R.index.name = "period"
        if periods is PERIODS:
            self._raw = R
        return R


if __name__ == "__main__":
    pd.set_option("display.width", 170, "display.max_columns", 30)
    R = SpaceModel().raw()
    print("Space fundamentals:\n", R.T)
    print(f"\nInternal launch cost carried from Connectivity: ${INTERNAL_LAUNCH_COST_M}M")
    core = R.revenue - R.cogs - R.sga - R.impairment
    print("\nCore op income (Revenue - COGS - SG&A - Impairment, i.e. pre-R&D):\n", core)
    print("\nReported op income (after R&D):\n", R.op_income)
