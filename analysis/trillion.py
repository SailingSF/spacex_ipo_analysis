"""The "$1,000,000,000,000" bridge — reverse-engineering the IPO hype number.

The football field (``analysis/valuation.py``) tops out around **$224–243B** equity,
and even the $350B private mark sits *above* every method. Yet the IPO chatter throws
around **$1T+** (and a ~$1.25T SpaceX–xAI merger mark, a ~$1.75T "IPO-day" target —
``csv/market_marks.csv``). This module does not try to *justify* $1T; it does the more
useful thing — it **decomposes what you would have to believe** to print it, and then
names how silly (or not) each belief is.

The logic is a residual bridge in **EV space** (so net debt is bridged once):

    target equity ($1T)  ->  target EV = $1T + net debt
    minus  EV(Connectivity) + EV(Space)         [valued *fairly*, from dcf.py]
    =      EV(AI) the number *requires*           <- the whole story lives here

We value Starlink + Space at our own (already-generous) DCF scenarios, so the bridge is
honest about where the disagreement is: it is **entirely the AI segment**. We then ask
the required AI EV three independent ways — none of which is our DCF:

* **Frontier-lab comps.** What revenue multiple does the required AI EV imply, and how
  does that compare to what the market actually pays for OpenAI / Anthropic / xAI / GOOG?
  (External marks, quarantined in ``csv/ai_labs.csv``.) The question becomes: *is SpaceX's
  AI worth ~3–4× xAI's own private mark, i.e. an OpenAI-scale franchise?*
* **AGI Bayesian P × V.** The hype is a probability-weighted bet on transformative AI.
  Given a payoff ``V`` (a multi-$T AGI franchise), what probability ``P`` must you assign
  for ``P × V`` to clear the required AI EV? We draw the indifference curve and read off
  the (P, V) pairs the $1T crowd is implicitly underwriting.
* **Super-bull reverse-DCF.** How far past our Bull do the AI dials (nameplate GW,
  utilization, $/GPU-hr, chip life, R&D) have to move for the *cash-flow* AI EV to reach
  the required number? This mirrors ``dcf._ai`` exactly, just with the dials cranked.

A small **Space mega-bull** lever (launch-monopoly multiple) is included to show it barely
moves the needle — the $1T is an AI story, not a rockets story.

External inputs live in flagged, date-stamped CSVs and are drawn distinct in the notebook;
nothing here is an S-1 fact. Conventions mirror ``dcf.py`` / ``valuation.py``: dollars in
\\$M internally, ``*_b`` helpers report \\$B. Nothing runs on import.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from analysis import dcf
from analysis import valuation as val

_CSV_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "csv"))

# AI engine constants, reused verbatim from dcf.py so the super-bull path can't drift.
from analysis.dcf import (GPU_PER_GW, HRS, CAPEX_PER_GW, BOOK_LIFE, GROSS0, GW0,
                          YEARS, UTIL0, PRICE0)

TARGET_B = 1000.0   # the headline number we are reverse-engineering ($B equity)


# =============================================================================
# 1. The fair (non-AI) base — Starlink + Space from our own DCF
# =============================================================================
def nonai_ev(conn_scn: str = "Bull", space_scn: str = "Bull",
             a: dcf.ValuationAssumptions | None = None) -> dict:
    """EV ($M) of Connectivity + Space, each at a chosen DCF scenario.

    We deliberately let the caller pick **generous** non-AI scenarios (default Bull/Bull)
    so the residual AI number is the *smallest* AI value consistent with the target — i.e.
    we give the bull every non-AI benefit of the doubt, and the AI ask is still enormous.
    """
    a = a or dcf.default_assumptions()
    act = dcf._actuals()
    conn_ev = dcf.value_scenario(conn_scn, a, actuals=act)["ev"]["Connectivity"]
    space_ev = dcf.value_scenario(space_scn, a, actuals=act)["ev"]["Space"]
    return dict(conn_ev=conn_ev, space_ev=space_ev, nonai_ev=conn_ev + space_ev,
                net_debt=a.net_debt, conn_scn=conn_scn, space_scn=space_scn)


def required_ai_ev(target_equity_b: float = TARGET_B, conn_scn: str = "Bull",
                   space_scn: str = "Bull", space_bonus_b: float = 0.0,
                   a: dcf.ValuationAssumptions | None = None) -> dict:
    """AI EV ($M) the target equity *requires*, after fair Starlink + Space.

    ``space_bonus_b`` lets a Space mega-bull add extra EV (shrinking the AI ask) — see
    :func:`space_megabull_bonus_b`. Returns the full bridge in $M.
    """
    a = a or dcf.default_assumptions()
    base = nonai_ev(conn_scn, space_scn, a)
    target_ev = target_equity_b * 1000 + base["net_debt"]
    nonai = base["nonai_ev"] + space_bonus_b * 1000
    ai_req = target_ev - nonai
    return dict(target_equity=target_equity_b * 1000, target_ev=target_ev,
                conn_ev=base["conn_ev"], space_ev=base["space_ev"],
                space_bonus=space_bonus_b * 1000, nonai_ev=nonai,
                ai_required_ev=ai_req, net_debt=base["net_debt"],
                conn_scn=conn_scn, space_scn=space_scn)


# =============================================================================
# 2. Method A — frontier-lab comps (what others pay for AI)
# =============================================================================
def load_ai_labs() -> pd.DataFrame:
    """Frontier-AI-lab valuation marks (EXTERNAL — see csv/README.md)."""
    return pd.read_csv(os.path.join(_CSV_DIR, "ai_labs.csv"))


def implied_ai_multiple(ai_required_ev_m: float, ai_fwd_rev_m: float) -> float:
    """Required AI EV ÷ a forward AI revenue = the EV/revenue multiple $1T implies."""
    return ai_required_ev_m / ai_fwd_rev_m if ai_fwd_rev_m else float("nan")


def comp_implied_ai_ev(ai_fwd_rev_m: float, labs: pd.DataFrame | None = None) -> pd.DataFrame:
    """For each lab's EV/revenue mark, the AI EV ($M) it implies on SpaceX's fwd AI revenue.

    Answers "if SpaceX's AI traded like OpenAI / Anthropic / xAI / GOOG, what would the
    segment be worth?" — a market-multiple cross-check on the residual AI ask.
    """
    labs = load_ai_labs() if labs is None else labs
    out = labs.copy()
    out["implied_ai_ev_m"] = out["ev_rev_mult"] * ai_fwd_rev_m
    return out


# =============================================================================
# 3. Method B — AGI Bayesian P × V (the option the hype is really pricing)
# =============================================================================
def agi_required_p(ai_required_ev_m: float, payoff_m: float) -> float:
    """Probability P such that P × payoff = required AI EV (the break-even AGI odds)."""
    return ai_required_ev_m / payoff_m if payoff_m else float("nan")


def agi_pv_grid(ai_required_ev_m: float, payoffs_b, probs) -> pd.DataFrame:
    """P×V grid ($B): cell = P × payoff; the indifference contour is where it = required AI EV.

    Rows = AGI payoff ``V`` ($B, the value of the won franchise); cols = probability ``P``.
    Lets the notebook shade the (P, V) region that clears the required AI value.
    """
    grid = pd.DataFrame(index=[f"${v:,.0f}B" for v in payoffs_b],
                        columns=[f"{p:.0%}" for p in probs], dtype=float)
    for v in payoffs_b:
        for p in probs:
            grid.loc[f"${v:,.0f}B", f"{p:.0%}"] = p * v * 1000  # $M
    return grid


# =============================================================================
# 4. Method C — super-bull reverse-DCF on the AI dials
# =============================================================================
@dataclass
class AISuperBull:
    """AI dials cranked *past* the DCF Bull — the cash-flow path to a huge AI EV.

    Mirrors ``dcf.AM['Bull']`` keys so the engine below is identical to ``dcf._ai`` /
    ``dcf.ai_mature_fcf`` except the levers are pushed: more nameplate GW, higher
    utilization and price (AGI pricing power), longer chip life, lower relative R&D.
    Defaults sit at a deliberately aggressive "and-then-some" calibration.
    """
    gw: float = 20.0      # 2030 nameplate GW   (Bull = 7)
    util: float = 0.90    # utilization         (Bull = 0.85)
    price: float = 4.0    # blended $/GPU-hr    (Bull = 2.2) — AGI scarcity pricing
    chip_life: float = 6.0  # refresh life, yrs (Bull = 6.0)
    rm: float = 0.65      # R&D multiple        (Bull = 0.65)
    ag: float = 0.0       # legacy ad growth


def _ai_super_path(d: AISuperBull) -> pd.DataFrame:
    """FY2026–FY2030 AI FCF path for the super-bull dials (mirrors ``dcf._ai``)."""
    g = lambda a, b: np.linspace(a, b, 5)
    gw = g(GW0, d.gw); util = g(UTIL0, d.util); price = g(PRICE0, d.price)
    gw_prev = np.concatenate([[GW0], gw[:-1]]); gross = GROSS0; out = []
    for i in range(5):
        compute = gw[i] * GPU_PER_GW * price[i] * HRS * util[i] / 1e6
        ads = 1844 * (1 + d.ag) ** (i + 1)
        rev = compute + ads
        build = max(0, gw[i] - gw_prev[i]) * CAPEX_PER_GW
        refresh = gross / d.chip_life
        capex = build + refresh; gross += build
        da = gross / BOOK_LIFE
        rnd = 5064 * d.rm
        power = gw[i] * 65 * HRS * 1000 * util[i] / 1e6
        sga, sbc = 1827 * 1.05 ** (i + 1), 1063
        op = rev - rev * 0.25 - power - da - rnd - sga
        out.append(dict(gw=gw[i], price=price[i], util=util[i], rev=rev, op=op,
                        da=da, sbc=sbc, capex=capex, fcf=op + da + sbc - capex))
    return pd.DataFrame(out, index=YEARS)


def _ai_super_mature_fcf(d: AISuperBull) -> float:
    """Mature steady-state AI FCF ($M/yr) for super-bull dials (mirrors ``dcf.ai_mature_fcf``)."""
    gross = GROSS0 + (d.gw - GW0) * CAPEX_PER_GW
    compute = d.gw * GPU_PER_GW * d.price * HRS * d.util / 1e6
    ads = 1844 * (1 + d.ag) ** 5
    rev = compute + ads
    power = d.gw * 65 * HRS * 1000 * d.util / 1e6
    rnd = 5064 * d.rm
    sga = 1827 * 1.05 ** 5
    refresh = gross / d.chip_life
    return rev - rev * 0.25 - power - rnd - sga - refresh + 1063


def super_bull_ai_ev(d: AISuperBull | None = None,
                     a: dcf.ValuationAssumptions | None = None,
                     floor: bool = False) -> dict:
    """AI segment EV ($M) for the super-bull dials, via the exact DCF machinery.

    EV = Σ discounted explicit FCF (FY2026–30, the build drag) + discounted Gordon
    terminal on the mature-fleet FCF. Returns the path, EVs, FY2030 revenue (for the
    multiple cross-check) and the mature FCF.
    """
    d = d or AISuperBull()
    a = a or dcf.default_assumptions()
    path = _ai_super_path(d)
    df = dcf.discount_factors(a.wacc, len(YEARS), a.mid_year)
    explicit_pv = float(np.sum(path.fcf.values * df))
    mature = _ai_super_mature_fcf(d)
    gordon = mature * (1 + a.terminal_growth) / (a.wacc - a.terminal_growth)
    if floor:
        gordon = max(0.0, gordon)
    terminal_pv = float(gordon * df[-1])
    return dict(dials=d, path=path, explicit_pv=explicit_pv, terminal_pv=terminal_pv,
                ev=explicit_pv + terminal_pv, mature_fcf=mature,
                fwd_rev_2030=float(path.rev.iloc[-1]))


def required_mature_fcf(ai_required_ev_m: float,
                        a: dcf.ValuationAssumptions | None = None) -> float:
    """Mature AI FCF ($M/yr) whose *terminal alone* equals the required AI EV.

    Terminal-only inversion (ignores the explicit build drag, so it is a *floor* on the
    FCF needed): EV = FCF·(1+g)/(wacc−g)·df5  ->  FCF = EV / [(1+g)/(wacc−g)·df5].
    A quick gut-check on how many $B/yr of mature AI cash the headline demands.
    """
    a = a or dcf.default_assumptions()
    df5 = dcf.discount_factors(a.wacc, len(YEARS), a.mid_year)[-1]
    gordon_mult = (1 + a.terminal_growth) / (a.wacc - a.terminal_growth) * df5
    return ai_required_ev_m / gordon_mult


# =============================================================================
# 5. The minor lever — a Space mega-bull (launch monopoly multiple)
# =============================================================================
def space_megabull_bonus_b(mult_high: float = 20.0, mega_mult: float = 40.0,
                           a: dcf.ValuationAssumptions | None = None) -> dict:
    """Extra Space EV ($B) from re-rating Space to a launch-monopoly multiple.

    Uses the SOTP comp engine's Space revenue (S-1 FY2025 *customer* revenue) and asks
    what a Rocket-Lab-peak-style multiple adds *over* our DCF Bull Space EV. Deliberately
    framed as a cross-check: even a rich multiple on the understated customer line adds
    only tens of $B — small next to the AI ask.
    """
    a = a or dcf.default_assumptions()
    space_rev = val.segment_metrics().loc["Space", "revenue"]
    dcf_bull_space = dcf.value_scenario("Bull", a)["ev"]["Space"] / 1000  # $B
    mega_ev = space_rev * mega_mult / 1000   # $B
    return dict(space_rev_m=space_rev, dcf_bull_space_b=dcf_bull_space,
                mega_mult=mega_mult, mega_ev_b=mega_ev,
                bonus_b=max(0.0, mega_ev - dcf_bull_space))


# =============================================================================
# 6. Assemble the bridge
# =============================================================================
def bridge(target_equity_b: float = TARGET_B, conn_scn: str = "Bull",
           space_scn: str = "Bull", space_bonus_b: float = 0.0,
           a: dcf.ValuationAssumptions | None = None) -> dict:
    """Full residual bridge to the target, plus the AI-ask cross-checks.

    Returns the bridge components ($B), the implied AI revenue multiple (on the super-bull
    FY2030 AI revenue), the break-even AGI probability at a few payoff anchors, and the
    super-bull AI EV for comparison to the required AI EV.
    """
    a = a or dcf.default_assumptions()
    req = required_ai_ev(target_equity_b, conn_scn, space_scn, space_bonus_b, a)
    sb = super_bull_ai_ev(a=a)
    ai_req = req["ai_required_ev"]

    mult = implied_ai_multiple(ai_req, sb["fwd_rev_2030"])
    # Break-even AGI odds at illustrative franchise payoffs.
    payoffs_b = [1000, 2000, 4000, 8000]
    breakeven_p = {f"${v:,}B": agi_required_p(ai_req, v * 1000) for v in payoffs_b}

    return dict(
        target_equity_b=target_equity_b,
        components_b=dict(
            Connectivity=req["conn_ev"] / 1000,
            Space=req["space_ev"] / 1000,
            **({"Space mega-bull": req["space_bonus"] / 1000} if space_bonus_b else {}),
            **{"AI (required)": ai_req / 1000},
            **{"less: net debt": -req["net_debt"] / 1000},
        ),
        ai_required_ev_b=ai_req / 1000,
        super_bull_ai_ev_b=sb["ev"] / 1000,
        super_bull_fwd_rev_b=sb["fwd_rev_2030"] / 1000,
        implied_ai_ev_rev_mult=mult,
        required_mature_fcf_b=required_mature_fcf(ai_req, a) / 1000,
        breakeven_agi_p=breakeven_p,
        assumptions=dict(conn_scn=conn_scn, space_scn=space_scn,
                         net_debt_b=req["net_debt"] / 1000),
    )


# =============================================================================
# 7. Reversed Bayesian — the $10T AGI lottery, priced across every lab
# =============================================================================
# The football-field real-option asked "what P×V justifies SpaceX's AI?". Flip it:
# fix a single transformative-AI prize V (a $10T stand-in for the AGI TAM), assume each
# lab is a ticket on it, and read each lab's *market valuation* as an implied P. Then the
# question stops being abstract — it becomes "does the $1T SpaceX mark imply that xAI is a
# better AGI bet than OpenAI or Anthropic?" (Spoiler: per-dollar-of-revenue, yes.)
def _spacex_ai_runrate_b() -> float:
    """SpaceX AI-segment FY2025 revenue ($B) — the real S-1 number, its no-AGI floor base."""
    return float(val.segment_metrics().loc["AI", "revenue"]) / 1000


def agi_lottery_table(prize_b: float = 10_000.0, floor_mult: float = 12.0,
                      target_equity_b: float = TARGET_B,
                      a: dcf.ValuationAssumptions | None = None) -> pd.DataFrame:
    """Implied P(this lab wins a common $V AGI prize) backed out of each lab's valuation.

    Two reads per lab:
      * ``p_pure``  — naive: ``valuation / prize`` (the whole value is the AGI ticket).
      * ``p_floor`` — credit a *no-AGI* business worth ``floor_mult × revenue run-rate``
        first; only the **residual** option value is the AGI bet, so
        ``p = (valuation − floor) / prize``. This is the fair comparison: OpenAI/Anthropic
        have huge real revenue doing the heavy lifting, xAI almost none.

    Rows: the three frontier labs (external, ``csv/ai_labs.csv``) plus **SpaceX's AI as the
    \\$1T mark implies it** (the residual AI EV from :func:`required_ai_ev`, on the real S-1
    AI-segment revenue). Alphabet is excluded — its value is a profitable business, not a
    lottery ticket. Returns a tidy frame in \\$B / probabilities.
    """
    a = a or dcf.default_assumptions()
    labs = load_ai_labs()
    rows = []
    for ent in ["OpenAI", "Anthropic", "xAI"]:
        r = labs[labs.entity == ent].iloc[0]
        rows.append(dict(entity=ent, kind="lab", valuation_b=float(r.valuation_usd_b),
                         runrate_b=float(r.rev_runrate_usd_b)))
    ai_req_b = required_ai_ev(target_equity_b, a=a)["ai_required_ev"] / 1000
    rows.append(dict(entity=f"SpaceX·AI (implied @ ${target_equity_b/1000:.0f}T)",
                     kind="spacex", valuation_b=ai_req_b, runrate_b=_spacex_ai_runrate_b()))
    df = pd.DataFrame(rows)
    df["floor_b"] = floor_mult * df.runrate_b
    df["p_pure"] = df.valuation_b / prize_b
    df["p_floor"] = (df.valuation_b - df.floor_b).clip(lower=0) / prize_b
    df["val_per_rev"] = df.valuation_b / df.runrate_b
    df["prize_b"] = prize_b
    return df


# =============================================================================
# 8. The infrastructure story — decode the super-bull into atoms, watts & a grid
# =============================================================================
PUE = 1.35                     # facility power / IT power (cooling, conversion overhead)
REACTOR_GW = 1.0               # nameplate of a large nuclear reactor (~1 GW)
US_GRID_CAPACITY_GW = 1_200.0  # ~US total generating capacity
US_AVG_DEMAND_GW = 500.0       # ~US average electricity demand


def infra_decode(gw: float) -> dict:
    """Translate a 2030 AI nameplate (GW) into the physical build it implies.

    The super-bull is not a spreadsheet cell — it is silicon, capex and *power*. This makes
    that legible: GPUs, cumulative build capex, and electricity (in reactor- and grid-share
    terms), so the 'just crank the dials' bull has to own what the dials mean.
    """
    fac = gw * PUE
    return dict(nameplate_gw=gw,
                gpus_m=gw * GPU_PER_GW / 1e6,
                build_capex_b=gw * CAPEX_PER_GW / 1000,
                it_power_gw=gw, facility_power_gw=fac,
                reactor_equiv=fac / REACTOR_GW,
                pct_us_capacity=fac / US_GRID_CAPACITY_GW,
                pct_us_demand=fac / US_AVG_DEMAND_GW)


def super_bull_ev_grid(gws, prices, util: float = 0.88, chip_life: float = 6.0,
                       rm: float = 0.65, a: dcf.ValuationAssumptions | None = None) -> pd.DataFrame:
    """AI segment EV ($B) over a (nameplate GW × blended \\$/GPU-hr) grid — for a heatmap.

    Rows = price ($/GPU-hr), cols = nameplate GW; every cell is a full super-bull DCF. The
    notebook contours this at the required AI EV so you can see the whole (scale × price)
    frontier that clears \\$1T, not just one path.
    """
    a = a or dcf.default_assumptions()
    grid = pd.DataFrame(index=[f"{p:.1f}" for p in prices],
                        columns=[f"{g:.0f}" for g in gws], dtype=float)
    for p in prices:
        for g in gws:
            d = AISuperBull(gw=g, util=util, price=p, chip_life=chip_life, rm=rm)
            grid.loc[f"{p:.1f}", f"{g:.0f}"] = super_bull_ai_ev(d, a)["ev"] / 1000
    return grid


if __name__ == "__main__":  # quick smoke test / reverse-engineering summary
    pd.set_option("display.width", 120)
    a = dcf.default_assumptions()
    for tgt in (1000.0, 1250.0, 1750.0):
        b = bridge(tgt, a=a)
        print(f"\n=== Reverse-engineering ${tgt/1000:.2f}T equity (Bull Starlink + Bull Space) ===")
        for k, v in b["components_b"].items():
            print(f"  {k:18} ${v:8.0f}B")
        print(f"  {'TARGET equity':18} ${tgt:8.0f}B")
        print(f"  -> AI must be worth     ${b['ai_required_ev_b']:.0f}B "
              f"(our super-bull AI DCF only gets to ${b['super_bull_ai_ev_b']:.0f}B)")
        print(f"  -> implied AI multiple  {b['implied_ai_ev_rev_mult']:.0f}x super-bull FY2030 AI rev "
              f"(${b['super_bull_fwd_rev_b']:.0f}B)")
        print(f"  -> needs mature AI FCF  ${b['required_mature_fcf_b']:.0f}B/yr")
        print(f"  -> break-even AGI odds: " +
              ", ".join(f"{p} @ {v}" for v, p in b["breakeven_agi_p"].items()))

    print("\n=== Reversed Bayesian: implied P(win a $10T AGI prize) across labs ===")
    lt = agi_lottery_table()
    disp = lt[["entity", "valuation_b", "runrate_b", "val_per_rev", "p_pure", "p_floor"]].copy()
    for c in ["p_pure", "p_floor"]:
        disp[c] = (disp[c] * 100).round(1).astype(str) + "%"
    print(disp.to_string(index=False))

    print("\n=== Infra decode of the ~17 GW cash path to $1T ===")
    for gw in (7, 17, 25):
        d = infra_decode(gw)
        print(f"  {gw:2d} GW IT -> {d['gpus_m']:.1f}M GPUs, ${d['build_capex_b']:.0f}B build, "
              f"{d['facility_power_gw']:.0f} GW facility power "
              f"(~{d['reactor_equiv']:.0f} reactors, ~{d['pct_us_capacity']:.1%} of US capacity)")
