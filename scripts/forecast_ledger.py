"""The forecast ledger for stress-test-3: a run's FORECASTS.csv, the shared LEDGER.csv and CALIBRATION.md.
Standard library only; the math is imported from forecast_tools.py in the same folder.

    py -3 forecast_ledger.py                                   # smoke test
    py -3 forecast_ledger.py --init <dir>                      # create LEDGER.csv + CALIBRATION.md in the shared folder
    py -3 forecast_ledger.py --check FORECASTS.csv             # required fields, ranges, groups, quantiles, extremes
    py -3 forecast_ledger.py --score FORECASTS.csv             # fill score / score_kind where outcome is present
    py -3 forecast_ledger.py --append FORECASTS.csv --to LEDGER.csv --run <id> --project <name>
    py -3 forecast_ledger.py --calibrate LEDGER.csv --out CALIBRATION.md

Columns and rules: references/forecast.md sections 2, 6, 8 and 9.
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from forecast_tools import QLEVELS, brier, calibration_table, check_partition, check_quantiles, cluster_bootstrap, quantile_score

COLUMNS = ["id", "decision", "made", "kind", "question", "criterion", "source", "resolve_date", "p",
           "q05", "q25", "q50", "q75", "q95", "range_low", "range_high", "forecaster", "method",
           "base_rate", "base_class", "base_n", "group", "node", "cluster", "ref_value", "model_cutoff", "status", "outcome",
           "score", "score_kind", "resolved_on", "notes"]
LEDGER_COLUMNS = ["run", "project"] + COLUMNS
QCOLS = ("q05", "q25", "q50", "q75", "q95")
REQUIRED = ["id", "decision", "made", "kind", "question", "criterion", "source", "resolve_date", "forecaster", "method"]


def read_csv(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: str, rows: Sequence[dict], columns: Sequence[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def _f(x) -> Optional[float]:
    try:
        return float(x) if x not in ("", None) else None
    except ValueError:
        return None


def check_run(rows: Sequence[dict]) -> List[str]:
    """Problems with a run's FORECASTS rows; an empty list means the file passes."""
    problems: List[str] = []
    groups: Dict[str, List[float]] = {}
    for r in rows:
        rid = r.get("id", "?")
        problems += [f"{rid}: missing {c}" for c in REQUIRED if not r.get(c)]
        kind, p = r.get("kind", ""), _f(r.get("p"))
        if kind in ("event", "ranking"):
            if p is None or not (0.0 <= p <= 1.0):
                problems.append(f"{rid}: p missing or outside [0,1]")
            else:
                lo, hi = _f(r.get("range_low")), _f(r.get("range_high"))
                if lo is None or hi is None:
                    problems.append(f"{rid}: range_low/range_high missing")
                elif not (lo <= p <= hi):
                    problems.append(f"{rid}: p {p} outside its range [{lo}, {hi}]")
                if (p < 0.05 or p > 0.95) and not r.get("base_class"):
                    problems.append(f"{rid}: p {p} is extreme with no named-case base_class")
                if r.get("group"):
                    groups.setdefault(r["group"], []).append(p)
        elif kind == "quantity":
            qs = [_f(r.get(c)) for c in QCOLS]
            if any(q is None for q in qs):
                problems.append(f"{rid}: quantity needs all five quantiles")
            elif not check_quantiles(qs):
                problems.append(f"{rid}: quantiles not monotone")
        else:
            problems.append(f"{rid}: unknown kind '{kind}'")
        bn = _f(r.get("base_n"))
        if r.get("base_rate") and (bn is None or bn < 30) and "estimated" not in (r.get("notes") or "").lower():
            problems.append(f"{rid}: base_n under 30 (or missing) but notes do not say 'estimated'")
        if r.get("status") not in ("open", "resolved", "void"):
            problems.append(f"{rid}: status must be open, resolved or void")
    for g, ps in groups.items():
        if len(ps) > 1 and not check_partition(ps):
            problems.append(f"group {g}: probabilities sum to {sum(ps):.3f}, not 1")
    return problems


def score_rows(rows: Sequence[dict], today: Optional[str] = None) -> int:
    """Fill score and score_kind where status is resolved and outcome is present. Returns the count scored."""
    n = 0
    for r in rows:
        y = _f(r.get("outcome"))
        if r.get("status") != "resolved" or y is None or r.get("score"):
            continue
        if r.get("kind") in ("event", "ranking"):
            r["score"], r["score_kind"] = f"{brier(_f(r['p']), int(y)):.4f}", "brier"
        elif r.get("kind") == "quantity":
            r["score"] = f"{quantile_score({t: _f(r.get(c)) for t, c in zip(QLEVELS, QCOLS)}, y):.4f}"
            r["score_kind"] = "pinball5"
        else:
            continue
        r["resolved_on"] = r.get("resolved_on") or (today or date.today().isoformat())
        n += 1
    return n


def append_run(run_rows: Sequence[dict], ledger_path: str, run_id: str, project: str) -> int:
    """Append a run's rows to the shared ledger; rows already present (same run and id) are skipped."""
    ledger = read_csv(ledger_path)
    seen = {(r.get("run"), r.get("id")) for r in ledger}
    added = 0
    for r in run_rows:
        if (run_id, r.get("id")) in seen:
            continue
        ledger.append({"run": run_id, "project": project, **r})
        seen.add((run_id, r.get("id")))
        added += 1
    write_csv(ledger_path, ledger, LEDGER_COLUMNS)
    return added


def calibration_report(ledger: Sequence[dict], min_skill_n: int = 15, min_bin_n: int = 8) -> str:
    res = [r for r in ledger if r.get("status") == "resolved" and r.get("kind") in ("event", "ranking")
           and _f(r.get("p")) is not None and _f(r.get("outcome")) is not None]
    lines = [f"# Calibration record — regenerated {date.today().isoformat()}", ""]
    if not res:
        return "\n".join(lines + ["No resolved event forecasts yet. Skill and bin tests read n/a until fifteen resolutions "
                                  "from at least two independent questions, and eight in a bin.", ""]) + "\n"
    pairs = [(float(r["p"]), int(float(r["outcome"]))) for r in res]
    briers = [brier(p, o) for p, o in pairs]
    by_dec: Dict[str, List[float]] = {}
    for r, b in zip(res, briers):
        by_dec.setdefault(r.get("decision") or r.get("run") or "?", []).append(b)
    point, lo, hi = cluster_bootstrap(by_dec, stat=lambda xs: 1.0 - statistics.fmean(xs) / 0.25)
    n = len(pairs)
    lean = statistics.fmean(p for p, _ in pairs) - statistics.fmean(o for _, o in pairs)
    skill = (f"- Brier skill vs climatology: {point:+.3f}, 80% cluster-bootstrap interval [{lo:+.3f}, {hi:+.3f}]"
             if n >= min_skill_n and len(by_dec) >= 2 else
             f"- Brier skill: n/a (n={n}, decisions={len(by_dec)}; needs {min_skill_n} from at least 2)")
    lines += [f"- Resolved event forecasts: {n} across {len(by_dec)} decisions "
              f"(all resolved rows: {sum(1 for r in ledger if r.get('status') == 'resolved')})",
              f"- Mean Brier: {statistics.fmean(briers):.3f} (climatology 0.250)", skill,
              f"- Yes-lean (mean forecast minus mean outcome): {lean:+.3f}", "",
              "| bin | n | mean p | resolved | Wilson 90% |", "|---|---|---|---|---|"]
    for row in calibration_table(pairs):
        if row["n"]:
            flag = "" if row["n"] >= min_bin_n else " (n under 8: no test)"
            lines.append(f"| {row['bin_lo']:.1f}–{row['bin_hi']:.1f} | {row['n']} | {row['mean_p']:.2f} | {row['freq']:.2f} "
                         f"| [{row['wilson_lo']:.2f}, {row['wilson_hi']:.2f}]{flag} |")
    by_fc: Dict[str, List[Tuple[float, int]]] = {}
    for r, pr in zip(res, pairs):
        by_fc.setdefault(r.get("forecaster") or "?", []).append(pr)
    lines += ["", "## By forecaster", "", "| forecaster | n | mean Brier | yes-lean |", "|---|---|---|---|"]
    for fc, prs in sorted(by_fc.items()):
        lines.append(f"| {fc} | {len(prs)} | {statistics.fmean(brier(p, o) for p, o in prs):.3f} | "
                     f"{statistics.fmean(p for p, _ in prs) - statistics.fmean(o for _, o in prs):+.3f} |")
    by_kind: Dict[str, List[float]] = {}
    for r, b in zip(res, briers):
        by_kind.setdefault(r.get("kind") or "?", []).append(b)
    lines += ["", "## By kind of question", "", "| kind | n | mean Brier |", "|---|---|---|"]
    lines += [f"| {k} | {len(bs)} | {statistics.fmean(bs):.3f} |" for k, bs in sorted(by_kind.items())]
    return "\n".join(lines) + "\n"


def init_folder(folder: str) -> None:
    os.makedirs(folder, exist_ok=True)
    ledger = os.path.join(folder, "LEDGER.csv")
    if not os.path.exists(ledger):
        write_csv(ledger, [], LEDGER_COLUMNS)
    with open(os.path.join(folder, "CALIBRATION.md"), "w", encoding="utf-8") as fh:
        fh.write(calibration_report(read_csv(ledger)))


def _smoke() -> None:
    import tempfile
    base = dict(decision="demo", made="2026-10-18", criterion="close vs benchmark", source="closes.csv", resolve_date="2026-11-18",
                forecaster="lead", method="base rate", base_rate="0.5", base_class="demo class", base_n="40",
                model_cutoff="2026-06", status="open", notes="too high: x; too low: y")
    rows = [dict(base, id="F1", kind="event", question="A beats B", p="0.62", range_low="0.55", range_high="0.70", group="g1"),
            dict(base, id="F2", kind="event", question="B beats A", p="0.38", range_low="0.30", range_high="0.45", group="g1"),
            dict(base, id="F3", kind="quantity", question="excess return", q05="-0.2", q25="-0.05", q50="0.01", q75="0.06", q95="0.2")]
    assert check_run(rows) == [], check_run(rows)
    assert any("extreme" in m for m in check_run([dict(base, id="X1", kind="event", question="q", p="0.02", range_low="0", range_high="0.1", base_class="")]))
    for r, o in zip(rows, ("1", "0", "0.03")):
        r["status"], r["outcome"] = "resolved", o
    assert score_rows(rows, today="2026-11-18") == 3 and rows[0]["score_kind"] == "brier" and rows[2]["score_kind"] == "pinball5"
    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "LEDGER.csv")
        assert append_run(rows, led, "run-1", "demo") == 3 and append_run(rows, led, "run-1", "demo") == 0
        append_run([dict(r, id=r["id"] + "b", decision="demo2") for r in rows], led, "run-2", "demo")
        rep = calibration_report(read_csv(led))
        assert "Resolved event forecasts: 4" in rep and "Brier skill: n/a" in rep
        init_folder(os.path.join(d, "shared"))
        assert os.path.exists(os.path.join(d, "shared", "CALIBRATION.md"))
    print("forecast_ledger smoke test: ok (run check, scoring, append with dedupe, calibration report, init)")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for flag, meta in (("--init", "DIR"), ("--check", "FORECASTS.csv"), ("--score", "FORECASTS.csv"),
                       ("--append", "FORECASTS.csv"), ("--to", "LEDGER.csv"), ("--calibrate", "LEDGER.csv"), ("--out", "CALIBRATION.md")):
        ap.add_argument(flag, metavar=meta)
    ap.add_argument("--run")
    ap.add_argument("--project", default="")
    a = ap.parse_args(argv)
    if a.init:
        init_folder(a.init)
        print(f"initialised {a.init}")
    elif a.check:
        probs = check_run(read_csv(a.check))
        print("\n".join(probs) if probs else "check: ok")
        return 1 if probs else 0
    elif a.score:
        rows = read_csv(a.score)
        n = score_rows(rows)
        write_csv(a.score, rows, COLUMNS)
        print(f"scored {n} rows")
    elif a.append:
        if not (a.to and a.run):
            ap.error("--append needs --to and --run")
        print(f"appended {append_run(read_csv(a.append), a.to, a.run, a.project)} rows to {a.to}")
    elif a.calibrate:
        rep = calibration_report(read_csv(a.calibrate))
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(rep)
            print(f"wrote {a.out}")
        else:
            print(rep)
    else:
        _smoke()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
