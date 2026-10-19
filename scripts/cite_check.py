"""Citation liveness check for stress-test-3 briefs. Standard library only.

Extracts every http(s) URL from the files given, checks that each resolves (HEAD, then GET after any HEAD
failure), and for a dead one asks the Wayback Machine for the closest archived copy with a 200 status.
Liveness is not support: a resolving page may still not say what the sentence claims; that is the second
reader's job (research-6b.md). A 401, 403 or 429 is reported as `blocked`, not dead: check it by hand.

    py -3 cite_check.py brief.md [more files] [--out CITES.md] [--timeout 15] [--no-archive] [--json]
                        [--ua "Name email"] [--timestamp YYYYMMDD]
    py -3 cite_check.py --selftest          # offline smoke test, no network

Exit 0 when every URL resolves, is blocked, or has a live archived copy; 1 when any is dead with no archive
or when no URL was found at all (a vacuous pass is a failure); 2 on usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

URL_RE = re.compile(r"https?://[^\s<>\[\]\"'`*|]+")
TRAIL = ".,;:!?]}>'\"*|"   # a trailing ')' is stripped only when unbalanced, so wiki-style URLs survive
DEFAULT_UA = "stress-test-3 cite_check (liveness check for a research brief)"
BLOCKED = {401, 403, 429, 451, 999}


def extract_urls(text: str) -> List[str]:
    """Unique URLs in order of first appearance, trailing punctuation and markdown emphasis stripped."""
    seen: Dict[str, None] = {}
    for m in URL_RE.finditer(text):
        u = m.group(0)
        changed = True
        while changed:
            changed = False
            s = u.rstrip(TRAIL)
            if s != u:
                u, changed = s, True
            if u.endswith(")") and u.count("(") < u.count(")"):
                u, changed = u[:-1], True
        seen.setdefault(u, None)
    return list(seen)


def encode_url(url: str) -> str:
    """Percent-encode non-ASCII characters so urllib can request the address."""
    return urllib.parse.quote(url, safe="%/:=&?~#+!$,;'@()*[]")


def _request(url: str, method: str, timeout: float, ua: str) -> int:
    req = urllib.request.Request(encode_url(url), method=method, headers={"User-Agent": ua, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # follows redirects
        if method == "GET":
            resp.read(2048)
        return int(resp.status)


def check_url(url: str, timeout: float = 15.0, ua: str = DEFAULT_UA) -> Dict[str, object]:
    """{'url', 'status': 'ok'|'blocked'|'dead', 'code': int|None, 'detail': str}."""
    try:
        return {"url": url, "status": "ok", "code": _request(url, "HEAD", timeout, ua), "detail": "HEAD"}
    except Exception as e1:  # noqa: BLE001 — any HEAD failure falls back to GET
        head = f"HEAD {e1.code}" if isinstance(e1, urllib.error.HTTPError) else f"HEAD {type(e1).__name__}"
        if isinstance(e1, urllib.error.HTTPError) and e1.code == 429:
            time.sleep(2.0)
        try:
            return {"url": url, "status": "ok", "code": _request(url, "GET", timeout, ua), "detail": f"GET after {head}"}
        except urllib.error.HTTPError as e2:
            st = "blocked" if e2.code in BLOCKED else "dead"
            return {"url": url, "status": st, "code": e2.code, "detail": f"HTTP {e2.code}"}
        except (urllib.error.URLError, socket.timeout, ConnectionError, ValueError, UnicodeError) as e2:
            reason = getattr(e2, "reason", "")
            return {"url": url, "status": "dead", "code": None, "detail": type(e2).__name__ + (f": {reason}" if reason else "")}
        except Exception as e2:  # noqa: BLE001
            return {"url": url, "status": "dead", "code": None, "detail": type(e2).__name__}


def archive_lookup(url: str, timeout: float = 15.0, timestamp: Optional[str] = None, ua: str = DEFAULT_UA) -> Optional[str]:
    """Closest Wayback snapshot URL whose own status is 200, or None. `timestamp` is YYYYMMDD."""
    q = {"url": url}
    if timestamp:
        q["timestamp"] = timestamp
    api = "https://archive.org/wayback/available?" + urllib.parse.urlencode(q)
    try:
        req = urllib.request.Request(api, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        snap = (data.get("archived_snapshots") or {}).get("closest") or {}
        return snap.get("url") if snap.get("available") and str(snap.get("status", "")) == "200" else None
    except Exception:  # noqa: BLE001
        return None


def classify(results: List[Dict[str, object]]) -> Dict[str, int]:
    c = {"ok": 0, "blocked": 0, "archived": 0, "dead": 0}
    for r in results:
        if r["status"] in ("ok", "blocked"):
            c[r["status"]] += 1
        elif r.get("archive"):
            c["archived"] += 1
        else:
            c["dead"] += 1
    return c


def render_table(results: List[Dict[str, object]], counts: Dict[str, int]) -> str:
    lines = ["# Citation check", "",
             f"{len(results)} URLs: {counts['ok']} resolve, {counts['blocked']} blocked (check by hand), "
             f"{counts['archived']} dead but archived, {counts['dead']} dead with no archive.",
             "Liveness only: a resolving page may still not support its sentence; that is the second reader's job.", "",
             "| # | status | code | url | archive or detail |", "|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        state = r["status"] if r["status"] in ("ok", "blocked") else ("archived" if r.get("archive") else "DEAD")
        lines.append(f"| {i} | {state} | {r.get('code') or ''} | {r['url']} | {r.get('archive') or r.get('detail', '')} |")
    return "\n".join(lines) + "\n"


def run(paths: List[str], timeout: float, archive: bool, timestamp: Optional[str], ua: str) -> List[Dict[str, object]]:
    text = ""
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            text += fh.read() + "\n"
    results = []
    for url in extract_urls(text):
        r = check_url(url, timeout, ua)
        if r["status"] == "dead" and archive:
            r["archive"] = archive_lookup(url, timeout, timestamp, ua)
        results.append(r)
        print(f"{r['status']:7s} {r.get('code') or '':>4} {url}" + (f"  -> {r['archive']}" if r.get("archive") else ""), file=sys.stderr)
    return results


def _selftest() -> None:
    sample = ("See (https://example.com/a), **https://example.com/b**. | https://example.com/c|cell <https://example.com/d>; "
              "https://en.wikipedia.org/wiki/Brier_score_(statistics) twice https://example.com/a https://de.wikipedia.org/wiki/München")
    urls = extract_urls(sample)
    assert urls == ["https://example.com/a", "https://example.com/b", "https://example.com/c", "https://example.com/d",
                    "https://en.wikipedia.org/wiki/Brier_score_(statistics)", "https://de.wikipedia.org/wiki/München"], urls
    assert encode_url(urls[-1]) == "https://de.wikipedia.org/wiki/M%C3%BCnchen"
    fake = [{"url": "u1", "status": "ok", "code": 200, "detail": "HEAD"},
            {"url": "u2", "status": "dead", "code": 404, "detail": "HTTP 404", "archive": "https://web.archive.org/web/2026/u2"},
            {"url": "u3", "status": "dead", "code": None, "detail": "URLError", "archive": None},
            {"url": "u4", "status": "blocked", "code": 403, "detail": "HTTP 403"}]
    counts = classify(fake)
    assert counts == {"ok": 1, "blocked": 1, "archived": 1, "dead": 1}, counts
    table = render_table(fake, counts)
    assert "| 3 | DEAD |" in table and "| 4 | blocked |" in table
    bad = check_url("http://nonexistent.invalid/x", timeout=3)   # .invalid never resolves: offline-safe negative case
    assert bad["status"] == "dead", bad
    print("cite_check selftest: ok (extraction incl. emphasis, table cells and non-ASCII; encoding; classification; table; dead host)")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--no-archive", action="store_true")
    ap.add_argument("--timestamp", help="YYYYMMDD: prefer archive copies near this date (the brief's access date)")
    ap.add_argument("--ua", default=DEFAULT_UA, help='user agent, e.g. "Jane Doe jane@example.com" for filing databases')
    ap.add_argument("--json", action="store_true", help="print JSON instead of the table")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        _selftest()
        return 0
    if not a.files:
        ap.print_usage()
        return 2
    results = run(a.files, a.timeout, not a.no_archive, a.timestamp, a.ua)
    if not results:
        print("no URL found in the files given: the sources table needs a Link column (research-6.md section 4)", file=sys.stderr)
        return 1
    counts = classify(results)
    out = json.dumps({"counts": counts, "results": results}, indent=1) if a.json else render_table(results, counts)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"wrote {a.out}: {counts}")
    else:
        print(out)
    return 1 if counts["dead"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
