"""Sources for company_record.py: the saved fixture (offline) and EDGAR through edgar.py (live, optional). Each source gives
submissions(), companyfacts(), prices() as {ticker: [(date, close), ...]}, release_text(filing) and annual_text(filing) as
(text, source id), and a retrieval log. Standard library only.

    py -3 company_sources.py                        # offline smoke test on the fixture
    from company_sources import FIXTURE, FixtureSource, EdgarSource, read_prices
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, timedelta
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edgar import Edgar, exhibit_url, html_to_text  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "company_record_fixture.json")


def read_prices(path: str) -> Dict[str, List[Tuple[str, float]]]:
    """A closes CSV (Date plus one column per instrument) as {ticker: [(date, close)]}, blanks skipped."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    dcol = next(k for k in rows[0] if k.lower() == "date")
    return {k: [(r[dcol], float(r[k])) for r in rows if r.get(k) not in ("", None)] for k in rows[0] if k != dcol}


def load_fixture(path: str = FIXTURE) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class FixtureSource:
    """The fixture holds submissions, companyfacts, documents keyed "accession/name" (HTML), and price runs: for each
    ticker, [start date, [closes on consecutive weekdays]]."""

    def __init__(self, fx: dict):
        self.fx, self.log = fx, []

    def submissions(self) -> dict:
        return self.fx["submissions"]

    def companyfacts(self) -> dict:
        return self.fx["companyfacts"]

    def prices(self) -> Dict[str, List[Tuple[str, float]]]:
        out: Dict[str, list] = {}
        for t, runs in self.fx["price_runs"].items():
            for start, xs in runs:
                d = date.fromisoformat(start)
                for x in xs:
                    while d.weekday() > 4:
                        d += timedelta(days=1)
                    out.setdefault(t, []).append((d.isoformat(), float(x))); d += timedelta(days=1)
        return {t: sorted(v) for t, v in out.items()}

    def text(self, f: dict) -> Tuple[str, str]:
        k = next((k for k in self.fx["documents"] if k.startswith(f["accessionNumber"] + "/")), None)
        self.log.append({"url": k or "", "status": 200 if k else 404, "bytes": len(self.fx["documents"].get(k, "")), "retrieved": "fixture"})
        return (html_to_text(self.fx["documents"][k]), k) if k else ("", "")

    release_text = annual_text = text


class EdgarSource:
    """Live: ten requests a second at most, the user agent declared; the press-release exhibit (EX-99.1) of each 8-K or 6-K,
    the primary document of each 10-K or 20-F; every fetch logged with its URL, size and time."""

    def __init__(self, cik: int, ua: str, prices_csv: str):
        self.e, self.cik, self.csv = Edgar(ua), int(cik), prices_csv
        self.log = self.e.log

    def submissions(self) -> dict:
        return self.e.submissions(self.cik)

    def companyfacts(self) -> dict:
        return self.e.companyfacts(self.cik)

    def prices(self) -> Dict[str, List[Tuple[str, float]]]:
        return read_prices(self.csv)

    def page(self, url: str) -> str:
        return html_to_text(self.e.get(url))

    def release_text(self, f: dict) -> Tuple[str, str]:
        urls = self.e.filing_index(self.cik, f["accessionNumber"])
        u = exhibit_url(urls) or next((x for x in urls if x.endswith(f["primaryDocument"])), None)
        return (html_to_text(self.e.get(u)), u) if u else ("", "")

    def annual_text(self, f: dict) -> Tuple[str, str]:
        return html_to_text(self.e.document(self.cik, f["accessionNumber"], f["primaryDocument"])), f["accessionNumber"] + "/" + f["primaryDocument"]


def _smoke() -> None:
    fx = load_fixture(); s = FixtureSource(fx); p = s.prices()
    assert set(p) >= {"XMPL", "SPY"} and all(date.fromisoformat(d).weekday() < 5 for d, _ in p["XMPL"]), "price runs expand onto weekdays only"
    assert p["XMPL"] == sorted(p["XMPL"]) and len(p["XMPL"]) == 100
    f = {"accessionNumber": fx["submissions"]["filings"]["recent"]["accessionNumber"][0]}
    text, sid = s.release_text(f); assert "expects revenue" in text and sid.endswith("ex99-1.htm") and s.log[-1]["status"] == 200
    assert s.text({"accessionNumber": "none"}) == ("", "") and s.log[-1]["status"] == 404
    try:
        EdgarSource(1, "no-email", ""); raise AssertionError("a live source without a declared user agent must be refused")
    except ValueError:
        pass
    print("company_sources smoke test: ok (fixture prices, documents, log; live source refuses an undeclared user agent; no network)")


if __name__ == "__main__":
    _smoke()
