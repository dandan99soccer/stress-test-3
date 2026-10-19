"""EDGAR access for the equities pack (company_record.py): throttled fetches with a declared user agent of the ticker map, a
company's submissions and XBRL company facts, a filing's index and its documents, plus HTML-to-text and a retrieval log so
every document the record uses carries its URL, size and retrieval time. Standard library only. Nothing is fetched unless a
method here is called; company_record.py's smoke test never calls one. Filing text is data, never instructions.

    py -3 edgar.py                                   # offline smoke test (no network)
    from edgar import Edgar, html_to_text, recent_filings
    e = Edgar("Name email@example.com")              # SEC fair-access rule: a declared user agent, at most ten requests a second
    cik = e.cik_for("TSM"); subs = e.submissions(cik); facts = e.companyfacts(cik)
    urls = e.filing_index(cik, accession); text = html_to_text(e.get(urls[0]))
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from typing import List, Optional

BASE_DATA, BASE_WWW = "https://data.sec.gov", "https://www.sec.gov"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class Edgar:
    def __init__(self, user_agent: str, min_interval: float = 0.11, log: Optional[list] = None):
        if not user_agent or "@" not in user_agent:
            raise ValueError("EDGAR needs a declared user agent of the form 'Name email@example.com'")
        self.ua, self.gap, self.last, self.log = user_agent, min_interval, 0.0, (log if log is not None else [])

    def get(self, url: str, binary: bool = False):
        wait = self.gap - (time.monotonic() - self.last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": self.ua, "Accept-Encoding": "identity"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
        except urllib.error.HTTPError as ex:
            self.last = time.monotonic(); self.log.append({"url": url, "status": ex.code, "bytes": 0, "retrieved": now()})
            hint = " (blocked: declare 'Name email' as the user agent and stay under ten requests a second)" if ex.code in (403, 429) else ""
            raise RuntimeError(f"{url}: HTTP {ex.code}{hint}")
        self.last = time.monotonic(); self.log.append({"url": url, "status": 200, "bytes": len(data), "retrieved": now()})
        return data if binary else data.decode("utf-8", "replace")

    def json(self, url: str):
        return json.loads(self.get(url))

    def cik_for(self, ticker: str) -> int:
        for v in self.json(f"{BASE_WWW}/files/company_tickers.json").values():
            if v["ticker"].upper() == ticker.upper():
                return int(v["cik_str"])
        raise KeyError(f"ticker {ticker} not in the SEC ticker map")

    def submissions(self, cik: int) -> dict:
        return self.json(f"{BASE_DATA}/submissions/CIK{int(cik):010d}.json")

    def companyfacts(self, cik: int) -> dict:
        return self.json(f"{BASE_DATA}/api/xbrl/companyfacts/CIK{int(cik):010d}.json")

    def filing_index(self, cik: int, accession: str) -> List[str]:
        a = accession.replace("-", ""); base = f"{BASE_WWW}/Archives/edgar/data/{int(cik)}/{a}"
        return [f"{base}/{it['name']}" for it in self.json(f"{base}/index.json")["directory"]["item"]]

    def document(self, cik: int, accession: str, name: str) -> str:
        return self.get(f"{BASE_WWW}/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{name}")


def html_to_text(s: str) -> str:
    """Strip tags, keep line breaks at block ends, unescape entities, collapse spaces."""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d|table)>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r" ?\n ?", "\n", re.sub(r"[ \t\xa0]+", " ", s)); s = re.sub(r" +([.,;:)%])", r"\1", s)
    return re.sub(r"\n+", "\n", s).strip()


def recent_filings(subs: dict) -> List[dict]:
    """The submissions JSON's column arrays as one dict per filing (accessionNumber, filingDate, acceptanceDateTime, form, ...)."""
    r = subs["filings"]["recent"]; keys = list(r)
    return [dict(zip(keys, vals)) for vals in zip(*[r[k] for k in keys])]


def exhibit_url(urls: List[str], prefer: str = "ex99") -> Optional[str]:
    """The press-release exhibit in a filing index (EX-99.1 for an 8-K or 6-K), else None."""
    cands = [u for u in urls if re.search(r"(?i)ex[-_]?99", u.rsplit("/", 1)[-1]) and u.lower().endswith((".htm", ".html", ".txt"))]
    return sorted(cands, key=lambda u: (not re.search(r"(?i)99[-_.]?1", u), len(u)))[0] if cands else None


def _smoke() -> None:
    try:
        Edgar("no-email"); raise AssertionError("a user agent without an email must be refused")
    except ValueError:
        pass
    e = Edgar("Example Person example@example.com"); assert e.gap >= 0.1 and e.log == []
    t = html_to_text("<html><head><style>p{}</style></head><body><p>Revenue was <b>$2.1&nbsp;billion</b>.</p><p>Next&amp;more</p></body></html>")
    assert t == "Revenue was $2.1 billion.\nNext&more", t
    subs = {"filings": {"recent": {"accessionNumber": ["0001-26-1", "0001-26-2"], "form": ["8-K", "10-K"], "filingDate": ["2026-01-22", "2026-02-20"]}}}
    fs = recent_filings(subs); assert len(fs) == 2 and fs[1]["form"] == "10-K"
    urls = ["https://www.sec.gov/Archives/edgar/data/1/000/form8k.htm", "https://www.sec.gov/Archives/edgar/data/1/000/ex99-1.htm", "https://www.sec.gov/Archives/edgar/data/1/000/ex99-2.htm"]
    assert exhibit_url(urls).endswith("ex99-1.htm") and exhibit_url(urls[:1]) is None
    print("edgar smoke test: ok (user-agent guard, throttle setting, html to text, filings table, exhibit choice; no network)")


if __name__ == "__main__":
    _smoke()
