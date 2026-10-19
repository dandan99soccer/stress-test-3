"""Per-company record for the equities pack (references/packs/equities-b.md section 4): (a) guidance given against delivered
by line item, by quarter; (b) beat or miss against the company's own guidance midpoint (or a supplied consensus) with the
one-day and 21-day moves from a price panel, keyed by the release's acceptance time (after 16:00 ET maps to the next
session); (c) customer concentration from the annual filing. Standard library only. Fiscal quarters and the XBRL facts are
in xbrl_quarters.py; the sources (the saved fixture, or EDGAR through edgar.py) in company_sources.py; the CSV and markdown
outputs and the command line in company_record_report.py, which this file hands off to. The smoke test runs offline on the
fixture and never fetches.

    py -3 company_record.py                                        # offline smoke test on scripts/fixtures/company_record_fixture.json
    py -3 company_record.py --fixture <json> --out <dir>
    py -3 company_record.py --ticker TSM | --cik 1046179  --ua "Name email@example.com" --prices closes.csv [--benchmark SPY]
        [--ir urls.txt] [--consensus consensus.csv] [--quarters 24] [--fy-end-month 12] --out <dir>

A guidance target is "stated" when the sentence names the quarter or year, else "inferred" (the next quarter, or the fiscal
year when the sentence says so); sentences are kept verbatim, every number carries its accession or URL, and a number that
crosses a flip threshold goes through the two-reader rule before use. Fiscal quarters are calendar unless --fy-end-month says
otherwise. --ir lines are "url<TAB>YYYY-MM-DD" (the page's date). Consensus CSV columns: quarter,item,value.
"""
from __future__ import annotations

import os, re, sys
from datetime import date, timedelta
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edgar import recent_filings  # noqa: E402
from xbrl_quarters import CONCEPTS, actual, lab, quarter_of, quarterly  # noqa: E402

ITEMS = {"revenue": r"\b(?:net )?(?:revenues?|net sales)\b", "gross_margin": r"\bgross margins?\b", "operating_margin": r"\boperating margins?\b",
         "eps": r"\b(?:diluted )?(?:EPS|earnings per (?:diluted )?share)\b", "capex": r"\bcapital expenditures?\b|\bcapex\b"}
GUIDE = re.compile(r"\b(expects?|expected|anticipates?|guidance|outlook|forecasts?|projects?|in the range of)\b", re.I)
NUMBER = re.compile(r"\$?\s?(\d+(?:\.\d+)?)\s*(billion|million|%|percent)?", re.I)
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
SENT = re.compile(r"(?<=[.!?])\s+")


# ---------- guidance ----------
def _num(m) -> Tuple[float, str]:
    v, u = float(m.group(1)), (m.group(2) or "").lower()
    return (v * 1e9, "USD") if u == "billion" else (v * 1e6, "USD") if u == "million" else (v, "%") if u in ("%", "percent") else (v, "USD")


def target_of(s: str, reported: Tuple[int, int], fem: int) -> Tuple[str, str]:
    """The quarter or fiscal year a guidance sentence is for, and whether it was stated or inferred."""
    Y, q = reported
    m = re.search(r"\b(first|second|third|fourth|1st|2nd|3rd|4th)[\s-]*(?:fiscal\s+)?quarter(?:\s+of)?(?:\s+fiscal)?(?:\s+year)?\s*(20\d\d)?", s, re.I)
    if m:
        qq = ORD[m.group(1).lower()]; return lab(int(m.group(2)) if m.group(2) else (Y if qq > q else Y + 1), qq), "stated"
    m = re.search(r"\bQ([1-4])\s*(?:FY|fiscal)?\s*'?(20\d\d|\d\d)?\b", s)
    if m:
        qq, yy = int(m.group(1)), m.group(2)
        return lab(int(yy) + (2000 if len(yy) == 2 else 0) if yy else (Y if qq > q else Y + 1), qq), "stated"
    m = re.search(r"\b(?:full[- ]year|fiscal(?: year)?|FY)\s*'?(20\d\d|\d\d)\b", s, re.I)
    if m:
        yy = m.group(1); return f"FY{int(yy) + (2000 if len(yy) == 2 else 0)}", "stated"
    if re.search(r"full[- ]year|fiscal year|\bFY\b|\bthe year\b", s, re.I):
        return f"FY{Y}", "inferred"
    return lab(Y + (q == 4), q % 4 + 1), "inferred"


def guidance_from_text(text: str, given: str, reported: Tuple[int, int], fem: int = 12, source: str = "") -> List[dict]:
    """Guidance sentences by pattern: a guide word, a line item, then the first one or two numbers of the item's unit after it."""
    out = []
    for s in SENT.split(text):
        if not GUIDE.search(s):
            continue
        for item, pat in ITEMS.items():
            mm = re.search(pat, s, re.I)
            if not mm:
                continue
            nums = [_num(m) for m in NUMBER.finditer(s[mm.end():])]
            nums = ([n for n in nums if n[1] == "%"] if item.endswith("margin") else [n for n in nums if n[1] == "USD" and n[0] < 1000] if item == "eps"
                    else [n for n in nums if n[1] == "USD" and n[0] >= 1e6])
            if not nums:
                continue
            lo, hi = sorted((nums[0][0], nums[1][0] if len(nums) > 1 else nums[0][0])); tgt, kind = target_of(s, reported, fem)
            out.append(dict(given=given, item=item, target=tgt, target_kind=kind, low=lo, high=hi, mid=(lo + hi) / 2, unit=nums[0][1], text=s.strip(), source=source))
    return out


def reported_quarter(text: str, release: date, fem: int) -> Tuple[int, int]:
    m = re.search(r"\b(first|second|third|fourth)\s+quarter(?:\s+and\s+full\s+year)?(?:\s+of)?(?:\s+fiscal)?\s*(20\d\d)", text[:400], re.I)
    return (int(m.group(2)), ORD[m.group(1).lower()]) if m else quarter_of(release - timedelta(days=14), fem)


def delivered(g: dict, fq) -> dict:
    a = actual(fq, g["item"], g["target"])
    if a is None:
        return dict(delivered="", inside="", miss_pct="")
    return dict(delivered=a, inside=(g["low"] <= a <= g["high"]), miss_pct=(100 * (a - g["mid"]) / g["mid"] if g["mid"] else ""))


# ---------- events, moves, verdicts, concentration ----------
def moves(series: List[Tuple[str, float]], release: str, after_close: bool) -> dict:
    """One-day and 21-day moves from the close before the reaction day (the next session after an after-close release)."""
    i = next((k for k, (d, _) in enumerate(series) if (d > release if after_close else d >= release)), None)
    if i is None or i == 0:
        return dict(reaction_day="", move_1d="", move_21d="")
    p0 = series[i - 1][1]
    return dict(reaction_day=series[i][0], move_1d=series[i][1] / p0 - 1, move_21d=(series[i + 20][1] / p0 - 1) if i + 20 < len(series) else "")


def verdict(ev: dict, guidance: List[dict], fq, consensus: Dict[Tuple[str, str], float]) -> dict:
    a, e = actual(fq, "revenue", ev["reported"]), actual(fq, "eps", ev["reported"])
    out = dict(revenue=a if a is not None else "", eps=e if e is not None else "", guided_mid="", vs="none")
    if a is None:
        return out
    if (ev["reported"], "revenue") in consensus:
        c = consensus[(ev["reported"], "revenue")]; return dict(out, guided_mid=c, vs=("beat consensus" if a > c else "miss consensus"))
    g = next((g for g in guidance if g["item"] == "revenue" and g["target"] == ev["reported"] and g["given"] < ev["release"]), None)
    if g:
        out.update(guided_mid=g["mid"], vs=("above range" if a > g["high"] else "below range" if a < g["low"] else "inside, above mid" if a >= g["mid"] else "inside, below mid"))
    return out


def concentration(text: str, source: str, fy: int) -> List[dict]:
    """Sentences naming customers with a percentage of revenue, verbatim, with the percentages pulled out."""
    out = []
    for s in SENT.split(text):
        if re.search(r"\bcustomers?\b", s, re.I) and re.search(r"\d+(?:\.\d+)?\s?%", s) and re.search(r"accounted for|represented|of (?:our |total |net |consolidated )*(?:net )?(?:revenues?|sales)", s, re.I):
            out.append(dict(fiscal_year=fy, percents=[float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s?%", s)], text=s.strip(), source=source))
    return out


def build(src, company: dict, bench: str = "", quarters: int = 24, fem: int = 12, consensus=None, ir_pages=()) -> dict:
    """The record from a source: guidance rows with delivered, events with moves and verdicts, concentration, the quarterly facts, the log."""
    filings = recent_filings(src.submissions()); facts = src.companyfacts(); fq = {i: quarterly(facts, i, fem) for i in CONCEPTS}
    prices, t, consensus = src.prices(), company["ticker"], (consensus or {})
    rels = sorted([f for f in filings if (f["form"].startswith("8-K") and "2.02" in (f.get("items") or "")) or f["form"] == "6-K"],
                  key=lambda f: f["filingDate"], reverse=True)[:quarters]
    guidance, evs = [], []
    for f in rels:
        text, sid = src.release_text(f)
        if not text or (f["form"] == "6-K" and not re.search(r"(?is)quarter.{0,400}revenue", text)):
            continue
        rep = reported_quarter(text, date.fromisoformat(f["filingDate"]), fem); after = int((f.get("acceptanceDateTime") or "T12")[11:13]) >= 16
        guidance += guidance_from_text(text, f["filingDate"], rep, fem, sid)
        mv = moves(prices.get(t, []), f["filingDate"], after); bm = moves(prices.get(bench, []), f["filingDate"], after) if bench else {}
        evs.append(dict(release=f["filingDate"], after_close=after, reported=lab(*rep), accn=f["accessionNumber"], **mv,
                        **{f"bench_{k}": v for k, v in bm.items() if k != "reaction_day"}))
    for url, d in ir_pages:
        guidance += guidance_from_text(src.page(url), d, quarter_of(date.fromisoformat(d) - timedelta(days=14), fem), fem, url)
    for g in guidance:
        g.update(delivered(g, fq))
    for ev in evs:
        ev.update(verdict(ev, guidance, fq, consensus))
    conc = []
    for f in filings:
        if f["form"] in ("10-K", "10-K/A", "20-F"):
            text, sid = src.annual_text(f); conc += concentration(text, sid, int(f["filingDate"][:4]) - 1)
    return dict(company=company, benchmark=bench, guidance=sorted(guidance, key=lambda g: (g["given"], g["item"])), events=sorted(evs, key=lambda e: e["release"]),
                concentration=conc, quarters={i: list(v.values()) for i, v in fq.items()}, log=src.log)


def _smoke() -> None:
    from company_sources import FixtureSource, load_fixture
    fx = load_fixture(); rec = build(FixtureSource(fx), fx["company"], fx.get("benchmark", ""), fem=fx["company"].get("fy_end_month", 12))
    by = {r["quarter"]: r for r in rec["quarters"]["revenue"]}; assert abs(by["2025Q4"]["value"] - 2.08e9) < 1 and by["2025Q4"]["derived"]
    cx = {r["quarter"]: r for r in rec["quarters"]["capex"]}; assert abs(cx["2026Q2"]["value"] - 0.41e9) < 1 and "2025Q4" not in cx, "capex quarters from year-to-date differences"
    g = {(x["given"], x["item"]): x for x in rec["guidance"]}
    r1 = g[("2026-01-22", "revenue")]; assert r1["target"] == "2026Q1" and r1["target_kind"] == "stated" and (r1["low"], r1["high"]) == (2.0e9, 2.1e9)
    assert r1["delivered"] == 2.12e9 and r1["inside"] is False and abs(r1["miss_pct"] - 100 * (2.12 - 2.05) / 2.05) < 1e-9
    gm = g[("2026-04-23", "gross_margin")]; assert gm["target"] == "2026Q2" and (gm["low"], gm["high"]) == (56.0, 58.0) and abs(gm["delivered"] - 57.0) < 1e-9 and gm["inside"]
    assert g[("2026-01-22", "eps")]["delivered"] == 1.35 and g[("2026-01-22", "capex")]["target"] == "FY2026" and g[("2026-01-22", "capex")]["delivered"] == ""
    assert target_of("Q3 FY26 revenue is expected to be $1 billion", (2026, 2), 12) == ("2026Q3", "stated") and target_of("we expect revenue to grow", (2026, 4), 12) == ("2027Q1", "inferred")
    ev = {e["release"]: e for e in rec["events"]}; assert len(ev) == 4
    assert ev["2026-01-22"]["after_close"] and ev["2026-01-22"]["reaction_day"] == "2026-01-23" and not ev["2026-07-23"]["after_close"] and ev["2026-07-23"]["reaction_day"] == "2026-07-23"
    assert ev["2026-04-23"]["vs"] == "above range" and ev["2026-07-23"]["vs"] == "below range" and ev["2025-10-23"]["vs"] == "none"
    assert ev["2026-04-23"]["move_1d"] > 0.04 and ev["2026-07-23"]["move_1d"] < -0.04 and ev["2026-04-23"]["move_21d"] != "" and ev["2026-04-23"]["bench_move_1d"] != ""
    assert len(rec["concentration"]) == 3 and 24.0 in rec["concentration"][0]["percents"] and rec["concentration"][0]["fiscal_year"] == 2025
    rec2 = build(FixtureSource(fx), fx["company"], consensus={("2026Q2", "revenue"): 2.25e9}); assert {e["release"]: e for e in rec2["events"]}["2026-07-23"]["vs"] == "miss consensus"
    print("company_record smoke test: ok (derived quarters, guidance targets and delivered, after-close mapping, verdicts, moves, concentration, consensus)")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        _smoke()
    else:
        from company_record_report import main
        raise SystemExit(main())
