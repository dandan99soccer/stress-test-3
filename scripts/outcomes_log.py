"""Logging and the command line for outcomes.py (the stress-test skill's Outcomes block, references/outcomes.md): the set's
rows appended to the shared forecast ledger at every level, the run's FORECASTS.csv at levels 4 to 6, the tab-separated rows
for a connected sheet, and the one line the shared record has to say back. Standard library only.

    python3 outcomes_log.py                     # smoke test
    python3 outcomes.py <arguments>             # the command line; outcomes.py's docstring lists the arguments

Where the rows go is ledger_store.ledger_target's answer: the laptop folder, a repository's ledger/ folder (one file per run
under runs/, committed and pushed with the session's work), or nowhere in a cloud session outside any repository, in which
case the `Logged:` line says so. A run logged again before any of its rows has resolved replaces its own outcome rows.
"""
from __future__ import annotations

import argparse
import os
import re
import statistics
import sys
from datetime import date
from typing import List, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forecast_ledger as FL  # noqa: E402
import outcomes as OC  # noqa: E402
from ledger_store import run_file  # noqa: E402
from outcomes import all_of, bins_from_dist, bins_from_quantiles, bucket_labels, build, ledger_rows, render, round_to_100  # noqa: E402


def record_line(ledger: Sequence[dict], today: Optional[str] = None) -> Optional[str]:
    """One line from the shared record, only when it has something to say: the lean once fifteen sets have resolved
    (references/forecast.md section 8), and any open rows past their date."""
    today, parts = today or date.today().isoformat(), []
    sets = FL.outcome_sets(ledger)
    if len(sets) >= 15:
        heads = [(float(r["p"]), float(r["outcome"])) for r in ledger if FL.in_outcome_set(r) and r.get("id") == "O1" and r.get("status") == "resolved"]
        lean = statistics.fmean(p for p, _ in heads) - statistics.fmean(y for _, y in heads)
        parts.append(f"{len(sets)} outcome sets resolved; what happened had been given {statistics.fmean(x['p_realized'] for x in sets):.0%} "
                     f"on average; headline yes-lean {lean:+.2f}")
    due = sorted(r.get("resolve_date") or "" for r in ledger if r.get("status") == "open" and (r.get("resolve_date") or "9999") < today)
    if due:
        parts.append(f"{len(due)} open rows are past their date (oldest {due[0]}): resolve them from their named sources (forecast.md section 13)")
    return "Record: " + "; ".join(parts) if parts else None


def _still_open(existing: Sequence[dict], run: str) -> None:
    if any(r.get("status") != "open" for r in existing):
        raise ValueError(f"run {run} already has resolved rows; rows are never edited after they resolve: pass a new --run")


def log(s: dict, rows: List[dict], a) -> str:
    """Append the rows to the shared ledger and return the `Logged:` line. A run logged again before any of its rows has
    resolved replaces its own outcome rows; nothing else in the ledger is touched."""
    run = a.run or f"{s['decision']}-{s['made']}-L{s['level']}"
    try:
        if a.to:
            folder, kind = (os.path.dirname(a.to) or "." if a.to.lower().endswith(".csv") else a.to), "explicit"
        else:
            folder, kind = FL.ledger_target()
        if kind == "ephemeral":
            return ("Logged: no — a cloud session outside any repository keeps no ledger; run from inside the working repository, "
                    "pass --to, or name the ledger sheet in the owner profile")
        before = FL.read_ledger(folder) if os.path.isdir(folder) else []
        if kind == "repo" or a.split:
            _still_open(FL.read_csv(run_file(folder, run)), run)
            path = FL.write_run_file(rows, folder, run, a.project)
            line = f"Logged: {len(rows)} rows → {os.path.relpath(path)} (run {run}); commit and push it with this session's work"
        else:
            path = os.path.join(folder, "LEDGER.csv")
            if not os.path.exists(path):
                FL.init_folder(folder)
            old = FL.read_csv(path)
            mine = [r for r in old if r.get("run") == run and FL.in_outcome_set(r)]
            _still_open(mine, run)
            if mine:
                FL.write_csv(path, [r for r in old if r not in mine], FL.LEDGER_COLUMNS)
            FL.append_run(rows, path, run, a.project)
            line = f"Logged: {len(rows)} rows → {path} (run {run})"
        rec = record_line([r for r in before if r.get("run") != run])
        return line + (f"\n{rec}" if rec else "")
    except (OSError, ValueError) as e:
        return f"Logged: no — {e}"


def to_run_file(rows: List[dict], path: str) -> str:
    """Levels 4-6: put the set in the run's FORECASTS.csv, replacing an earlier copy of the same set."""
    keep = [r for r in FL.read_csv(path) if not (FL.in_outcome_set(r) and r.get("group") == rows[0]["group"])]
    FL.write_csv(path, keep + rows, FL.COLUMNS)
    return f"Logged: {len(rows)} rows → {path}; forecast_ledger.py --check and --append carry them to the shared ledger"


def _glue(argv: Sequence[str]) -> List[str]:
    """'--cuts -0.15,0.1' -> '--cuts=-0.15,0.1': argparse would read a value that starts with a minus as an option."""
    out, i = [], 0
    while i < len(argv):
        if argv[i] in ("--q", "--cuts", "--dist") and i + 1 < len(argv) and re.match(r"^-[\d.]", argv[i + 1]):
            out.append(f"{argv[i]}={argv[i + 1]}"); i += 2
        else:
            out.append(argv[i]); i += 1
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=OC.__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for flag in ("--decision", "--call", "--by", "--made", "--range", "--base", "--base-class", "--reason", "--why", "--high", "--low",
                 "--source", "--cutoff", "--how", "--forecaster", "--rows", "--to", "--run", "--q", "--cuts", "--dist", "--all-of"):
        ap.add_argument(flag)
    ap.add_argument("--level", type=int, default=1); ap.add_argument("--project", default="")
    ap.add_argument("--outcome", action="append"); ap.add_argument("--option", action="append"); ap.add_argument("--sets", nargs="+")
    ap.add_argument("--other", type=float); ap.add_argument("--base-rate", type=float); ap.add_argument("--df", type=float, default=4.0)
    for flag in ("--log", "--tsv", "--split", "--compact", "--fact", "--bins"):
        ap.add_argument(flag, action="store_true")
    a = ap.parse_args(_glue(sys.argv[1:] if argv is None else list(argv)))
    num = lambda s: [float(x) for x in s.split(",")]  # noqa: E731
    if a.all_of:
        ind, linked = all_of(num(a.all_of))
        print(f"All of {a.all_of}: {ind:.0%} if the parts are independent, {linked:.0%} if one cause decides them all. Use the pair as the "
              "range and place the number by how much the parts share a cause.")
        return 0
    if a.bins:
        if not a.cuts or not (a.q or a.dist):
            ap.error("--bins needs --cuts and either --q (five quantiles) or --dist mean,sd[,df]")
        cuts = num(a.cuts)
        if a.q:
            q = num(a.q)
            if len(q) != 5 or any(x > y for x, y in zip(q, q[1:])) or cuts != sorted(cuts):
                ap.error("--q is q05,q25,q50,q75,q95 in rising order, and --cuts rise too")
            masses, (f25, f75) = bins_from_quantiles(q, cuts, a.df)
            half = max(q[4] - q[0], 1e-12) / 2
            note = f"fit check (two-piece t, df {a.df:g}): q25 given {q[1]:g}, fitted {f25:.3g}; q75 given {q[3]:g}, fitted {f75:.3g}"
            note += "; the fit misses a quartile by more than a tenth of the 5-95 half-width: read the buckets as rough" if max(abs(f25 - q[1]), abs(f75 - q[3])) > 0.1 * half else ""
        else:
            d = num(a.dist)
            masses, note = bins_from_dist(d[0], d[1], d[2] if len(d) > 2 else a.df, cuts), f"scaled t, mean {d[0]:g}, sd {d[1]:g}"
        print(" · ".join(f"{lab}: {p}%" for lab, p in zip(bucket_labels(cuts), round_to_100(masses))))
        print(note)
        return 0
    if not a.outcome:
        ap.error("give the --outcome rows, or --all-of, or --bins (outcomes.py with no arguments runs the smoke test)")
    s, errs, chk = build(a)
    if errs:
        print("\n".join(f"error: {e}" for e in errs), file=sys.stderr)
        return 2
    rows = ledger_rows(s)
    logged = ""
    if a.log or a.rows or a.tsv:
        probs = FL.check_run(rows)
        if probs:
            print("\n".join(f"error: {p}" for p in probs), file=sys.stderr)
            return 2
        logged = to_run_file(rows, a.rows) if a.rows else (log(s, rows, a) if a.log else "Logged: rows below, for the ledger sheet")
    logged, _, record = logged.partition("\n")
    print(render(s, logged, a.compact))
    for line in ([record] if record else []) + [f"Check: {c}" for c in chk]:  # not part of the block: relayed or answered by the pass
        print(line)
    if a.tsv:
        print("\n" + FL.sheet_rows(rows, a.run or f"{s['decision']}-{s['made']}-L{s['level']}", a.project), end="")
    return 0


def _smoke() -> None:
    import contextlib
    import io
    import tempfile
    ns, three = OC._ns, OC.THREE

    def cli(args: List[str]) -> tuple:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()
    s, errs, _ = build(ns(outcome=three, range="40-70", base="3/6", base_class="in-house launches 2024-26", high="h", low="l", log=True))
    rows = ledger_rows(s)
    assert errs == [] and FL.check_run(rows) == []
    with tempfile.TemporaryDirectory() as d:
        a = ns(outcome=three, range="40-70", high="h", low="l", log=True, to=d)
        line = log(s, rows, a)
        assert line.startswith("Logged: 4 rows → ") and len(FL.read_ledger(d)) == 4
        assert len(FL.read_ledger(d)) == 4 and log(s, rows, a).startswith("Logged: 4 rows"), "the same run logged twice replaces itself"
        led = os.path.join(d, "LEDGER.csv"); old = FL.read_csv(led)
        FL.write_csv(led, old + [dict(old[0], run="older", id="P1", group="", resolve_date="2020-01-01")], FL.LEDGER_COLUMNS)
        assert "1 open rows are past their date (oldest 2020-01-01)" in log(s, rows, ns(outcome=three, to=d, run="another"))
        done = [dict(r, status="resolved", outcome=("1" if r["id"] == "O1" else "0")) for r in FL.read_csv(led) if r["run"] == "another"]
        FL.write_csv(led, [r for r in FL.read_csv(led) if r["run"] != "another"] + done, FL.LEDGER_COLUMNS)
        assert "never edited" in log(s, rows, ns(outcome=three, to=d, run="another")), "a resolved run is not overwritten"
        split = log(s, rows, ns(outcome=three, to=os.path.join(d, "repo-ledger"), split=True))
        assert "runs" in split and "commit and push" in split and len(FL.read_ledger(os.path.join(d, "repo-ledger"))) == 4
        f = os.path.join(d, "FORECASTS.csv")
        assert to_run_file(rows, f).startswith("Logged: 4 rows") and to_run_file(rows, f) and len(FL.read_csv(f)) == 4 and FL.check_run(FL.read_csv(f)) == []
        many = [dict(r, run=f"r{i}", status="resolved", outcome=("1" if r["id"] == ("O1" if i % 2 else "O3") else "0")) for i in range(16) for r in rows]
        rec = record_line(many, today="2026-11-27")
        assert rec and "16 outcome sets resolved" in rec and "headline yes-lean +0.05" in rec and record_line(rows, today="2026-11-27") is None
        assert "56% if the parts are independent, 70% if one cause" in cli(["--all-of", "0.8,0.7"])[1]
        assert cli(["--bins", "--q", "-0.25,-0.08,0,0.08,0.25", "--cuts", "-0.15,0.1"])[1].startswith("below -0.15: 14% · -0.15 to 0.1: 64% · above 0.1: 22%")
        argv = ["--decision", "pilot", "--call", "Pilot first", "--by", "2027-03-31", "--made", "2026-11-27", "--high", "h", "--low", "l"]
        code, out, _ = cli(argv + [x for o in three for x in ("--outcome", o)] + ["--log", "--to", os.path.join(d, "cli")])
        assert code == 0 and "- **55%** Works: 20+ qualified leads a month\n" in out and "\n\nBasis: judgment; no base rate found" in out
        assert "\nLogged: 4 rows → " in out and "\nCheck: give the headline row its range" in out, out
        code, _, err = cli(argv + ["--outcome", "Works: x=97", "--outcome", "Fails: y=3", "--other", "0", "--log", "--to", os.path.join(d, "cli")])
        assert code == 2 and "at least 5% for what is not listed" in err and len(FL.read_ledger(os.path.join(d, "cli"))) == 4, "a refused set logs nothing"
        code, out, _ = cli(argv + [x for o in three for x in ("--outcome", o)] + ["--compact", "--tsv", "--range", "40-70"])
        assert code == 0 and out.startswith("**Outcomes** by 31 Mar 2027: works 55% (40–70) · partly 25%") and "\nrun\tproject\tid\t" in out
    print("outcomes_log smoke test: ok (logging with replace, split run files, the run's FORECASTS.csv, the record line, a resolved "
          "run left alone, the command line end to end, a refused set logs nothing)")


if __name__ == "__main__":
    _smoke() if len(sys.argv) <= 1 else sys.exit(main())
