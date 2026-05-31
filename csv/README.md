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

## Validation
`validate.py` re-checks that subtotals reconcile (segments → consolidated, components → totals,
disaggregated revenue → segment revenue, etc.). Run: `python3 validate.py`.
