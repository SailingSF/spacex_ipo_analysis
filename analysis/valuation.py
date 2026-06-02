"""Multi-method valuation — the inputs to the "football field".

The DCF (``analysis/dcf.py``) is one lens. This module adds the lenses that *contest*
it, so the report can show the final number as a **convergence of independent methods**
rather than a single discounted-cash-flow bet — and, more honestly, so the *disagreement*
between methods (which is almost entirely *how you value AI*) is visible.

Three bars + one reference line, all expressed as **group equity value ($B)** (a secondary
\\$/share axis divides by the pro-forma share count):

* **DCF (floored + diluted)** — our cash-flow view. Bar = the scenario range
  (bear SOTP floor → bull), point = the probability-weighted blend. Engine: ``dcf.py``.
* **SOTP on comps** — value each segment on **peer multiples, not our cash flows**
  (Connectivity/Space/AI × EV-revenue bands from ``csv/comps.csv``). A genuinely
  independent, market-multiple engine.
* **Real-option (AI)** — prices exactly what the DCF floors at \\$0: a Bayesian
  ``P × V`` on the AI build (does Grok/the fleet ever clear its frontier?), added on top
  of the DCF value of Starlink + Space. The intellectually load-bearing bar; shown *wide*.
* **Private mark** — not a bar; a dated reference line (``csv/market_marks.csv``), the
  ~\\$350B Dec-2024 tender as the conservative anchor.

External inputs (comps, marks) are **not S-1 facts** — they live in flagged CSVs
(``csv/comps.csv``, ``csv/market_marks.csv``), are date-stamped, and are drawn visually
distinct (hatched/outlined) in the field. See ``csv/README.md``.

Conventions mirror ``dcf.py``: dollars in \\$M internally; ``*_b`` helpers report \\$B.
Nothing runs on import.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from analysis import dcf
from analysis.connectivity_economics import ConnectivityModel
from analysis.space_economics import SpaceModel
from analysis.ai_economics import AIModel

_CSV_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "csv"))
SEGMENTS = ["Connectivity", "Space", "AI"]


# =============================================================================
# Shared bridge inputs (from the S-1, via dcf.py)
# =============================================================================
def net_debt_m() -> float:
    """Net debt ($M), Mar-31-2026 — same source the DCF uses."""
    return dcf.net_debt_from_csv()


def shares_m() -> float:
    """Pro-forma diluted shares (M), post conversion / pre-IPO primary."""
    return dcf.PROFORMA_SHARES_M


def per_share(equity_m: float) -> float:
    """$M equity -> $/share on the pro-forma count."""
    return equity_m / shares_m()


# =============================================================================
# S-1 segment metrics the multiples multiply (FY2025 actuals, from the models)
# =============================================================================
def segment_metrics() -> pd.DataFrame:
    """FY2025 revenue & adjusted EBITDA ($M) by segment, pulled live from the models.

    Space revenue is *customer* revenue (internal Starlink launches are unbooked —
    capitalized into Connectivity — so this understates the launch franchise).
    """
    rows = {
        "Connectivity": ConnectivityModel().raw().loc["FY2025"],
        "Space":        SpaceModel().raw().loc["FY2025"],
        "AI":           AIModel().raw().loc["FY2025"],
    }
    out = pd.DataFrame({
        seg: {"revenue": float(r["revenue"]),
              "adj_ebitda": float(r["adj_ebitda_reported"])}
        for seg, r in rows.items()
    }).T.loc[SEGMENTS]
    return out


# =============================================================================
# External data loaders (flagged, non-S-1)
# =============================================================================
def load_comps() -> pd.DataFrame:
    """Peer-multiple bands by segment (EXTERNAL — see csv/README.md)."""
    return pd.read_csv(os.path.join(_CSV_DIR, "comps.csv"))


def load_marks() -> pd.DataFrame:
    """Private / secondary valuation marks (EXTERNAL — see csv/README.md)."""
    return pd.read_csv(os.path.join(_CSV_DIR, "market_marks.csv"))


def private_mark_anchor_b() -> float:
    """The conservative SpaceX private-mark anchor ($B) — the established Dec-2024 tender."""
    m = load_marks()
    spacex = m[(m.entity == "SpaceX") & (m.reliability == "established")]
    return float(spacex["mark_usd_b"].iloc[0])


# =============================================================================
# Method 1 — DCF range (from dcf.py)
# =============================================================================
def dcf_range(a: dcf.ValuationAssumptions | None = None) -> dict:
    """DCF equity range ($M): bear SOTP floor -> bull, with the prob-weighted point.

    Low = bear abandonment floor (≈ standalone Starlink); high = bull; point = the
    25/50/25 probability-weighted blend (SOTP basis). All from ``dcf.py``.
    """
    a = a or dcf.default_assumptions()
    act = dcf._actuals()
    res = {s: dcf.value_scenario(s, a, actuals=act) for s in ["Bear", "Base", "Bull"]}
    low = res["Bear"]["equity_sotp"]
    high = res["Bull"]["equity_sotp"]
    point = dcf.expected_value(a=a, basis="sotp")["equity"]
    return dict(low=low, high=high, point=point,
                bear=res["Bear"]["equity_sotp"], base=res["Base"]["equity_sotp"],
                bull=res["Bull"]["equity_sotp"])


# =============================================================================
# Method 2 — Sum-of-the-parts on peer multiples
# =============================================================================
def sotp_comps(comps: pd.DataFrame | None = None,
               metrics: pd.DataFrame | None = None) -> dict:
    """Value each segment on EV/revenue peer bands; sum to EV; bridge to equity.

    Multiples are EXTERNAL (``csv/comps.csv``); the revenue they multiply is the S-1
    FY2025 segment revenue. Returns a per-segment table plus the summed EV / equity
    range ($M). Deliberately uses the *revenue* multiple for all three segments (Space
    EBITDA is thin, AI EBITDA is negative), so the bars are comparable; Connectivity's
    EV/EBITDA band is reported as a cross-check.
    """
    comps = load_comps() if comps is None else comps
    metrics = segment_metrics() if metrics is None else metrics
    rev_mult = comps[comps.metric == "ev_revenue"].set_index("segment")

    rows = []
    for seg in SEGMENTS:
        rev = metrics.loc[seg, "revenue"]
        lo, hi = float(rev_mult.loc[seg, "mult_low"]), float(rev_mult.loc[seg, "mult_high"])
        rows.append(dict(segment=seg, basis="revenue", basis_usd_m=rev,
                         mult_low=lo, mult_high=hi, ev_low=rev * lo, ev_high=rev * hi))
    table = pd.DataFrame(rows).set_index("segment")

    ev_low, ev_high = table.ev_low.sum(), table.ev_high.sum()
    nd = net_debt_m()
    return dict(table=table, ev_low=ev_low, ev_high=ev_high,
                equity_low=max(0.0, ev_low - nd), equity_high=max(0.0, ev_high - nd),
                net_debt=nd)


# =============================================================================
# Method 3 — Real-option on AI (Bayesian P x V), added to the Starlink+Space DCF
# =============================================================================
@dataclass
class AIOptionAssumptions:
    """Bayesian real-option inputs for the AI build (deliberately wide & subjective).

    The DCF floors AI's terminal at \\$0 — it prices the abandonment case. This layer
    prices the *upside it throws away*: with probability ``p`` the build clears its
    frontier (integrated §6/§7) and AI becomes a real franchise worth ``payoff``; with
    probability ``1-p`` you abandon it (already the DCF's \\$0). So the option value is
    ``p × payoff`` — a fat-tailed bet, shown as a range, not a point.

    Defaults: ``p`` spans a skeptic-to-believer band; ``payoff`` spans the DCF's own
    Bull AI *terminal* (~\\$70B) up to the standalone xAI private mark (~\\$230B,
    market_marks.csv). These are assumptions, not S-1 facts.
    """
    p_low: float = 0.15
    p_high: float = 0.40
    payoff_low_m: float = 70_000.0    # ≈ DCF Bull AI terminal PV
    payoff_high_m: float = 230_000.0  # ≈ standalone xAI Series-E mark (Jan-2026)


def real_option_ai(a: dcf.ValuationAssumptions | None = None,
                   o: AIOptionAssumptions | None = None,
                   base_scenario: str = "Base") -> dict:
    """Total equity ($M) = DCF value of Starlink + Space  +  Bayesian AI option.

    The Starlink+Space base is the DCF's own segment EVs for ``base_scenario`` (AI
    excluded — it's the part the DCF values confidently); the AI option ``p × payoff``
    is layered on. Low/high combine the conservative and optimistic ends. This isolates
    the one bar whose disagreement with the DCF is the whole point: *what is the AI
    option worth?*
    """
    a = a or dcf.default_assumptions()
    o = o or AIOptionAssumptions()
    r = dcf.value_scenario(base_scenario, a)
    starlink_space_ev = r["ev"]["Connectivity"] + r["ev"]["Space"]
    base_equity = starlink_space_ev - r["net_debt"]

    opt_low = o.p_low * o.payoff_low_m
    opt_high = o.p_high * o.payoff_high_m
    return dict(base_equity=base_equity, ai_option_low=opt_low, ai_option_high=opt_high,
                low=base_equity + opt_low, high=base_equity + opt_high,
                point=base_equity + 0.5 * (opt_low + opt_high))


# =============================================================================
# Method 4 — Replacement / asset value  (DEFERRED — not built this pass)
# =============================================================================
def replacement_value() -> dict:
    """Cost-to-rebuild floor (constellation + launch infra + spectrum).

    Deferred per the football-field plan (§6.5 / §2.4): include only if per-satellite,
    launch-cost, and spectrum inputs can be sourced defensibly. Left as a stub so the
    field assembles without it; add as a thin floor marker in a later pass.
    """
    raise NotImplementedError("replacement_value: deferred — see valuation_football_field_plan.md")


# =============================================================================
# Assemble the football field
# =============================================================================
def football_field(a: dcf.ValuationAssumptions | None = None,
                   o: AIOptionAssumptions | None = None) -> pd.DataFrame:
    """Tidy (method, low, high, point, source_flag) frame in **equity $B**.

    ``source_flag`` ∈ {``s1``, ``external``} drives the chart's provenance hatching.
    The private mark is returned as a row too (low==high==point) for convenience, but
    is meant to be drawn as a reference *line*, not a bar.
    """
    a = a or dcf.default_assumptions()
    o = o or AIOptionAssumptions()
    d = dcf_range(a)
    s = sotp_comps()
    ro = real_option_ai(a, o)
    pm = private_mark_anchor_b()

    rows = [
        dict(method="DCF (floored + diluted)", low=d["low"] / 1000, high=d["high"] / 1000,
             point=d["point"] / 1000, source_flag="s1"),
        dict(method="SOTP on comps", low=s["equity_low"] / 1000, high=s["equity_high"] / 1000,
             point=0.5 * (s["equity_low"] + s["equity_high"]) / 1000, source_flag="external"),
        dict(method="Real-option (AI)", low=ro["low"] / 1000, high=ro["high"] / 1000,
             point=ro["point"] / 1000, source_flag="external"),
        dict(method="Private mark (Dec-2024)", low=pm, high=pm, point=pm, source_flag="external"),
    ]
    return pd.DataFrame(rows)


if __name__ == "__main__":  # quick smoke test
    pd.set_option("display.width", 120)
    print("Segment metrics (FY2025, $M):")
    print(segment_metrics().round(0).to_string(), "\n")
    s = sotp_comps()
    print("SOTP on comps (EV by segment):")
    disp = s["table"][["basis_usd_m", "mult_low", "mult_high", "ev_low", "ev_high"]].copy()
    for c in ["basis_usd_m", "ev_low", "ev_high"]:
        disp[c] = disp[c] / 1000  # -> $B
    print(disp.round(1).to_string())
    print(f"  -> EV {s['ev_low']/1000:.0f}-{s['ev_high']/1000:.0f}B | equity "
          f"{s['equity_low']/1000:.0f}-{s['equity_high']/1000:.0f}B\n")
    print("Football field (equity $B):")
    ff = football_field()
    ff["$/sh low"] = ff["low"] * 1000 / shares_m()
    ff["$/sh high"] = ff["high"] * 1000 / shares_m()
    print(ff.round(2).to_string(index=False))
