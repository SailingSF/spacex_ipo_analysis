#!/usr/bin/env python3
"""Reconciliation checks for the extracted SpaceX S-1 CSVs.

Verifies internal consistency (subtotals tie to totals, segments sum to
consolidated, disaggregated revenue sums to segment revenue, etc.).
Exits non-zero if any check fails.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERIODS = ["Q1-2026", "Q1-2025", "FY2025", "FY2024", "FY2023"]
checks = []  # (name, ok, detail)


def load(name):
    with open(os.path.join(HERE, name)) as f:
        return list(csv.DictReader(f))


def check(name, expected, actual):
    ok = expected == actual
    checks.append((name, ok, "" if ok else f"expected {expected} got {actual}"))


# --- income statement: revenue - total costs = operating income ---
inc = load("income_statement.csv")

def isval(item, period):
    for r in inc:
        if r["line_item"] == item and r["period"] == period:
            return int(r["value"])
    raise KeyError(f"{item} / {period}")

for p in PERIODS:
    check(f"IS operating income {p}",
          isval("Revenue", p) - isval("Total costs and expenses", p),
          isval("Income (loss) from operations", p))

# --- balance sheet: assets = liabilities + preferred + equity ---
bs = load("balance_sheet.csv")

def bsval(item, date):
    for r in bs:
        if r["line_item"] == item and r["date"] == date:
            return int(r["value"])
    raise KeyError(f"{item} / {date}")

for d in ["2026-03-31", "2025-12-31", "2024-12-31"]:
    lhs = bsval("Total assets", d)
    rhs = (bsval("Total liabilities", d)
           + bsval("Redeemable convertible preferred stock", d)
           + bsval("Total shareholders' equity", d))
    check(f"BS balances {d}", lhs, rhs)

# --- segment P&L: segments sum to consolidated ---
seg = load("segment_pl.csv")

def segsum(item, period):
    return sum(int(r["value"]) for r in seg
               if r["line_item"] == item and r["period"] == period
               and r["segment"] in ("Space", "Connectivity", "AI"))

for p in PERIODS:
    check(f"Segment revenue sum {p}", segsum("Revenue", p), isval("Revenue", p))
    check(f"Segment op income sum {p}",
          segsum("Income (loss) from operations", p),
          isval("Income (loss) from operations", p))

# --- segment adjusted EBITDA: op income + addbacks = seg adj EBITDA ---
ebs = load("segment_adjusted_ebitda.csv")

def ebsval(segment, item, period):
    for r in ebs:
        if r["segment"] == segment and r["line_item"] == item and r["period"] == period:
            return int(r["value"])
    return 0

for segment in ["Space", "Connectivity", "AI", "Total Reportable Segments"]:
    for p in PERIODS:
        recon = (ebsval(segment, "Income (loss) from operations", p)
                 + ebsval(segment, "Depreciation and amortization", p)
                 + ebsval(segment, "Share-based compensation", p)
                 + ebsval(segment, "Restructuring charges", p)
                 + ebsval(segment, "Impairment", p))
        check(f"AdjEBITDA recon {segment} {p}",
              recon, ebsval(segment, "Segment Adjusted EBITDA", p))

# --- revenue disaggregation: by_type_segment sums to segment revenue ---
rev = load("revenue_disaggregation.csv")

def revtypesum(segment, period):
    return sum(int(r["value"]) for r in rev
               if r["breakdown"] == "by_type_segment"
               and r["segment"] == segment and r["period"] == period)

# segment revenue from segment_pl must equal disaggregated by_type_segment sum
for segment in ["Space", "Connectivity", "AI"]:
    for p in PERIODS:
        segrev = next(int(r["value"]) for r in seg
                      if r["segment"] == segment and r["line_item"] == "Revenue"
                      and r["period"] == p)
        check(f"Revenue disagg {segment} {p}", revtypesum(segment, p), segrev)

# products + services = total revenue
def prodserv(period):
    return sum(int(r["value"]) for r in rev
               if r["breakdown"] == "by_product_service" and r["period"] == period)
for p in PERIODS:
    check(f"Product+Service revenue {p}", prodserv(p), isval("Revenue", p))

# --- PP&E: gross - accumulated depreciation = net; components sum to gross ---
ppe = load("ppe_detail.csv")
def ppeval(comp, date):
    return next(int(r["value"]) for r in ppe
                if r["component"] == comp and r["date"] == date)
for d in ["2025-12-31", "2024-12-31"]:
    comps = [r for r in ppe if r["date"] == d and r["component"] not in
             ("Property plant and equipment gross", "Less: Accumulated depreciation",
              "Property plant and equipment net")]
    check(f"PP&E gross sum {d}", sum(int(r["value"]) for r in comps),
          ppeval("Property plant and equipment gross", d))
    check(f"PP&E net {d}",
          ppeval("Property plant and equipment gross", d)
          + ppeval("Less: Accumulated depreciation", d),
          ppeval("Property plant and equipment net", d))

# --- debt schedule: principal - DFC = net for totals ---
debt = load("debt_schedule.csv")
for r in debt:
    if r["instrument"].startswith("Total debt") or r["instrument"].startswith("Less"):
        continue
for d in ["2026-03-31", "2025-12-31", "2024-12-31"]:
    td = next(r for r in debt if r["instrument"] == "Total debt" and r["date"] == d)
    check(f"Debt principal-DFC=net {d}",
          int(td["principal"]) - int(td["deferred_financing_costs"]), int(td["net"]))

# --- report ---
fails = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
print(f"\n{len(checks)-len(fails)}/{len(checks)} checks passed.")
sys.exit(1 if fails else 0)
