# SpaceX S-1 — Project Guide

## Goal
Build a **DCF valuation model** and an **analyst report** for the upcoming **SpaceX IPO**,
working from the company's Form S-1 financials. The report is deliberately **tuned to a
technical audience** — readers who deeply understand **AI and Space** but are *not*
necessarily finance professionals. That framing drives every choice:

- **Explain the finance, assume the tech.** Define WACC, terminal value, FCF, dilution, etc.
  in plain language; do *not* over-explain what Starship, Starlink, nameplate compute, or
  inference economics are.
- **Lead with the engineering/operating story**, then connect it to the numbers
  (e.g. mass-to-orbit and launch cadence → Space revenue; subscriber + ARPU → Connectivity;
  compute draw and capex → AI economics).
- Favor **clear visuals and intuition** over dense financial tables.

## Deliverables
1. **DCF model** — segment-level (Space / Connectivity / AI), scaffolded in `analysis/dcf.py`.
   Revenue forecast → margins → unlevered FCF → WACC discounting + terminal value →
   EV → equity value → implied per-share, plus a terminal-growth × WACC sensitivity grid.
2. **Analyst report** — narrative + charts built on the model and the extracted data.

## Repository layout
```
spacex_s1/
├── CLAUDE.md            <- this file
├── MANIFEST.md          <- inventory of every source file + what data it holds
├── requirements.txt     <- pandas, matplotlib, numpy
├── .venv/               <- Python virtual environment (see below)
├── source_docs/         <- original S-1 PDFs (8) and screenshots (20)  [read-only source of truth]
├── csv/                 <- extracted data, tidy/long format (18 datasets) + README + validate.py
└── analysis/            <- Python package (setup only so far; no analysis run yet)
    ├── data.py          <- loaders for csv/ -> pandas DataFrames + reshape helpers
    ├── charts.py        <- matplotlib house style + thin chart helpers (segment color identity)
    └── dcf.py           <- DCF model scaffold (structure/assumptions stubs, not yet implemented)
```

## Environment
A virtualenv lives at `.venv/`. Use it for all Python:
```bash
./.venv/bin/python <script.py>          # run a script
./.venv/bin/python -m pip install ...   # add a dependency (then update requirements.txt)
source .venv/bin/activate               # or activate the shell
```

## Working with the data
- Source of truth for figures is `source_docs/`; `csv/` is the cleaned extraction. If a number
  looks off, check it against the source doc named in `MANIFEST.md`.
- `csv/validate.py` re-checks that subtotals reconcile (65 checks). Re-run after any edit to a CSV:
  `./.venv/bin/python csv/validate.py`.
- Load data via the package, don't re-parse CSVs ad hoc:
  ```python
  from analysis import data, charts
  d = data.load_all()                                   # dict of DataFrames
  charts.apply_style()                                  # before plotting
  conn = data.wide(d["segment_pl"], "line_item",
                   filt={"segment": "Connectivity"})    # statement-style pivot
  ```

## Data conventions (mirror these everywhere)
- Dollars in **millions USD** unless a `unit` column says otherwise.
- Filing parentheses → **negative numbers**; em-dashes (`—`) → `0`.
- Periods: `FY2023`/`FY2024`/`FY2025` (years ended Dec 31), `Q1-2025`/`Q1-2026`
  (three months ended Mar 31). `period` is an ordered categorical in loaded frames.
- Segments: `Space`, `Connectivity`, `AI` (+ `Total Reportable Segments` where reported).
- Balance-sheet dates are ISO (`2026-03-31`, `2025-12-31`, `2024-12-31`).

## Key facts to keep in mind (from the S-1)
- FY2025: revenue **$18,674M** (+33% YoY); net loss **$(4,937)M**; Adjusted EBITDA **$6,584M**.
- Q1-2026: revenue **$4,694M**; net loss **$(4,276)M**, inflated by a **$1,526M loss on debt
  extinguishment** (refinancing X/xAI term loans into the **$20,000M SpaceX Bridge Loan**, Mar 2026).
- Segment shape: **Connectivity** (Starlink) is the profit engine; **AI** is the heavy investment
  zone (FY2025 R&D $5,064M, capex $12,727M, EBITDA $(1,237)M); **Space** roughly breakeven.
- Capital structure: the IPO triggers a **preferred → common conversion** (see `capitalization.csv`
  Actual vs Pro Forma); Bridge Loan must be substantially repaid from IPO proceeds.

## Status / next steps
- [x] Extract all S-1 data to tidy CSVs (`csv/`), validated.
- [x] Align manifest to `source_docs/`.
- [x] Python environment + analysis/charts/dcf scaffolding (setup only — nothing computed yet).
- [ ] Build the DCF (fill in `analysis/dcf.py` assumptions and model steps).
- [ ] Produce report charts and the written analyst report.

**Important:** Per current direction, we are only *setting up* — do not run analysis or
generate charts/forecasts until asked.
