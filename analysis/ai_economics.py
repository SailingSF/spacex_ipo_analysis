"""AI segment — fundamental S-1 inputs for the analysis notebook.

Sibling of `space_economics.py` and `connectivity_economics.py`: a thin DATA layer
that loads the validated S-1 CSVs (via analysis.data) and assembles one tidy
per-period table of AI-segment fundamentals. It deliberately does NOT compute the
economics — those formulas live, in the open, in `ai.ipynb`, so a reader can see
exactly how every number is derived.

What the "AI" segment actually is (from the S-1):
  The AI segment is the merged X / xAI business folded into SpaceX. It earns money two
  ways and reports them as one disaggregation pair (Note 3 Revenue):
    * Advertising            — the X (formerly Twitter) social platform's ad business.
      This is a LEGACY, declining line ($2,323M FY2023 -> $1,844M FY2025).
    * AI Solutions & Infrastructure — Grok subscriptions/API, plus leasing data-center
      compute capacity to third parties (e.g. Anthropic). This is the GROWTH line
      ($638M FY2023 -> $1,357M FY2025) and the reason for the build-out.

Accounting / cost notes that drive the analysis:
  * The segment is in a heavy investment phase. R&D exploded $186M -> $1,176M -> $5,064M
    (FY2023->25) as xAI scaled Grok training. Capex went $463M -> $5,633M -> $12,727M:
    roughly 4x the segment's own revenue, almost all of it servers + data centers.
  * The S-1 does NOT disaggregate AI operating cost into power / headcount / hosting.
    What it DOES give, segment-level, is the three P&L buckets (COGS, R&D, SG&A) plus
    three cross-cutting "nature of cost" disclosures — Depreciation & amortization,
    Share-based compensation, and Capital expenditures. D&A is the accounting echo of
    the server build-out (the capital cost of compute hitting the P&L); SBC is a visible
    slice of employee cost. Electricity is NOT disclosed and must be ESTIMATED from the
    nameplate compute draw (see POWER_* constants) — done explicitly in the notebook.
  * FY2023 carried a $3,775M Impairment (legacy X goodwill/intangible writedown). It does
    not recur, but it is why FY2023 "income from operations" looks catastrophic relative
    to its then-positive Adjusted EBITDA.
  * Operating KPI: Nameplate compute draw (GW) — the contracted/installed power envelope
    of the AI data-center fleet. 0 -> 0.3 -> 0.8 GW (FY23->25), 1.0 GW at Q1-2026.

Usage
-----
>>> from analysis.ai_economics import AIModel, PERIODS
>>> R = AIModel().raw()      # per-period AI fundamentals (index = period)
"""
from __future__ import annotations

import pandas as pd

from analysis import data

PERIODS = ["FY2023", "FY2024", "FY2025", "Q1-2026"]

# --- Electricity estimate inputs (NOT disclosed; explicit assumptions, used in notebook) ---
#   The S-1 gives only "nameplate compute draw" in GW. To size the power bill we assume an
#   average utilization of the nameplate envelope and an all-in industrial $/MWh. Both are
#   carried as bands so the notebook can stress-test the (small-but-real) electricity line.
POWER_UTILIZATION = 0.65            # avg fraction of nameplate GW actually drawn over a year
POWER_UTILIZATION_BAND = (0.50, 0.80)
POWER_PRICE_PER_MWH = 65.0          # all-in industrial power ($/MWh), base case
POWER_PRICE_BAND = (45.0, 90.0)
HOURS_PER_YEAR = 8_760

# PP&E components (consolidated, Note 5) that are predominantly the AI build-out. Used to
# show WHERE the capex physically landed; PP&E is reported company-wide, not by segment, but
# these lines are overwhelmingly AI (servers/networking + data-center infrastructure).
AI_PPE_COMPONENTS = ["Servers and networking equipment", "Data center infrastructure"]

# ---------------------------------------------------------------------------
# GPU fleet & depreciation deep-dive — REFERENCE DATA + ASSUMPTIONS
# ---------------------------------------------------------------------------
# The S-1 describes the AI fleet only two ways: a "nameplate compute draw" (GW)
# KPI and a dollar PP&E balance ("Servers and networking equipment"). To reason
# about the *chips* underneath the depreciation we triangulate from public NVIDIA
# platform specs. These are REFERENCE estimates (vendor TDPs, reported system
# prices, typical data-center overhead) — NOT S-1 figures. Every value is an
# assumption and is carried as a band so the notebook can stress-test it.
#
#   all_in_kw  = per-GPU power at the *meter*: GPU TDP grossed up for the server
#                (CPU / NVSwitch / NIC) and then for facility overhead (PUE~1.25).
#   system_usd_k = fully-built cost per GPU in $000s, INCLUDING that GPU's share of
#                networking/storage/integration (i.e. what lands in the "Servers &
#                networking" PP&E line) — not the bare-die ASP.
GPU_SPECS = {
    #  gen        TDP(W)        all-in kW/GPU      system $k/GPU     first shipped
    "H100":  dict(tdp_w=700,    all_in_kw=1.60,    system_usd_k=32,  year=2023),
    "H200":  dict(tdp_w=700,    all_in_kw=1.60,    system_usd_k=34,  year=2024),
    "B200":  dict(tdp_w=1000,   all_in_kw=1.90,    system_usd_k=38,  year=2025),
    "GB200": dict(tdp_w=1200,   all_in_kw=2.00,    system_usd_k=42,  year=2025),
}
PUE_ASSUMED = 1.25                    # data-center power-usage effectiveness (already folded into all_in_kw)

# Blended fleet assumptions (a mix of 2024 Hopper + 2025-26 Blackwell). Used for headline
# point estimates; the per-spec min/max above set the triangulation band.
FLEET_ALL_IN_KW = 1.75                # blended per-GPU all-in power (kW)
FLEET_SYSTEM_USD_K = 36               # blended fully-built cost per GPU ($000s)

# Depreciation. The S-1 does NOT disclose a server useful life for the segment, so we
# (a) infer it empirically (D&A / gross AI PP&E) in the notebook, and (b) carry a band:
# hyperscaler practice is 5-6 yr straight-line; AI-obsolescence skeptics argue 2-3 yr of
# real economic life given NVIDIA's now-annual cadence.
USEFUL_LIFE_ACCOUNTING = 5.0          # yr, base-case book life (straight-line)
USEFUL_LIFE_BAND = (3.0, 6.0)         # (obsolescence-bear, hyperscaler-bull)
SALVAGE_FRACTION = 0.10               # residual value assumed at end of book life

# "Does a GPU earn its keep?" inputs.
WACC_ASSUMED = 0.11                   # cost of capital tying up the chip (placeholder for dcf.py)
GPU_RENTAL_USD_HR = 2.2               # base-case achievable blended $/GPU-hr (2025-26)
GPU_RENTAL_USD_HR_BAND = (1.5, 4.0)   # market H100-class rental: ~$4 (2023) -> ~$2 and below (2025)


class AIModel:
    def __init__(self):
        self._d = data.load_all()
        self._raw: pd.DataFrame | None = None

    def raw(self, periods: list[str] | None = None) -> pd.DataFrame:
        """Per-period AI fundamentals straight from the S-1 CSVs (index = period).

        Columns ($M unless noted):
          revenue, op_income, cogs, rnd, sga, restructuring, impairment,
          da, sbc, capex, adj_ebitda_reported,
          advertising, ai_solutions (revenue disaggregation buckets), ads_pct,
          compute_draw_gw (KPI, gigawatts).

        `periods` defaults to the standard set (PERIODS); pass an explicit list to pull
        others (e.g. the Q1-2025/Q1-2026 pair). The cached full-PERIODS frame is reused.
        """
        cache = periods is None
        if periods is None:
            periods = PERIODS
            if self._raw is not None:
                return self._raw
        d = self._d

        def seg(df, item, col="line_item", segment="AI"):
            return data.series(df, item, item_col=col, segment=segment).reindex(periods)

        pl, sup = d["segment_pl"], d["segment_supplemental"]
        kpi, disagg = d["segment_kpi"], d["revenue_disaggregation"]

        def rev_type(category):
            sub = disagg[(disagg.breakdown == "by_type_segment") &
                         (disagg.segment == "AI") & (disagg.category == category)]
            return sub.set_index("period")["value"].reindex(periods)

        def kpi_metric(metric):
            sub = kpi[(kpi.segment == "AI") & (kpi.metric == metric)]
            return sub.set_index("period")["value"].reindex(periods)

        ads = rev_type("Advertising")
        sol = rev_type("AI Solutions & Infrastructure")

        R = pd.DataFrame({
            "revenue": seg(pl, "Revenue"),
            "op_income": seg(pl, "Income (loss) from operations"),
            "cogs": seg(pl, "Cost of revenue"),
            "rnd": seg(pl, "Research and development"),
            "sga": seg(pl, "Selling general and administrative"),
            "restructuring": seg(pl, "Restructuring charges"),
            "impairment": seg(pl, "Impairment"),
            "da": seg(sup, "Depreciation and amortization", "metric"),
            "sbc": seg(sup, "Share-based compensation", "metric"),
            "capex": seg(sup, "Capital expenditures", "metric"),
            "adj_ebitda_reported": seg(d["segment_adjusted_ebitda"], "Segment Adjusted EBITDA"),
            "advertising": ads,
            "ai_solutions": sol,
            "ads_pct": ads / (ads + sol),
            "compute_draw_gw": kpi_metric("Nameplate compute draw"),
        })
        R.index.name = "period"
        if cache:
            self._raw = R
        return R

    def ppe_ai(self) -> pd.DataFrame:
        """Consolidated PP&E components that are predominantly the AI build-out (by date)."""
        ppe = self._d["ppe_detail"]
        sub = ppe[ppe.component.isin(AI_PPE_COMPONENTS)]
        return sub.pivot_table(index="component", columns="date", values="value", aggfunc="first")


if __name__ == "__main__":
    pd.set_option("display.width", 170, "display.max_columns", 30)
    R = AIModel().raw()
    print("AI fundamentals:\n", R.T)
    print("\nAI-relevant PP&E (consolidated):\n", AIModel().ppe_ai())
    print("\nRevenue mix flip — Advertising share of segment revenue:\n", R.ads_pct)
