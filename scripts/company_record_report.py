"""Outputs and the command line for company_record.py (the equities pack): guidance.csv, events.csv, concentration.csv,
retrieval_log.csv and RECORD.md in the output folder, each number with its source. Standard library only.

    py -3 company_record_report.py                  # smoke test: writes the fixture's record to a temp folder
    py -3 company_record.py --fixture <json> --out <dir>
    py -3 company_record.py --ticker TSM --ua "Name email@example.com" --prices closes.csv [--benchmark SPY] [--ir urls.txt]
        [--consensus consensus.csv] [--quarters 24] [--fy-end-month 12] --out <dir>
"""
from __future__ import annotations

import argparse, csv, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from company_record import build  # noqa: E402
from company_sources import EdgarSource, FixtureSource, load_fixture  # noqa: E402
from edgar import Edgar  # noqa: E402


def _g(v, fmt: str) -> str:
    """Blank for a missing value; money in millions when large (fmt 'money'); else the format given."""
    if v == "" or v is None:
        return ""
    if fmt == "money":
        return f"{v / 1e6:,.0f}M" if abs(v) >= 1e6 else f"{v:,.2f}"
    return format(v, fmt)


def write(rec: dict, out: str) -> None:
    os.makedirs(out, exist_ok=True)
    for name, rows in (("guidance", rec["guidance"]), ("events", rec["events"]), ("concentration", rec["concentration"]), ("retrieval_log", rec["log"])):
        with open(os.path.join(out, name + ".csv"), "w", newline="", encoding="utf-8") as fh:
            if rows:
                w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r})); w.writeheader(); w.writerows(rows)
    g = [x for x in rec["guidance"] if x["delivered"] != ""]; ev = [e for e in rec["events"] if e["move_1d"] != ""]
    L = [f"# Company record — {rec['company']['name']} ({rec['company']['ticker']}), measured (computed) by company_record.py; benchmark {rec.get('benchmark') or 'none'}", ""]
    L.append(f"Guidance rows {len(rec['guidance'])}, delivered {len(g)}: inside the range {sum(1 for x in g if x['inside'])} of {len(g)}; mean miss against the midpoint "
             f"{statistics.fmean(x['miss_pct'] for x in g if x['miss_pct'] != ''):+.1f}% (n={len(g)}{'; estimated, n under 30' if len(g) < 30 else ''})" if g else "Guidance: none delivered yet")
    L += ["", "| given | item | target | guided low–high (mid) | delivered | inside | miss % | source |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {x['given']} | {x['item']} | {x['target']} ({x['target_kind']}) | {_g(x['low'], 'money')}–{_g(x['high'], 'money')} ({_g(x['mid'], 'money')}) {x['unit']} | "
          f"{_g(x['delivered'], 'money')} | {x['inside']} | {_g(x['miss_pct'], '+.1f')} | {x['source']} |" for x in rec["guidance"]]
    if ev:
        judged = [e for e in ev if e["vs"] != "none"]
        L += ["", f"Events {len(ev)} with moves: mean |1-day| {statistics.fmean(abs(e['move_1d']) for e in ev):.1%}, median 1-day {statistics.median(e['move_1d'] for e in ev):+.1%}; "
              f"beats (above the midpoint, or consensus) {sum(1 for e in judged if e['vs'].startswith(('above', 'inside, above', 'beat')))} of {len(judged)} judged"
              f"{'; estimated, n under 30' if len(ev) < 30 else ''}"]
    L += ["", "| release | after close | reported | revenue | guided mid | vs guidance | eps | 1d | 21d | bench 1d | bench 21d |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    L += [f"| {e['release']} | {e['after_close']} | {e['reported']} | {_g(e['revenue'], 'money')} | {_g(e['guided_mid'], 'money')} | {e['vs']} | {_g(e['eps'], '.2f')} | {_g(e['move_1d'], '+.1%')} | "
          f"{_g(e['move_21d'], '+.1%')} | {_g(e.get('bench_move_1d', ''), '+.1%')} | {_g(e.get('bench_move_21d', ''), '+.1%')} |" for e in rec["events"]]
    L += ["", "Customer concentration (verbatim; the lead reads):"] + [f"- FY{c['fiscal_year']}: {c['text']} [{c['source']}]" for c in rec["concentration"]]
    L += ["", "Guidance targets marked inferred were not named in the sentence; every number that crosses a flip threshold goes through the two-reader rule before use."]
    with open(os.path.join(out, "RECORD.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixture"); ap.add_argument("--ticker"); ap.add_argument("--cik", type=int); ap.add_argument("--ua", default=""); ap.add_argument("--prices")
    ap.add_argument("--benchmark", default="SPY"); ap.add_argument("--ir"); ap.add_argument("--consensus"); ap.add_argument("--quarters", type=int, default=24)
    ap.add_argument("--fy-end-month", type=int, default=12); ap.add_argument("--out", default="company_record_out")
    a = ap.parse_args(argv)
    if not (a.fixture or a.ticker or a.cik):
        ap.error("give --fixture, or --ticker/--cik with --ua and --prices")
    cons = {}
    if a.consensus:
        with open(a.consensus, newline="", encoding="utf-8") as fh:
            cons = {(r["quarter"], r["item"]): float(r["value"]) for r in csv.DictReader(fh)}
    if a.fixture:
        fx = load_fixture(a.fixture)
        rec = build(FixtureSource(fx), fx["company"], a.benchmark if a.benchmark in fx["price_runs"] else "", a.quarters, fx["company"].get("fy_end_month", 12), cons)
    else:
        if not a.prices:
            ap.error("--prices closes.csv is needed for the moves")
        e = Edgar(a.ua); cik = a.cik or e.cik_for(a.ticker); src = EdgarSource(cik, a.ua, a.prices)
        ir = []
        if a.ir:
            with open(a.ir, encoding="utf-8") as fh:
                ir = [tuple(l.rstrip("\n").split("\t")[:2]) for l in fh if l.strip()]
        rec = build(src, {"cik": cik, "ticker": a.ticker or str(cik), "name": src.submissions().get("name", "")}, a.benchmark, a.quarters, a.fy_end_month, cons, ir)
    write(rec, a.out)
    print(f"wrote {a.out}: {len(rec['guidance'])} guidance rows, {len(rec['events'])} events, {len(rec['concentration'])} concentration rows, {len(rec['log'])} retrievals logged")
    return 0


def _smoke() -> None:
    import tempfile
    fx = load_fixture(); out = os.path.join(tempfile.gettempdir(), "company_record_smoke")
    rec = build(FixtureSource(fx), fx["company"], fx.get("benchmark", "")); write(rec, out)
    md = open(os.path.join(out, "RECORD.md"), encoding="utf-8").read()
    assert "inside the range" in md and "| 2026-01-22 | True | 2025Q4 |" in md and "Customer A" in md and os.path.exists(os.path.join(out, "events.csv"))
    assert main(["--fixture", fx and __import__("company_sources").FIXTURE, "--out", out]) == 0
    print(f"company_record_report smoke test: ok (RECORD.md and the four CSVs written to {out}; the command line runs on the fixture)")


if __name__ == "__main__":
    _smoke()
