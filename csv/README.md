# SpaceX S-1 — Extracted CSVs

Tidy/long-format extraction of the SpaceX Form S-1 financial data (see `../MANIFEST.md`
for the source-file inventory). All values are **raw reported figures** — period-over-period
$ and % changes are intentionally omitted (trivially recomputed).

## Conventions
- **Units**: dollar amounts in **millions USD** unless the `unit` column says otherwise
  (`usd_per_share`, `millions_shares`, `pct`, `metric_tons`, `count`, `gigawatts`, `usd_per_month`).
- **Negatives**: parentheses in the filing are stored as negative numbers (e.g. `(4,276)` → `-4276`).
- **Dashes** (`—`, meaning zero/none) are stored as `0`.
- **Periods**: `Q1-2026`, `Q1-2025` (three months ended Mar 31), `FY2025`/`FY2024`/`FY2023`
  (years ended Dec 31). `period_type` = `quarter` | `year`.
- **Balance-sheet dates**: ISO `YYYY-MM-DD` (`2026-03-31`, `2025-12-31`, `2024-12-31`).
- **Segments**: `Space`, `Connectivity`, `AI`, plus `Total Reportable Segments` where reported.

## Files
| File | Grain | Periods |
|---|---|---|
| `income_statement.csv` | consolidated line item × period | 5 periods + EPS/shares |
| `balance_sheet.csv` | line item × date | 3 dates |
| `cash_flow.csv` | section / line item × period | FY full detail + Q1 summary |
| `comprehensive_income.csv` | line item × period | 5 periods |
| `segment_pl.csv` | segment × line item × period | 5 periods |
| `segment_supplemental.csv` | segment × metric (D&A, SBC, impairment, capex) × period | 5 periods |
| `segment_kpi.csv` | segment × operating KPI × period | 5 periods |
| `segment_adjusted_ebitda.csv` | segment × reconciliation line × period | 5 periods |
| `adjusted_ebitda_consolidated.csv` | reconciliation line × period | 5 periods |
| `revenue_disaggregation.csv` | by product/service & by type+segment | 5 periods |
| `revenue_geography.csv` | geography × period | FY only |
| `debt_schedule.csv` | instrument × date (principal / DFC / net) | 3 dates |
| `debt_terms.csv` | instrument × date (status, rate, effective rate, maturity, secured) | Mar 31 2026 current + Dec 31 2025 extinguished |
| `debt_maturities.csv` | scheduled principal maturity × year (as filed) | as of Dec 31 2025 |
| `capitalization.csv` | line item × basis (Actual / Pro Forma) | Mar 31 2026 |
| `inventory_detail.csv` | component × date | 2 dates |
| `ppe_detail.csv` | component × date | 2 dates |
| `restructuring_rollforward.csv` | liability rollforward | FY2024, FY2025 |
| `space_revenue_mix_pct.csv` | Launch Svc vs Launch & Dev as % of Space rev | 5 periods |
| `other_metrics.csv` | misc (customer concentration, affiliate investments, debt terms) | mixed |

## External data — NOT from the S-1 (quarantined, for the valuation football field)
These two files are the **only** non-S-1 data in `csv/`. They hold market/peer inputs for the
multi-method valuation (`notebooks/valuation.ipynb`) and must stay visually and provenance-distinct
from the filed financials. Every row is date-stamped (`as_of`) and carries a `source_url`; do not
mix them into reconciliation or treat them as facts.
| File | Grain | Notes |
|---|---|---|
| `comps.csv` | segment × valuation metric (multiple band) | **EXTERNAL.** Peer-multiple bands (EV/revenue, EV/EBITDA) by segment + anchor comps & rationale. Multiples only — the S-1 segment metric they multiply comes from `analysis/`. |
| `market_marks.csv` | entity × dated private/secondary mark | **EXTERNAL.** SpaceX / xAI private-round & secondary valuations, each with a `reliability` flag (`established` / `reported` / `speculative`). $350B (Dec-2024) is the conservative anchor; trillion-plus figures are speculative chatter, shown only as ceiling annotations. |
| `gpu_rental_rates.csv` | GPU rental $/hr: H100 history (marketplace vs hyperscaler) + Jun-2026 by chip | **EXTERNAL.** Market GPU rental rates for the AI-segment treadmill/bull-case charts in `notebooks/ai.ipynb`. H100 open-market collapse ($8 peak 2023 -> ~$2 by mid-2025) vs sticky hyperscaler list prices, plus current cross-provider medians by chip generation (A100 -> B300). Mixed methodologies across sources; date-stamped + `reliability`-flagged like the other external files. |
| `ai_labs.csv` | frontier-lab / hyperscaler × valuation + revenue mark | **EXTERNAL.** Frontier-AI-lab marks (OpenAI, Anthropic, xAI) + a hyperscaler (Alphabet) with implied `ev_rev_mult`, for the `$1T-bridge` reverse-valuation in `notebooks/valuation.ipynb` (`analysis/trillion.py`). Several rows were seeded from training knowledge while the live-search API was unavailable — flagged in `note` as **UNVERIFIED at build; refresh** and with `reliability` set accordingly. Refresh + pin the specific `source_url` before relying on them. |

## Validation
`validate.py` re-checks that subtotals reconcile (segments → consolidated, components → totals,
disaggregated revenue → segment revenue, etc.). Run: `python3 validate.py`.
