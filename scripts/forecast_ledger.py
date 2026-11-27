"""The forecast ledger for the stress-test skill: a run's FORECASTS.csv, the shared LEDGER.csv and CALIBRATION.md.
Standard library only; the math is imported from forecast_tools.py in the same folder.

    python3 forecast_ledger.py                                   # smoke test
    python3 forecast_ledger.py --where                           # print the shared ledger folder this run would use
    python3 forecast_ledger.py --init [<dir>]                    # create LEDGER.csv + CALIBRATION.md there (or in <dir>)
    python3 forecast_ledger.py --check FORECASTS.csv             # required fields, ranges, groups, quantiles, extremes
    python3 forecast_ledger.py --score FORECASTS.csv             # fill score / score_kind where outcome is present
    python3 forecast_ledger.py --append FORECASTS.csv --run <id> [--project <name>] [--to LEDGER.csv]
    python3 forecast_ledger.py --calibrate [LEDGER.csv] --out CALIBRATION.md
    python3 forecast_ledger.py --sheet-rows FORECASTS.csv --run <id>   # ledger rows as TSV, for a connected spreadsheet

The shared folder, when --to / --calibrate / --init give none, is the first of: $STRESS_TEST_LEDGER;
a ledger/ folder in the working folder or at the top of its repository (a committed folder, which outlives
a cloud session; in a cloud session it is used even before it exists); ~/.claude/sessions/stress-test-forecasts
(the laptop). In a repository's ledger/ each run is its own file under runs/, so two sessions on two branches
never edit the same file; --calibrate reads LEDGER.csv and every file under runs/. The columns, the folder
order and the file reading are in ledger_store.py. Rules: references/forecast.md sections 2, 6, 8 and 9; the
outcome sets every level logs: references/outcomes.md.
"""
from __future__ import annotations

import argparse
import os
import re
import statistics
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from forecast_tools import QLEVELS, brier, calibration_table, check_partition, check_quantiles, cluster_bootstrap, quantile_score
from ledger_store import (COLUMNS, EPHEMERAL_NOTE, LAPTOP_LEDGER_DIR, LEDGER_COLUMNS, OUTCOME_GROUP, in_outcome_set, is_headline,  # noqa: F401
                          ledger_target, num as _f, outcome_sets, read_csv, read_ledger, resolve_ledger_dir, write_csv, write_run_file)

QCOLS = ("q05", "q25", "q50", "q75", "q95")
REQUIRED = ["id", "decision", "made", "kind", "question", "criterion", "source", "resolve_date", "forecaster", "method"]


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
        if g.endswith(OUTCOME_GROUP):  # an outcome set (references/outcomes.md): once resolved, exactly one row happened
            ys = [_f(r.get("outcome")) for r in rows if r.get("group") == g and r.get("status") == "resolved"]
            if len(ys) == len(ps) and None not in ys and abs(sum(ys) - 1.0) > 1e-9:
                problems.append(f"group {g}: {sum(ys):g} rows marked as happened; exactly one row of an outcome set happens")
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


def level_of(r: dict) -> str:
    m = re.match(r"\s*level\s*(\d)", r.get("method") or "", re.I)
    return m.group(1) if m else "untagged"


def outcome_set_report(ledger: Sequence[dict]) -> str:
    sets = outcome_sets(ledger)
    if not sets:
        return ""
    lines = ["", "## Outcome sets (references/outcomes.md)", "",
             f"- Sets resolved: {len(sets)}; what happened had been given {statistics.fmean(s['p_realized'] for s in sets):.0%} on average",
             f"- Mean multi-category Brier: {statistics.fmean(s['brier'] for s in sets):.3f} "
             f"(an even split over the same rows scores {statistics.fmean(s['even'] for s in sets):.3f}; lower is better)"]
    others = [s["other"] for s in sets if s["other"]]
    if others:
        lines.append(f"- Not listed: given {statistics.fmean(p for p, _ in others):.0%} on average, happened in "
                     f"{statistics.fmean(y for _, y in others):.0%} of {len(others)} sets")
    return "\n".join(lines) + "\n"


def calibration_report(ledger: Sequence[dict], min_skill_n: int = 15, min_bin_n: int = 8) -> str:
    # an outcome set enters the pooled figures through its headline row only (is_headline); the set is scored whole at the end
    res = [r for r in ledger if r.get("status") == "resolved" and r.get("kind") in ("event", "ranking") and is_headline(r)
           and _f(r.get("p")) is not None and _f(r.get("outcome")) is not None]
    lines = [f"# Calibration record — regenerated {date.today().isoformat()}", ""]
    today = date.today().isoformat()
    overdue = [r for r in ledger if r.get("status") == "open" and (r.get("resolve_date") or "9999") < today]
    if overdue:
        # the review-date task (references/forecast.md section 13) resolves these before any new row is written
        lines += [f"**{len(overdue)} open row(s) past their resolve date** — resolve from each row's named source before writing new rows:", ""]
        lines += [f"- {r.get('id')} ({r.get('decision')}, due {r.get('resolve_date')}): {r.get('question')} — source: {r.get('source')}"
                  for r in overdue[:50]]
        if len(overdue) > 50:
            lines.append(f"- … and {len(overdue) - 50} more")
        lines.append("")
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
    by_lvl: Dict[str, List[Tuple[float, int]]] = {}
    for r, pr in zip(res, pairs):
        by_lvl.setdefault(level_of(r), []).append(pr)
    if set(by_lvl) - {"untagged"}:  # rows whose method starts "level N": the outcome sets every level logs
        lines += ["", "## By level", "", "| level | n | mean Brier | yes-lean |", "|---|---|---|---|"]
        for lv, prs in sorted(by_lvl.items()):
            lines.append(f"| {lv} | {len(prs)} | {statistics.fmean(brier(p, o) for p, o in prs):.3f} | "
                         f"{statistics.fmean(p for p, _ in prs) - statistics.fmean(o for _, o in prs):+.3f} |")
    return "\n".join(lines) + "\n" + outcome_set_report(ledger)


def sheet_rows(rows: List[Dict[str, str]], run: str, project: str) -> str:
    """Ledger rows as tab-separated text, header first, for appending to a connected spreadsheet."""
    out = ["\t".join(LEDGER_COLUMNS)]
    for r in rows:
        full = dict(r, run=run, project=project)
        out.append("\t".join((full.get(c) or "").replace("\t", " ").replace("\n", " ") for c in LEDGER_COLUMNS))
    return "\n".join(out) + "\n"


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
        stale = [dict(base, id="S1", kind="event", question="late", p="0.5", range_low="0.4", range_high="0.6", resolve_date="2000-01-01")]
        assert "1 open row(s) past their resolve date" in calibration_report(stale) and "S1 (demo, due 2000-01-01)" in calibration_report(stale)
        init_folder(os.path.join(d, "shared"))
        assert os.path.exists(os.path.join(d, "shared", "CALIBRATION.md"))
        # the shared folder still resolves through this module (the order and the kinds are tested in ledger_store.py)
        assert resolve_ledger_dir("/x/y", env={"STRESS_TEST_LEDGER": "/z"}, cwd=d) == "/x/y"
        assert resolve_ledger_dir(None, env={}, cwd=d) == os.path.expanduser(LAPTOP_LEDGER_DIR)
        tsv = sheet_rows(rows, "run-1", "demo").splitlines()
        assert tsv[0].split("\t") == LEDGER_COLUMNS and len(tsv) == 4 and tsv[1].startswith("run-1\tdemo\tF1\t")
        # an outcome set (references/outcomes.md): one run file, exactly one row happens, the headline row alone is pooled
        oset = [dict(base, id=i, kind="event", question=q, p=p, range_low=lo, range_high=hi, group="demo3:outcomes", decision="demo3",
                     method="level 1: lead's judgment")
                for i, q, p, lo, hi in (("O1", "Works", "0.55", "0.4", "0.7"), ("O2", "Partly", "0.25", "0.15", "0.35"),
                                        ("O3", "Fails", "0.15", "0.05", "0.25"), ("OX", "Not listed", "0.05", "0.05", "0.15"))]
        assert check_run(oset) == [], check_run(oset)
        rl = os.path.join(d, "repo-ledger")
        write_run_file(oset, rl, "demo3-L1", "demo")
        for r, o in zip(oset, ("0", "1", "0", "0")):
            r["status"], r["outcome"] = "resolved", o
        assert check_run(oset) == [] and any("exactly one row" in m for m in check_run([dict(r, outcome="1") for r in oset]))
        score_rows(oset, today="2026-11-18"); append_run(oset, os.path.join(rl, "LEDGER.csv"), "demo3-L1", "demo")
        merged = read_ledger(rl)
        assert len(merged) == 4 and all(r["status"] == "resolved" for r in merged), "the resolved copy wins over the open run file"
        rep2 = calibration_report(merged + read_csv(led))
        assert "Resolved event forecasts: 5" in rep2, "a set adds its headline row only to the pooled figures"
        assert "## By level" in rep2 and "| 1 | 1 |" in rep2 and "Sets resolved: 1" in rep2 and "Not listed: given 5%" in rep2
    print("forecast_ledger smoke test: ok (run check, scoring, append with dedupe, calibration report, init, sheet rows, "
          "outcome sets checked and scored whole, by-level table, run files merged)")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for flag, meta in (("--check", "FORECASTS.csv"), ("--score", "FORECASTS.csv"), ("--append", "FORECASTS.csv"),
                       ("--to", "LEDGER.csv"), ("--out", "CALIBRATION.md"), ("--sheet-rows", "FORECASTS.csv")):
        ap.add_argument(flag, metavar=meta)
    ap.add_argument("--init", nargs="?", const="", metavar="DIR")
    ap.add_argument("--calibrate", nargs="?", const="", metavar="LEDGER.csv")
    ap.add_argument("--where", action="store_true", help="print the shared ledger folder this run would use")
    ap.add_argument("--split", action="store_true", help="with --append: write the run as its own file under runs/ "
                    "(the default in a repository's ledger/ folder)")
    ap.add_argument("--run")
    ap.add_argument("--project", default="")
    a = ap.parse_args(argv)
    if a.where:
        folder, kind = ledger_target()
        print(folder)
        if kind == "repo":
            print("(a repository folder: each run is written as its own file under runs/; commit and push it with the run)")
        elif kind == "ephemeral":
            print(f"({EPHEMERAL_NOTE})")
    elif a.init is not None:
        folder = resolve_ledger_dir(a.init or None)
        init_folder(folder)
        print(f"initialised {folder}")
    elif a.check:
        probs = check_run(read_csv(a.check))
        print("\n".join(probs) if probs else "check: ok")
        return 1 if probs else 0
    elif a.score:
        rows = read_csv(a.score)
        n = score_rows(rows)
        # keep the file's own columns: a run's FORECASTS.csv, or a ledger file (LEDGER.csv, runs/<run>.csv) with run and project
        write_csv(a.score, rows, LEDGER_COLUMNS if rows and "run" in rows[0] else COLUMNS)
        print(f"scored {n} rows")
    elif a.append:
        if not a.run:
            ap.error("--append needs --run")
        folder, kind = (os.path.dirname(a.to) or ".", "explicit") if a.to else ledger_target()
        rows = read_csv(a.append)
        if a.split or kind == "repo":
            print(f"wrote {len(rows)} rows to {write_run_file(rows, folder, a.run, a.project)} (one file per run; commit and push it with the run)")
        else:
            to = a.to or os.path.join(folder, "LEDGER.csv")
            if not os.path.exists(to):
                init_folder(os.path.dirname(to) or ".")
            print(f"appended {append_run(rows, to, a.run, a.project)} rows to {to}")
        if kind == "ephemeral":
            print(f"warning: {EPHEMERAL_NOTE}")
    elif a.sheet_rows:
        if not a.run:
            ap.error("--sheet-rows needs --run")
        print(sheet_rows(read_csv(a.sheet_rows), a.run, a.project), end="")
    elif a.calibrate is not None:
        ledger = a.calibrate or os.path.join(resolve_ledger_dir(), "LEDGER.csv")
        rep = calibration_report(read_ledger(ledger))  # LEDGER.csv and every run file under runs/ beside it
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
