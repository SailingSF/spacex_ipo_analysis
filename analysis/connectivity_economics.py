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

import numpy as np
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

# =============================================================================
# §7.7 affordability-cost flywheel — the deterministic "ARPU down, subs up,
# margin computed" Connectivity path from connectivity.ipynb §7.4-§7.7. Canonical
# home so the DCF can cite it (it wires this in as the BULL connectivity path).
# These are external / assumption anchors (NOT S-1 line items), mirroring the
# notebook; the FY2025 anchors are pulled live from the S-1 CSVs in the function.
# =============================================================================
FLY_YEARS = [2026, 2027, 2028, 2029, 2030]
# Reachable-ceiling math (§7.4): raw unconnected envelope + affordability coupling.
UNCONNECTED_PEOPLE_B = 3.0     # S-1: ~3B unconnected people
PPL_PER_HH           = 3.5     # -> ~857M unconnected households
SERVED_HH_M          = 1000    # fixed-broadband HH ex-China/Russia (ITU)
REF_ARPU             = 65.0    # ARPU the central ~307M ceiling was calibrated near
REF_INCOME_SHARE     = 0.30    # central income-capable share of unconnected
CEILING_ELASTIC      = 0.40    # sublinear: lower ARPU expands reach, not 1:1
CEILING_INCOME_CAP   = 0.52    # cap on income-capable share
WIN_SHARE            = 0.05    # central Starlink-win share of served HH
# Demand path (§7.7).
ARPU_2030_FLY        = 38.0    # accelerated ARPU glide endpoint ($/mo)
SUB_G_YOY_FLY        = [0.85, 0.65, 0.48, 0.32, 0.20]  # FY26-30 YoY subscriber growth
PEN_OF_CEILING_FLY   = 0.58    # approach 58% of the dynamic ceiling by FY2030
NONC_G_FLY           = 0.22    # non-consumer (aviation/maritime/MNO) growth
# Infrastructure cost decline (§7.6, Starship + v3).
LAUNCH_COST_30       = 8.0     # $M internal/launch by FY2030 (Starship target)
SATS_PER_LAUNCH_25   = 23      # v2-mini per Falcon 9 today
SATS_LAUNCH_30       = 60      # v3 batch on Starship by FY2030
CAP_G_FLY            = 0.30    # capacity per satellite /yr (v3 + beamforming)
SAT_MFG_LEARN        = 0.03    # satellite-manufacturing efficiency /yr
CASH_OPEX_SCALE_FLY  = 0.995   # -0.5%/yr scale benefit on kit + network ops
FLEET_2025           = 8000    # operational satellites end-2025 (external)
SAT_LIFE_YR          = 5.0     # satellite deorbit/license life


def project_connectivity_flywheel(R: pd.DataFrame | None = None,
                                  d: dict | None = None) -> pd.DataFrame:
    """FY2026-FY2030 Connectivity FCF on the §7.7 affordability-cost flywheel path.

    The deterministic "ARPU down, subscribers up, operating margin *computed* from
    Starship launch economics" alternative built in ``connectivity.ipynb`` §7.7. The
    DCF wires this in as the **bull** Connectivity path (the S-1's stated strategy:
    ARPU falls on purpose to reach more households, and cheaper launch / more
    bandwidth-per-satellite is the margin offset). FY2025 anchors come live from the
    S-1 CSVs; everything else is the named assumption set above.

    FCF = operating income + D&A + SBC - capex (unlevered, same as ``dcf.py``).
    Returns a DataFrame indexed by year (FY2026-FY2030) with columns
    ``rev, op, da, sbc, capex, fcf, subs, arpu``.
    """
    if R is None:
        R = ConnectivityModel().raw()
    if d is None:
        d = data.load_all()

    kc = d["segment_kpi"]; kc = kc[kc.segment == "Connectivity"]
    subs_kpi = kc[kc.metric == "Starlink Subscribers"].set_index("period")["value"]
    arpu_kpi = kc[kc.metric == "Starlink ARPU"].set_index("period")["value"]
    satg = d["ppe_detail"]
    satg = satg[satg.component == "Satellites"].set_index("date")["value"]

    subs25, subs24 = float(subs_kpi["FY2025"]), float(subs_kpi["FY2024"])
    arpu25 = float(arpu_kpi["FY2025"])
    rev25 = float(R.revenue["FY2025"])
    cons25 = (subs24 + subs25) / 2 * arpu25 * 12          # FY2025 consumer revenue
    noncons25 = rev25 - cons25                            # residual = non-consumer
    launches25 = float(R.starlink_launches["FY2025"])
    sat_add25 = float(satg["2025-12-31"] - satg["2024-12-31"])   # gross sats added FY2025
    capex_per_launch = sat_add25 / launches25            # all-in $M per launch (hardware + launch)
    mfg_share25 = 1 - (INTERNAL_LAUNCH_COST_M * launches25 / sat_add25)
    subs_per_sat25 = subs25 * 1e6 / FLEET_2025
    cash_opex_rev25 = ((float(R.cogs["FY2025"]) - float(R.da["FY2025"]))
                       + float(R.rnd["FY2025"]) + float(R.sga["FY2025"])) / rev25
    sbc_pct = float(R.sbc["FY2025"]) / rev25
    arpu_26e = arpu25 * float(arpu_kpi["Q1-2026"]) / float(arpu_kpi["Q1-2025"])

    yrs = [2025] + FLY_YEARS                              # anchor + forecast
    n = len(yrs)
    arpu_fly = np.zeros(n); arpu_fly[0] = arpu25; arpu_fly[1] = arpu_26e
    for i in range(2, n):                                 # front-loaded post-2026 decline
        t = (i - 1) / (n - 2)
        arpu_fly[i] = arpu_26e + (ARPU_2030_FLY - arpu_26e) * t ** 1.2

    def ceiling(arpu_mo):
        unconn = UNCONNECTED_PEOPLE_B * 1000 / PPL_PER_HH
        inc = min(CEILING_INCOME_CAP, REF_INCOME_SHARE * (REF_ARPU / arpu_mo) ** CEILING_ELASTIC)
        return inc * unconn + WIN_SHARE * SERVED_HH_M

    def launch_econ(i):
        t = i / (n - 1)
        lc = INTERNAL_LAUNCH_COST_M + (LAUNCH_COST_30 - INTERNAL_LAUNCH_COST_M) * t
        spl = SATS_PER_LAUNCH_25 + (SATS_LAUNCH_30 - SATS_PER_LAUNCH_25) * t
        mfg = capex_per_launch * mfg_share25 * (1 - SAT_MFG_LEARN) ** i
        return lc + mfg, spl

    subs_prev, nc_prev = subs25, noncons25
    fleet = [FLEET_2025]; launches = [launches25]; rows = []
    for i, yr in enumerate(yrs):
        ceil = ceiling(arpu_fly[i])
        if i == 0:
            subs_eop, cons, nc = subs_prev, cons25, nc_prev
            sat_dep, sat_capex = float(R.da["FY2025"]), float(R.capex["FY2025"])
        else:
            target = ceil * PEN_OF_CEILING_FLY
            subs_eop = min(subs_prev * (1 + SUB_G_YOY_FLY[i - 1]), target)
            cons = (subs_prev + subs_eop) / 2 * arpu_fly[i] * 12
            nc = nc_prev * (1 + NONC_G_FLY)
            sps = subs_per_sat25 * (1 + CAP_G_FLY) ** i
            need = subs_eop * 1e6 / sps
            grow = max(0.0, need - fleet[-1]); repl = fleet[-1] / SAT_LIFE_YR
            cpl, spl = launch_econ(i)
            launches.append((grow + repl) / spl); fleet.append(need)
            avg_fleet = (fleet[-2] + fleet[-1]) / 2
            sat_dep = avg_fleet * (cpl / spl) / SAT_LIFE_YR
            sat_capex = launches[-1] * cpl
        rev = cons + nc
        cash_ox = cash_opex_rev25 * (CASH_OPEX_SCALE_FLY ** i)
        op = rev * (1 - cash_ox - sat_dep / rev)
        sbc = rev * sbc_pct
        rows.append(dict(year=yr, rev=rev, op=op, da=sat_dep, sbc=sbc, capex=sat_capex,
                         fcf=op + sat_dep + sbc - sat_capex, subs=subs_eop, arpu=arpu_fly[i]))
        subs_prev, nc_prev = subs_eop, nc

    return pd.DataFrame(rows).set_index("year").loc[FLY_YEARS]


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
