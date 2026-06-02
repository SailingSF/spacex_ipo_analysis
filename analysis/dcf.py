"""Segment-level DCF valuation for SpaceX, built off the S-1 fundamentals.

This module turns the integrated funding model (``notebooks/integrated.ipynb``)
into an actual per-share value. The chain is the standard one, kept deliberately
legible so the report can show its work:

    explicit-period unlevered FCF (FY2026-FY2030, by segment, per scenario)
      -> discount at WACC
      -> + terminal value (segment-normalized steady state; AI off the §6 frontier)
      = enterprise value
      -> - net debt                          (debt_schedule.csv, Mar-31-2026)
      = equity value
      -> / pro-forma shares                  (capitalization.csv, post-conversion)
      = implied value per share
    + a terminal-growth x WACC sensitivity grid.

Design choices (all explicit and stress-testable):

* **One canonical scenario engine.** The Bear/Base/Bull segment FCF paths are the
  same ones ``integrated.ipynb`` charts; that logic lives *here* now so the DCF and
  the funding notebook can't drift. ``project_segments(scn)`` reproduces each
  sibling notebook's levers (subs x ARPU for Connectivity; ``space_economics``
  franchise + Starship commercialization for Space; GW x utilization x $/GPU-hr for AI).
* **Unlevered FCF = op_income + D&A + SBC - capex**, summed across segments — the
  segment-summable proxy that ties to consolidated CFO-capex (integrated §1). SBC
  is added back as the non-cash charge it is; its cost re-appears as *dilution*,
  which we DEFER to a follow-on step (see "Deferred" below).
* **Terminal value is where the thesis lives.** Raw FY2030 FCF is still mid-build
  (AI capex hasn't normalized), so a Gordon perpetuity on it would be nonsense.
  Instead each segment gets a *normalized steady-state* terminal FCF: Connectivity
  and Space off their FY2030 run-rate (capex glided to maintenance), and **AI off
  the integrated §6 feasibility frontier** — the mature, done-growing fleet whose
  only capex is chip refresh. That makes "does AI ever clear the frontier?" the
  single switch that turns terminal value, exactly as the integrated hand-off said.
* **AI terminal is floored at zero (abandonment option).** A mature fleet that is
  FCF-negative even on refresh would simply *not be refreshed* — you run the chips
  to end-of-life and stop, you don't burn cash into perpetuity. So AI's terminal
  contribution is ``max(0, gordon)`` by default; set ``floor_ai_terminal=False`` to
  see the unfloored perpetual-drag case.

Deferred to follow-on steps (intentionally, so the bear/base/bull per-share is a
clean read first):
  * **Future equity raises / dilution.** The explicit period burns cash (integrated
    §5: ~$74-92B in bear/base); funding it issues shares. We value on the *current*
    pro-forma share count and treat the dilution path as a separate report step.
  * **Cash taxes.** Held at 0 — a $41B accumulated deficit plus continuing heavy
    D&A/R&D shields make near-zero cash tax defensible for years. ``tax_rate`` is
    exposed for stress-testing.
  * **Depreciation schedule refinement** beyond the segment models' own D&A.

Nothing runs on import. Build assumptions with :func:`default_assumptions`, pick a
scenario, and call :func:`value_scenario`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from analysis.connectivity_economics import ConnectivityModel
from analysis.space_economics import SpaceModel, SS_YEAR, project_space_forward
from analysis.ai_economics import AIModel

# --- horizon -----------------------------------------------------------------
BASE_YEAR = 2025                       # last full actual fiscal year
YEARS = [2026, 2027, 2028, 2029, 2030] # explicit forecast period
SEGMENTS = ["Connectivity", "Space", "AI"]

_g = lambda a, b: np.linspace(a, b, 5)  # 5-year linear glide, FY2026..FY2030


# =============================================================================
# 1. Scenario dials  (canonical; mirrored from the segment + integrated notebooks)
# =============================================================================
# Each scenario fixes ALL three segments AND the Starship commercialization year
# together, because they are coupled: cheap launch is what lets Starlink hold its
# margin and is what makes the AI build cheaper to deploy.
# Starship commercialization year lives in space_economics.SS_YEAR (Space + Connectivity coupling).
SS_CAPEX_CUT = {"Bear": 0.15, "Base": 0.25, "Bull": 0.35}   # $/kg-driven cut to new sat-launch capex

# Connectivity: subs growth glide, ARPU floor ($/mo), non-consumer growth, op margin,
# terminal D&A %, starting capex %.
CN = {"Bear": dict(sub=[.50, .30, .20, .15, .10], af=35, ng=.15, opm=.35, da1=.13, cx0=.42),
      "Base": dict(sub=[.80, .55, .40, .30, .20], af=45, ng=.25, opm=.40, da1=.12, cx0=.48),
      "Bull": dict(sub=[1.0, .80, .60, .45, .30], af=55, ng=.40, opm=.45, da1=.11, cx0=.52)}
SUBS0, ARPU0 = 8.9, 81.0   # FY2025 year-end subscribers (M), FY2025 ARPU ($/mo)

# AI: 2030 nameplate (GW), utilization, blended $/GPU-hr, ad growth, refresh chip life (yrs), R&D multiple.
AM = {"Bear": dict(gw=2.0, u=.55, pr=1.2, ag=-.05, rl=3.0, rm=1.00),
      "Base": dict(gw=4.0, u=.70, pr=1.6, ag=-.02, rl=4.5, rm=0.85),
      "Bull": dict(gw=7.0, u=.85, pr=2.2, ag=.00,  rl=6.0, rm=0.65)}
GPU_PER_GW, HRS, CAPEX_PER_GW, BOOK_LIFE = 600_000, 8760, 22_000, 4.5  # ~$22B builds ~1GW (~600k GPUs)
GW0, UTIL0, PRICE0, GROSS0 = 1.0, 0.50, 2.0, 22_700.0  # today: ~1GW, ~50% util, ~$2/hr, $22.7B gross fleet

# Group financing (explicit period). Net debt / shares come from the CSVs (loaded below).
INTEREST = np.array([1.6, 1.8, 2.0, 2.2, 2.4]) * 1000   # post-refi cash interest, $M
BRIDGE   = np.array([0, 20000, 0, 0, 0])               # $20B bridge bullet (Sep-2027), repaid from the raise


# =============================================================================
# 2. The segment FCF engine  (FY2026-FY2030, per scenario)
# =============================================================================
def _actuals():
    """FY2025 segment baselines pulled live from the validated S-1 CSVs."""
    C = ConnectivityModel().raw(); S = SpaceModel().raw(); A = AIModel().raw()
    return C, S, A


def _conn(scn: str, C: pd.DataFrame) -> pd.DataFrame:
    """Connectivity FCF path: subs x ARPU, op-margin held, capex/D&A glide."""
    p = CN[scn]
    nonc0 = C.loc["FY2025", "revenue"] - (4.4 + 8.9) / 2 * ARPU0 * 12  # FY2025 non-consumer revenue
    subs = [SUBS0]
    for r in p["sub"]:
        subs.append(subs[-1] * (1 + r))
    subs = np.array(subs)
    arpu = _g(ARPU0, p["af"]); avg = (subs[:-1] + subs[1:]) / 2
    consumer = avg * arpu * 12
    nonconsumer = np.array([nonc0 * (1 + p["ng"]) ** (i + 1) for i in range(5)])
    rev = consumer + nonconsumer
    op = rev * p["opm"]; da = rev * _g(.205, p["da1"]); sbc = rev * .03
    capex = rev * _g(p["cx0"], p["da1"] + .01)
    for i, y in enumerate(YEARS):  # Starship $/kg cut shaves sat-launch capex once commercial
        if y >= SS_YEAR[scn]:
            capex[i] *= (1 - SS_CAPEX_CUT[scn] * 0.5)
    return pd.DataFrame(dict(rev=rev, op=op, da=da, sbc=sbc, capex=capex,
                             fcf=op + da + sbc - capex, subs=subs[1:], arpu=arpu), index=YEARS)


def _space(scn: str) -> pd.DataFrame:
    """Space FCF path — canonical engine in ``space_economics.project_space_forward`` (``space.ipynb`` §6–§7)."""
    f = project_space_forward(scn)
    return f.rename(columns={"revenue": "rev", "op_income": "op"})[
        ["rev", "op", "da", "sbc", "capex", "fcf"]
    ]


def _ai(scn: str) -> pd.DataFrame:
    """AI FCF path: GW x utilization x $/GPU-hr; depreciation scales with the build."""
    p = AM[scn]
    gw = _g(GW0, p["gw"]); util = _g(UTIL0, p["u"]); price = _g(PRICE0, p["pr"])
    gw_prev = np.concatenate([[GW0], gw[:-1]]); gross = GROSS0; out = []
    for i, y in enumerate(YEARS):
        compute = gw[i] * GPU_PER_GW * price[i] * HRS * util[i] / 1e6   # monetizable compute ($M)
        ads = 1844 * (1 + p["ag"]) ** (i + 1)                          # legacy X advertising, fading
        rev = compute + ads
        build = max(0, gw[i] - gw_prev[i]) * CAPEX_PER_GW              # new GW
        refresh = gross / p["rl"]                                      # the treadmill: re-buy aging chips
        capex = build + refresh; gross += build
        da = gross / BOOK_LIFE
        rnd = 5064 * p["rm"]                                           # model-training R&D (recurring)
        power = gw[i] * 65 * HRS * 1000 * util[i] / 1e6               # GW * $/MWh * hrs * util
        sga, sbc = 1827 * 1.05 ** (i + 1), 1063
        op = rev - rev * 0.25 - power - da - rnd - sga                 # cash COGS ~25% + power + D&A + R&D + SG&A
        out.append(dict(gw=gw[i], util=util[i], price=price[i], compute=compute, rev=rev,
                        op=op, da=da, sbc=sbc, capex=capex, fcf=op + da + sbc - capex))
    return pd.DataFrame(out, index=YEARS)


def project_segments(scenario: str, actuals=None) -> dict[str, pd.DataFrame]:
    """Return {'Connectivity','Space','AI'} -> FY2026-FY2030 FCF DataFrames for a scenario."""
    C, S, A = actuals if actuals is not None else _actuals()
    return {"Connectivity": _conn(scenario, C), "Space": _space(scenario), "AI": _ai(scenario)}


def group_fcf(proj: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Assemble segment FCF into a group table (unlevered, levered, external need)."""
    grp = proj["Connectivity"].fcf + proj["Space"].fcf + proj["AI"].fcf
    lev = grp - INTEREST
    ext = -lev + BRIDGE
    return pd.DataFrame(dict(Connectivity=proj["Connectivity"].fcf, Space=proj["Space"].fcf,
                             AI=proj["AI"].fcf, Group=grp, Levered=lev, ExtNeed=ext), index=YEARS)


# =============================================================================
# 3. Terminal value  (normalized steady state; AI off the §6 frontier)
# =============================================================================
def ai_mature_fcf(scenario: str, util: float | None = None, price: float | None = None,
                  chip_life: float = BOOK_LIFE) -> float:
    """Mature AI-fleet steady-state FCF ($M/yr): done growing, only chip refresh remains.

    This is the integrated §6 feasibility frontier evaluated at a scenario's mature
    fleet — the honest terminal number for AI. Negative means the fleet never covers
    its own refresh + power + R&D at that utilization/price.
    """
    p = AM[scenario]
    util = p["u"] if util is None else util
    price = p["pr"] if price is None else price
    gw = p["gw"]
    gross = GROSS0 + (gw - GW0) * CAPEX_PER_GW            # legacy fleet + the build
    compute = gw * GPU_PER_GW * price * HRS * util / 1e6
    ads = 1844 * 0.98 ** 5                                # advertising faded out
    rev = compute + ads
    power = gw * 65 * HRS * 1000 * util / 1e6
    rnd = 5064 * p["rm"]
    sga = 1827 * 1.05 ** 5
    refresh = gross / chip_life
    # SBC (~$1.06B) is non-cash; add it back to match the unlevered-FCF convention.
    return rev - rev * 0.25 - power - rnd - sga - refresh + 1063


def terminal_fcf(scenario: str, proj: dict[str, pd.DataFrame]) -> dict[str, float]:
    """Normalized steady-state FCF entering the terminal period, by segment ($M/yr)."""
    # Space: FY2030 capex still compounds at ``cxg`` (~2.5-3x D&A) — it is mid-build,
    # NOT a steady state, so the raw FY2030 FCF is the wrong terminal input (it makes
    # the launch monopoly worth *negative* EV). Normalize capex to maintenance (= D&A),
    # exactly as Connectivity's capex glides to ~D&A by FY2030, so the Gordon perpetuity
    # grows a mature franchise rather than one still in heavy expansion.
    sp = proj["Space"].iloc[-1]
    space_term = float(sp.op + sp.da + sp.sbc - sp.da)  # capex set to maintenance (= D&A)
    return {
        "Connectivity": float(proj["Connectivity"].fcf.iloc[-1]),  # FY2030 run-rate (capex already glided to ~D&A)
        "Space":        space_term,                                # capex normalized to maintenance (= D&A)
        "AI":           ai_mature_fcf(scenario),                   # §6 frontier, NOT mid-build FY2030
    }


# =============================================================================
# 4. Valuation assumptions + the DCF
# =============================================================================
@dataclass
class ValuationAssumptions:
    """Top-level valuation inputs. Defaults are the base-case calibration."""
    wacc: float = 0.12             # single group discount rate (AI arguably deserves higher; see notebook)
    terminal_growth: float = 0.03  # perpetuity growth (~long-run nominal GDP)
    tax_rate: float = 0.0          # cash tax — 0 via NOLs (deferred); exposed for stress tests
    net_debt: float | None = None  # $M; from debt_schedule.csv if None
    shares_m: float | None = None  # pro-forma diluted shares (M); from capitalization if None
    floor_ai_terminal: bool = True # AI terminal = max(0, gordon): you can stop refreshing the fleet
    mid_year: bool = False         # mid-year discounting convention

    def __post_init__(self):
        if self.net_debt is None:
            self.net_debt = net_debt_from_csv()
        if self.shares_m is None:
            self.shares_m = PROFORMA_SHARES_M


# Pro-forma diluted share count, post preferred conversion + Class C reclassification,
# BEFORE the IPO primary issuance (capitalization.pdf, as of Mar-31-2026):
#   Class A 6,824,581,339 + Class B 5,695,729,430 = 12,520,310,769
PROFORMA_SHARES_M = (6_824_581_339 + 5_695_729_430) / 1e6  # ≈ 12,520.3M


def net_debt_from_csv() -> float:
    """Net debt ($M) as of Mar-31-2026: total debt + finance leases - cash."""
    from analysis import data
    d = data.load_all()
    ds = d["debt_schedule"]
    total = ds[(ds.instrument == "Total debt and finance leases") &
               (ds.date == "2026-03-31")]["net"].iloc[0]
    cap = d["capitalization"]
    cash = cap[(cap.line_item == "Cash and cash equivalents") &
               (cap.basis == "Actual")]["value"].iloc[0]
    return float(total - cash)


def discount_factors(wacc: float, n: int = 5, mid_year: bool = False) -> np.ndarray:
    """Year-end (or mid-year) discount factors for t = 1..n."""
    t = np.arange(1, n + 1) - (0.5 if mid_year else 0.0)
    return 1.0 / (1.0 + wacc) ** t


def value_scenario(scenario: str, a: ValuationAssumptions | None = None,
                   actuals=None) -> dict:
    """Run the full DCF for one scenario. Returns a dict of every intermediate.

    Keys: ``proj`` (segment FCF), ``group``, ``explicit_pv`` / ``terminal_pv`` /
    ``ev`` (per segment + total), ``terminal_fcf``, ``equity_value``,
    ``per_share``, and the assumptions used.
    """
    a = a or ValuationAssumptions()
    proj = project_segments(scenario, actuals=actuals)
    grp = group_fcf(proj)
    df = discount_factors(a.wacc, len(YEARS), a.mid_year)
    tf = terminal_fcf(scenario, proj)

    explicit_pv, terminal_pv, ev = {}, {}, {}
    for seg in SEGMENTS:
        fcf = proj[seg].fcf.values * (1 - a.tax_rate * (proj[seg].fcf.values > 0))
        explicit_pv[seg] = float(np.sum(fcf * df))
        # Gordon terminal on normalized steady-state FCF, discounted back 5 years.
        gordon = tf[seg] * (1 + a.terminal_growth) / (a.wacc - a.terminal_growth)
        if seg == "AI" and a.floor_ai_terminal:
            gordon = max(0.0, gordon)   # abandonment option: stop refreshing rather than burn forever
        terminal_pv[seg] = float(gordon * df[-1])
        ev[seg] = explicit_pv[seg] + terminal_pv[seg]

    ev_total = sum(ev.values())
    equity = ev_total - a.net_debt
    per_share = equity / a.shares_m  # $M / M shares = $/share (RAW — can go negative)

    # --- limited liability: equity is a call option on the enterprise; it can't
    # be worth less than zero. A negative raw value is a *signal of insolvency on
    # that path*, not a price. Floor it.
    equity_floored = max(0.0, equity)

    # --- sum-of-the-parts / abandonment-consistent value. A rational owner stops
    # funding a segment whose own DCF is negative (integrated §8: the AI burn is
    # self-limiting — capital throttles it), so the going concern is worth at
    # least its *surviving* parts. Floor each segment EV at 0 before summing, then
    # bridge net debt (all of it charged against the survivors — conservative for
    # equity). This is the honest floor the raw DCF misses: even in the bear you
    # still own Starlink and simply don't pour cash into the furnace.
    ev_sotp = sum(max(0.0, v) for v in ev.values())
    equity_sotp = max(0.0, ev_sotp - a.net_debt)

    return dict(scenario=scenario, assumptions=a, proj=proj, group=grp,
                terminal_fcf=tf, explicit_pv=explicit_pv, terminal_pv=terminal_pv,
                ev=ev, ev_total=ev_total, net_debt=a.net_debt,
                equity_value=equity, shares_m=a.shares_m, per_share=per_share,
                equity_floored=equity_floored, per_share_floored=equity_floored / a.shares_m,
                ev_sotp=ev_sotp, equity_sotp=equity_sotp,
                per_share_sotp=equity_sotp / a.shares_m)


def value_all(a: ValuationAssumptions | None = None) -> pd.DataFrame:
    """Per-share summary across Bear / Base / Bull (shares one CSV load).

    Three reads per scenario, weakest-to-strongest claim on reality:
      * ``$/sh raw``     — the unfloored DCF (can be negative = modeled insolvency).
      * ``$/sh floored``  — same, but equity floored at 0 (limited liability).
      * ``$/sh SOTP``     — abandonment-consistent: value-destroying segments shut,
                            so the floor is roughly standalone Starlink. The number
                            we'd actually carry to the report as the bear floor.
    """
    a = a or ValuationAssumptions()
    act = _actuals()
    rows = {}
    for s in ["Bear", "Base", "Bull"]:
        r = value_scenario(s, a, actuals=act)
        rows[s] = {"EV ($B)": r["ev_total"] / 1000,
                   "Net debt ($B)": r["net_debt"] / 1000,
                   "Equity ($B)": r["equity_value"] / 1000,
                   "$/sh raw": r["per_share"],
                   "$/sh floored": r["per_share_floored"],
                   "$/sh SOTP": r["per_share_sotp"]}
    return pd.DataFrame(rows).T


# =============================================================================
# 5. Dilution — turning the pre-money per-share into what a TODAY holder keeps
# =============================================================================
@dataclass
class DilutionAssumptions:
    """Drivers for the funding-path / dilution step.

    The conceptual crux (and the thing most "dilution" hand-waving gets wrong):
    **the cash burn is ALREADY inside the DCF** — it's the negative explicit-period
    FCF that EV is net of. So funding that burn by issuing equity *at fair value*
    is an NPV-neutral swap (you get $1 of cash, you give $1 of stock); it does NOT
    lower intrinsic value per share, it only shrinks each holder's **ownership %**.

    The genuine per-share *value* haircut is therefore NOT the raise itself — it's
    only what you give away by issuing **below** fair value (IPO/follow-on/down-round
    discount) plus banking **fees**. That value transfer to new holders is the real
    cost; the headline "sold ~a third of the company" is an ownership story, largely
    distinct from the value-per-share story.
    """
    equity_share_of_gap: float = 0.80   # fraction of the external need raised as equity
                                        # (rest is debt — but debt just reloads the maturity wall, debt nb §5–7)
    issue_discount: float = 0.15        # avg issue price discount to intrinsic (IPO pop + follow-on + down-round risk)
    financing_fee: float = 0.04         # underwriting / placement fees as % of gross raise


def funding_need(scenario: str, keep_ai: bool = True, actuals=None) -> float:
    """Net cumulative external capital needed over FY2026–FY2030 ($M).

    = Σ ExtNeed (incl. cash interest + the $20B bridge takeout, net of any late-year
    surpluses that repay it). Ties to integrated §5 (~$16B/$74B/$91B Bull/Base/Bear).

    ``keep_ai=False`` (the abandonment world) zeroes AI's forward cash flows — you
    wind the segment down rather than fund its build — so the gap collapses to roughly
    the bridge + interest net of Starlink's surplus. The funding gap IS the cost of
    keeping AI, so this flag must match the valuation basis (abandon ↔ SOTP).
    """
    proj = project_segments(scenario, actuals=actuals)
    if not keep_ai:
        proj = dict(proj); proj["AI"] = proj["AI"].copy(); proj["AI"]["fcf"] = 0.0
    return float(group_fcf(proj)["ExtNeed"].sum())


def dilution(scenario: str, a: ValuationAssumptions | None = None,
             da: DilutionAssumptions | None = None, basis: str = "sotp",
             actuals=None) -> dict:
    """Quantify ownership vs. value dilution from funding the plan with equity.

    ``basis`` picks the pre-money equity (``'sotp'`` default / ``'floored'`` / ``'raw'``).
    Returns the equity raise, new shares, ownership retained, and the *value* haircut —
    which is only the issue-discount + fee transfer, NOT the whole raise.
    """
    a = a or ValuationAssumptions()
    da = da or DilutionAssumptions()
    r = value_scenario(scenario, a, actuals=actuals)
    key = {"sotp": "equity_sotp", "floored": "equity_floored", "raw": "equity_value"}[basis]
    pre_equity = max(0.0, r[key])
    pre_ps = pre_equity / a.shares_m

    # Gap must match the AI decision: SOTP = abandon AI (gap collapses), else keep it.
    keep_ai = basis != "sotp"
    gap = funding_need(scenario, keep_ai=keep_ai, actuals=actuals)
    equity_raise = max(0.0, gap) * da.equity_share_of_gap

    # Wipeout: if the business has ~no equity but still needs a raise, current
    # holders can't be funded without ceding ~everything — value goes to ~0.
    if pre_equity <= 0 and equity_raise > 0:
        return dict(scenario=scenario, basis=basis, pre_equity=pre_equity, pre_ps=pre_ps,
                    gap=gap, equity_raise=equity_raise, new_shares=float("inf"),
                    ownership_retained=0.0, ownership_sold=1.0, value_transfer=pre_equity,
                    post_equity_existing=0.0, post_ps=0.0, value_haircut_pct=1.0, wipeout=True)

    # Ownership dilution: new shares sold at the discounted issue price.
    issue_ps = pre_ps * (1 - da.issue_discount)
    new_shares = equity_raise / issue_ps if issue_ps > 0 else float("inf")
    ownership_retained = a.shares_m / (a.shares_m + new_shares) if new_shares != float("inf") else 0.0

    # VALUE dilution to existing holders = value handed to new holders by selling
    # below fair value, + fees. (The raise itself is NPV-neutral; only the discount bites.)
    value_transfer = equity_raise * (da.issue_discount / (1 - da.issue_discount)) \
        + equity_raise * da.financing_fee
    post_equity_existing = max(0.0, pre_equity - value_transfer)
    post_ps = post_equity_existing / a.shares_m

    return dict(scenario=scenario, basis=basis, pre_equity=pre_equity, pre_ps=pre_ps,
                gap=gap, equity_raise=equity_raise, new_shares=new_shares,
                ownership_retained=ownership_retained,
                ownership_sold=1 - ownership_retained, value_transfer=value_transfer,
                post_equity_existing=post_equity_existing, post_ps=post_ps,
                value_haircut_pct=((pre_equity - post_equity_existing) / pre_equity if pre_equity else 0.0),
                wipeout=False)


# Default scenario probabilities for the option-like blend. Deliberately humble:
# the base case is modal, the tails roughly balance. Override per call.
DEFAULT_WEIGHTS = {"Bear": 0.25, "Base": 0.50, "Bull": 0.25}


def expected_value(weights: dict | None = None, a: ValuationAssumptions | None = None,
                   basis: str = "sotp") -> dict:
    """Probability-weighted equity value across Bear/Base/Bull.

    Equity is an option (floored downside, fat-tailed upside), so a single
    probability-weighted number is more honest than any one scenario point.
    ``basis`` selects which per-scenario equity to weight: ``'sotp'`` (default,
    abandonment-floored), ``'floored'`` (limited-liability floor only), or
    ``'raw'`` (unfloored).
    """
    a = a or ValuationAssumptions()
    weights = weights or DEFAULT_WEIGHTS
    act = _actuals()
    key = {"sotp": "equity_sotp", "floored": "equity_floored", "raw": "equity_value"}[basis]
    eq = sum(w * value_scenario(s, a, actuals=act)[key] for s, w in weights.items())
    return dict(basis=basis, weights=weights, equity=eq, per_share=eq / a.shares_m)


def sensitivity_grid(scenario: str, waccs, growths,
                     a: ValuationAssumptions | None = None) -> pd.DataFrame:
    """Per-share value across a WACC (rows) x terminal-growth (cols) grid."""
    a = a or ValuationAssumptions()
    act = _actuals()
    out = pd.DataFrame(index=[f"{w:.0%}" for w in waccs],
                       columns=[f"{gth:.1%}" for gth in growths], dtype=float)
    for w in waccs:
        for gth in growths:
            aa = ValuationAssumptions(wacc=w, terminal_growth=gth, tax_rate=a.tax_rate,
                                      net_debt=a.net_debt, shares_m=a.shares_m,
                                      floor_ai_terminal=a.floor_ai_terminal, mid_year=a.mid_year)
            out.loc[f"{w:.0%}", f"{gth:.1%}"] = value_scenario(scenario, aa, actuals=act)["per_share"]
    return out


def default_assumptions() -> ValuationAssumptions:
    """Base-case valuation assumptions (net debt + shares filled from the CSVs)."""
    return ValuationAssumptions()


if __name__ == "__main__":  # quick smoke test / reconciliation
    a = default_assumptions()
    print(f"Net debt (Mar-2026): ${a.net_debt/1000:.1f}B | Pro-forma shares: {a.shares_m:,.0f}M\n")
    print(value_all(a).round(2).to_string())
    ev = expected_value(a=a)
    print(f"\nProb-weighted (SOTP, {ev['weights']}): "
          f"${ev['equity']/1000:.0f}B equity -> ${ev['per_share']:.2f}/share")

    print("\nDilution — keep AI (fund the furnace) vs abandon AI (keep Starlink):")
    da = DilutionAssumptions()
    for basis, lbl in [("floored", "keep AI"), ("sotp", "abandon AI")]:
        for s in ["Bear", "Base", "Bull"]:
            d = dilution(s, a, da, basis=basis)
            tag = "WIPEOUT" if d["wipeout"] else f"sell {d['ownership_sold']:.0%}, -{d['value_haircut_pct']:.0%} val"
            print(f"  {lbl:11} {s:4}: ${d['pre_ps']:5.2f} -> ${d['post_ps']:5.2f}/sh  "
                  f"(raise ${d['equity_raise']/1000:.0f}B; {tag})")
