"""Fiscal quarters and first-reported quarterly values from EDGAR company facts (XBRL), for company_record.py. Standard
library only. A fiscal year ends in month `fem` (12 unless the filer says otherwise); quarter labels read 2026Q1.

    py -3 xbrl_quarters.py                         # smoke test
    from xbrl_quarters import CONCEPTS, q_end, quarter_of, lab, quarterly, actual

quarterly() keeps, for each (start, end) period, the earliest filing's value (as first reported, the point-in-time rule),
takes periods of 80 to 100 days as quarters, and derives the last quarter of a year-to-date or full-year value by
subtracting the earlier quarters already known (marked derived); us-gaap and ifrs-full concept names are both tried.
"""
from __future__ import annotations

import statistics
from datetime import date, timedelta
from typing import Dict, Tuple

CONCEPTS = {"revenue": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenue"),
            "gross_profit": ("GrossProfit",), "operating_income": ("OperatingIncomeLoss", "ProfitLossFromOperatingActivities"),
            "eps": ("EarningsPerShareDiluted", "DilutedEarningsLossPerShare"),
            "capex": ("PaymentsToAcquirePropertyPlantAndEquipment", "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities")}


def q_end(Y: int, q: int, fem: int = 12) -> date:
    m, y = fem - 3 * (4 - q), Y
    if m <= 0:
        m, y = m + 12, y - 1
    return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def quarter_of(d: date, fem: int = 12) -> Tuple[int, int]:
    """The fiscal (year, quarter) whose end is the latest quarter end on or before d."""
    for Y in (d.year + 1, d.year, d.year - 1):
        for q in (4, 3, 2, 1):
            if q_end(Y, q, fem) <= d:
                return Y, q
    raise ValueError(d)


def lab(Y: int, q: int) -> str:
    return f"{Y}Q{q}"


def quarterly(facts: dict, item: str, fem: int = 12) -> Dict[str, dict]:
    rows: list = []
    for tax in facts.get("facts", {}).values():
        for n in CONCEPTS[item]:
            if n in tax:
                rows = next(iter(tax[n]["units"].values())); break
        if rows:
            break
    best: Dict[tuple, dict] = {}
    for e in rows:
        if "start" in e and ((e["start"], e["end"]) not in best or e["filed"] < best[(e["start"], e["end"])]["filed"]):
            best[(e["start"], e["end"])] = e
    per, ytd = {}, {}
    for (s, en), e in sorted(best.items(), key=lambda kv: kv[0][1]):
        d1 = date.fromisoformat(en); days = (d1 - date.fromisoformat(s)).days; Y, q = quarter_of(d1, fem)
        if 80 <= days <= 100:
            per[(Y, q)] = dict(value=e["val"], filed=e["filed"], accn=e["accn"], derived="")
        elif days > 100:
            ytd.setdefault((Y, q), e)
    for (Y, q), e in sorted(ytd.items()):
        earlier = [per[(Y, j)]["value"] for j in range(1, q) if (Y, j) in per]
        if (Y, q) not in per and len(earlier) == q - 1:
            per[(Y, q)] = dict(value=e["val"] - sum(earlier), filed=e["filed"], accn=e["accn"], derived="year-to-date minus earlier quarters")
    return {lab(Y, q): dict(r, quarter=lab(Y, q), end=q_end(Y, q, fem).isoformat()) for (Y, q), r in sorted(per.items())}


def actual(fq: Dict[str, Dict[str, dict]], item: str, target: str):
    """The delivered value for a quarter label or FYyyyy: sums for flows, the quarters' mean for margins; None when unknown."""
    one = lambda i, t: (None if fq[i].get(t) is None else float(fq[i][t]["value"]))
    if target.startswith("FY"):
        vals = [actual(fq, item, f"{target[2:]}Q{q}") for q in (1, 2, 3, 4)]
        return None if any(v is None for v in vals) else (statistics.fmean(vals) if item.endswith("margin") else sum(vals))
    if item.endswith("margin"):
        num, den = one("gross_profit" if item == "gross_margin" else "operating_income", target), one("revenue", target)
        return None if num is None or not den else 100 * num / den
    return one(item, target)


def _smoke() -> None:
    assert q_end(2026, 1) == date(2026, 3, 31) and q_end(2026, 4) == date(2026, 12, 31) and q_end(2026, 4, 6) == date(2026, 6, 30) and q_end(2026, 1, 6) == date(2025, 9, 30)
    assert quarter_of(date(2026, 10, 16)) == (2026, 3) and quarter_of(date(2026, 12, 31)) == (2026, 4) and quarter_of(date(2026, 8, 1), 6) == (2026, 4)
    f = lambda s, e, v, filed: {"start": s, "end": e, "val": v, "filed": filed, "accn": "a"}
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [f("2025-01-01", "2025-03-31", 10, "2025-05-01"), f("2025-01-01", "2025-03-31", 11, "2026-02-01"),
                                                                 f("2025-04-01", "2025-06-30", 12, "2025-08-01"), f("2025-07-01", "2025-09-30", 13, "2025-11-01"),
                                                                 f("2025-01-01", "2025-12-31", 50, "2026-02-20")]}},
                                   "GrossProfit": {"units": {"USD": [f("2025-04-01", "2025-06-30", 6, "2025-08-01")]}}},
                       "ifrs-full": {"Revenue": {"units": {"TWD": [f("2026-01-01", "2026-03-31", 99, "2026-05-01")]}}}}}
    q = quarterly(facts, "revenue"); assert q["2025Q1"]["value"] == 10, "the first-reported value wins over the later restatement"
    assert q["2025Q4"]["value"] == 15 and q["2025Q4"]["derived"] and q["2025Q4"]["end"] == "2025-12-31" and "2026Q1" not in q, "us-gaap found first; ifrs-full only when us-gaap lacks the concept"
    fq = {"revenue": q, "gross_profit": quarterly(facts, "gross_profit"), "operating_income": {}}
    assert actual(fq, "revenue", "FY2025") == 50 and actual(fq, "gross_margin", "2025Q2") == 50.0 and actual(fq, "gross_margin", "2025Q3") is None and actual(fq, "revenue", "FY2026") is None
    print("xbrl_quarters smoke test: ok (fiscal quarter ends, first-reported values, derived Q4, taxonomy fallback, delivered lookups)")


if __name__ == "__main__":
    _smoke()
