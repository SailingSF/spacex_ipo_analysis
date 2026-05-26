# SpaceX IPO — Analyst Report

The analysis now lives in **`connectivity.ipynb`** (notes + calculations + charts together), backed by
the reusable compute helper `analysis/connectivity_economics.py` and the loaders in `analysis/data.py`.
Open it from the repo root:

```bash
source .venv/bin/activate && jupyter lab connectivity.ipynb
# or re-execute headless:
./.venv/bin/python -m analysis.connectivity_economics   # CLI sanity check of the same numbers
```

Saved figures land in `output/figures/`.

## Sections so far
1. **Connectivity / Starlink economics** (`connectivity.ipynb`)
   - Definitive S-1 finding: Starlink launch costs are *capitalized into Connectivity* and depreciated
     (not hidden in Space) — reported margin already bears launch.
   - The moat = the internal-vs-market launch *price spread* (~$5.2B FY2025 advantage); standalone
     Starlink would be loss-making at market launch prices.
   - Cost-of-revenue decomposition (~40% is constellation depreciation).
   - **FCF = cash from operations − capex**, where segment CFO = operating income + non-cash charges
     (D&A + SBC + impairment), ΔWC excluded (conservative — Starlink subs are prepaid). FCF traces a
     J-curve: −$0.9B (2023) → +$0.4B (2024) → +$3.0B (2025). Segment D&A/SBC/capex tie to the
     consolidated cash-flow statement.
   - Opportunity cost of Starlink-dedicated rockets ≈ $0 (backfills idle capacity).

**EBITDA policy:** EBITDA is shown **only for comparison** — never used in a calculation. For SpaceX it
is misleading: the depreciation it removes is real asset consumption (boosters retire at end-of-life;
satellites deorbit and burn up), and that hardware must be rebuilt with cash. FY2025 GAAP EBITDA ~$6.8B
vs FCF ~$3.0B — EBITDA overstates cash ~2×. Valuation uses FCF.

## Next
- Space and AI segment write-ups, ARPU/subscriber growth model, then the segment-level DCF.
