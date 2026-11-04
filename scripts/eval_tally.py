"""Tally the eval set (evals/README.md): per-level hit rates with Wilson intervals, and the paired
comparison between adjacent levels on the decisions run at both. Standard library only.

    python3 eval_tally.py                        # smoke test
    python3 eval_tally.py evals/results.csv      # the tally
    python3 eval_tally.py evals/results.csv --compare 1 4   # one specific pair of levels

Columns of results.csv: slug, level, run_date, model, effort, skill_commit, call_matched,
kill_criterion_right, weakest_link_named, first_step_right, points, words, notes. Measures are 1, 0, 0.5 or na; a row whose
notes say "void" is skipped. Rows are never edited; a correction is a new row that names the old one.
"""
from __future__ import annotations

import csv
import math
import sys
from typing import Dict, List, Optional, Sequence, Tuple

MEASURES = ("call_matched", "kill_criterion_right", "weakest_link_named", "first_step_right")


def wilson(k: float, n: int, z: float = 1.645) -> Tuple[float, float]:
    """Wilson score interval (90% at z=1.645) for k successes in n; fractional k is allowed (0.5 credits)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def value(s: str) -> Optional[float]:
    s = (s or "").strip().lower()
    if s in ("", "na", "n/a", "-"):
        return None
    return float(s)


def read_rows(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if "void" not in (r.get("notes") or "").lower()]


def latest_per_decision(rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, str]]:
    """One row per (slug, level): the latest run_date, so a re-run after a rule change replaces the old row in the tally."""
    out: Dict[Tuple[str, str], Dict[str, str]] = {}
    for r in rows:
        key = (r["slug"].strip(), r["level"].strip())
        if key not in out or (r.get("run_date") or "") >= (out[key].get("run_date") or ""):
            out[key] = r
    return out


def per_level(latest: Dict[Tuple[str, str], Dict[str, str]]) -> List[str]:
    levels = sorted({lvl for _, lvl in latest}, key=lambda x: (len(x), x))
    lines = ["| level | n | " + " | ".join(MEASURES) + " | mean points |", "|---|---|" + "---|" * len(MEASURES) + "---|"]
    for lvl in levels:
        rows = [r for (s, l), r in latest.items() if l == lvl]
        cells = []
        for m in MEASURES:
            vals = [v for v in (value(r.get(m, "")) for r in rows) if v is not None]
            if not vals:
                cells.append("n/a")
                continue
            lo, hi = wilson(sum(vals), len(vals))
            cells.append(f"{sum(vals) / len(vals):.2f} [{lo:.2f}, {hi:.2f}] n={len(vals)}")
        pts = [v for v in (value(r.get("points", "")) for r in rows) if v is not None]
        mean_pts = f"{sum(pts) / len(pts):.1f}" if pts else "n/a"
        lines.append(f"| {lvl} | {len(rows)} | " + " | ".join(cells) + f" | {mean_pts} |")
    return lines


def paired(latest: Dict[Tuple[str, str], Dict[str, str]], a: str, b: str) -> str:
    slugs = sorted({s for (s, l) in latest if l == a} & {s for (s, l) in latest if l == b})
    if not slugs:
        return f"levels {a} vs {b}: no decision run at both"
    wins = losses = ties = 0
    pa = pb = 0.0
    npts = 0
    for s in slugs:
        va, vb = value(latest[(s, a)].get("call_matched", "")), value(latest[(s, b)].get("call_matched", ""))
        if va is None or vb is None:
            continue
        if vb > va:
            wins += 1
        elif vb < va:
            losses += 1
        else:
            ties += 1
        xa, xb = value(latest[(s, a)].get("points", "")), value(latest[(s, b)].get("points", ""))
        if xa is not None and xb is not None:
            pa += xa
            pb += xb
            npts += 1
    n = wins + losses + ties
    cost = f"; mean points {pa / npts:.1f} vs {pb / npts:.1f}" if npts else ""
    verdict = "higher level ahead" if wins > losses else ("lower level ahead" if losses > wins else "no difference")
    return (f"levels {a} vs {b} on {n} paired decisions (call_matched): level {b} wins {wins}, loses {losses}, ties {ties}"
            f" — {verdict}; a one-decision difference is inside the interval below about n=15{cost}")


def tally(path: str, compare: Optional[Tuple[str, str]] = None) -> str:
    latest = latest_per_decision(read_rows(path))
    if not latest:
        return "no scored rows yet — see evals/README.md for how a run is scored"
    lines = ["# Eval tally", "", f"Decisions: {len({s for s, _ in latest})}; rows counted: {len(latest)} (latest run per decision and level)", ""]
    lines += per_level(latest)
    lines.append("")
    levels = sorted({lvl for _, lvl in latest}, key=lambda x: (len(x), x))
    pairs = [compare] if compare else list(zip(levels, levels[1:]))
    lines += [paired(latest, a, b) for a, b in pairs]
    return "\n".join(lines) + "\n"


def _smoke() -> None:
    import os
    import tempfile
    lo, hi = wilson(5, 10)
    assert 0.25 < lo < 0.5 < hi < 0.75, (lo, hi)
    assert wilson(0, 0) == (0.0, 1.0)
    rows = [
        "slug,level,run_date,model,effort,skill_commit,call_matched,kill_criterion_right,weakest_link_named,first_step_right,points,words,notes",
        "a,1,2026-11-01,opus,high,abc,1,na,1,1,0.5,400,",
        "a,2,2026-11-01,opus,high,abc,1,1,1,1,2,900,",
        "b,1,2026-11-01,opus,high,abc,0,0,0,1,0.4,380,",
        "b,2,2026-11-01,opus,high,abc,1,1,1,1,2.5,950,",
        "b,2,2026-10-01,opus,,old,0,0,0,0,2.5,950,superseded by the later run",
        "c,1,2026-11-01,opus,high,abc,0.5,na,1,0,0.6,420,",
        "c,2,2026-11-01,opus,high,abc,0,0,0,0,2,880,void: key leaked",
    ]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "results.csv")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(rows) + "\n")
        out = tally(p)
        assert "Decisions: 3" in out and "rows counted: 5" in out, out
        assert "level 2 wins 1, loses 0, ties 1" in out, out
        assert "| 1 | 3 |" in out and "n=3" in out
        assert tally(p, ("1", "2")).count("levels 1 vs 2") == 1
    print("eval_tally smoke test: ok (Wilson, latest-run dedupe, void rows skipped, per-level table, paired comparison)")


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        _smoke()
        return 0
    compare = None
    if "--compare" in argv:
        i = argv.index("--compare")
        compare = (argv[i + 1], argv[i + 2])
        del argv[i:i + 3]
    print(tally(argv[0], compare), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
