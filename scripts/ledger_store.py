"""Where the stress-test skill's forecast ledger lives and how its files are read and written: the columns, the shared
folder for the surface a run is on, one file per run in a repository's ledger/ folder, the merged read, and the reading of
outcome sets (references/forecast.md section 9; references/outcomes.md). Standard library only. forecast_ledger.py (check,
score, append, calibrate, the command line) and outcomes_log.py import this file.

    python3 ledger_store.py            # smoke test
"""
from __future__ import annotations

import csv
import glob
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

COLUMNS = ["id", "decision", "made", "kind", "question", "criterion", "source", "resolve_date", "p",
           "q05", "q25", "q50", "q75", "q95", "range_low", "range_high", "forecaster", "method",
           "base_rate", "base_class", "base_n", "group", "node", "cluster", "ref_value", "model_cutoff", "status", "outcome",
           "score", "score_kind", "resolved_on", "notes"]
LEDGER_COLUMNS = ["run", "project"] + COLUMNS
LAPTOP_LEDGER_DIR = os.path.join("~", ".claude", "sessions", "stress-test-forecasts")
OUTCOME_GROUP = ":outcomes"   # suffix of the group that the rows of one Outcomes block share (references/outcomes.md)
EPHEMERAL_NOTE = ("this folder is inside a cloud container and will not outlive the session: run from inside the working "
                  "repository, pass --to, or set STRESS_TEST_LEDGER")


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


def num(x) -> Optional[float]:
    try:
        return float(x) if x not in ("", None) else None
    except ValueError:
        return None


def find_repo_root(start: str) -> Optional[str]:
    """The nearest folder at or above `start` that holds a .git entry, or None."""
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def ledger_target(explicit: Optional[str] = None, env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> Tuple[str, str]:
    """(folder, kind) of the shared ledger. In order: the explicit path (`explicit`); $STRESS_TEST_LEDGER (`env`); a ledger/
    folder in the working folder or at the top of its repository (`repo`: committed with the run, one file per run); in a
    cloud session (CLAUDE_CODE_REMOTE=true) the repository's ledger/ even before it exists (`repo`), or, outside any
    repository, the home folder marked `ephemeral` because the container is discarded; else the laptop folder (`home`)."""
    env = os.environ if env is None else env
    cwd = cwd or os.getcwd()
    if explicit:
        return os.path.expanduser(explicit), "explicit"
    if env.get("STRESS_TEST_LEDGER"):
        return os.path.expanduser(env["STRESS_TEST_LEDGER"]), "env"
    root = find_repo_root(cwd)
    for base in (cwd, root):
        if base and os.path.isdir(os.path.join(base, "ledger")):
            return os.path.abspath(os.path.join(base, "ledger")), "repo"
    if str(env.get("CLAUDE_CODE_REMOTE", "")).lower() == "true":
        return (os.path.join(root, "ledger"), "repo") if root else (os.path.expanduser(LAPTOP_LEDGER_DIR), "ephemeral")
    return os.path.expanduser(LAPTOP_LEDGER_DIR), "home"


def resolve_ledger_dir(explicit: Optional[str] = None, env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> str:
    """The shared ledger folder (see ledger_target for the order and the kinds)."""
    return ledger_target(explicit, env, cwd)[0]


def run_file(folder: str, run_id: str) -> str:
    return os.path.join(folder, "runs", re.sub(r"[^A-Za-z0-9._-]+", "-", run_id).strip("-") + ".csv")


def write_run_file(run_rows: Sequence[dict], folder: str, run_id: str, project: str) -> str:
    """Write one run's rows as their own file, <folder>/runs/<run>.csv, in the ledger's columns. Used where the ledger is a
    repository folder, so that sessions on different branches never append to the same file. Returns the path."""
    os.makedirs(os.path.join(folder, "runs"), exist_ok=True)
    path = run_file(folder, run_id)
    write_csv(path, [{"run": run_id, "project": project, **r} for r in run_rows], LEDGER_COLUMNS)
    return path


def read_ledger(path: str) -> List[dict]:
    """Every row of a shared ledger: LEDGER.csv and each file under runs/ beside it. `path` is the folder or the LEDGER.csv
    in it. A row met twice (same run and id) is kept once, the resolved copy winning over an open one."""
    folder = path if os.path.isdir(path) else (os.path.dirname(path) or ".")
    main = os.path.join(folder, "LEDGER.csv") if os.path.isdir(path) else path
    out: Dict[Tuple[str, str], dict] = {}
    for f in [main] + sorted(glob.glob(os.path.join(folder, "runs", "*.csv"))):
        for r in read_csv(f):
            key = (r.get("run") or "", r.get("id") or "")
            if key not in out or (out[key].get("status") == "open" and r.get("status") != "open"):
                out[key] = r
    return list(out.values())


def in_outcome_set(r: dict) -> bool:
    return (r.get("group") or "").endswith(OUTCOME_GROUP)


def is_headline(r: dict) -> bool:
    """False only for the non-headline rows of an outcome set. A set's rows sum to one and so do their outcomes, so pooled
    with other rows they pull the yes-lean to zero and the mean Brier under any binary reference; the set is scored whole."""
    return not in_outcome_set(r) or r.get("id") == "O1"


def outcome_sets(ledger: Sequence[dict]) -> List[dict]:
    """One entry per fully resolved outcome set: the probability it gave what happened, its multi-category Brier score,
    the even-split score for a set of its size, and the not-listed row's probability and outcome."""
    sets: Dict[Tuple[str, str], List[dict]] = {}
    for r in ledger:
        if in_outcome_set(r) and r.get("status") != "void":
            sets.setdefault((r.get("run") or r.get("decision") or "", r["group"]), []).append(r)
    out = []
    for (_, g), rs in sets.items():
        ps, ys = [num(r.get("p")) for r in rs], [num(r.get("outcome")) for r in rs]
        if any(r.get("status") != "resolved" for r in rs) or None in ps or None in ys or abs(sum(ys) - 1.0) > 1e-9:
            continue
        other = next(((p, y) for r, p, y in zip(rs, ps, ys) if r.get("id") == "OX"), None)
        out.append(dict(group=g, k=len(rs), p_realized=sum(p * y for p, y in zip(ps, ys)), brier=sum((p - y) ** 2 for p, y in zip(ps, ys)),
                        even=1.0 - 1.0 / len(rs), other=other))
    return out


def _smoke() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        # the shared folder resolves in order: explicit, environment, ledger/ here or at the repository top, cloud, the laptop folder
        home = os.path.expanduser(LAPTOP_LEDGER_DIR)
        assert resolve_ledger_dir("/x/y", env={"STRESS_TEST_LEDGER": "/z"}, cwd=d) == "/x/y"
        assert ledger_target(None, env={"STRESS_TEST_LEDGER": "/z"}, cwd=d) == ("/z", "env")
        assert ledger_target(None, env={}, cwd=d) == (home, "home")
        assert ledger_target(None, env={"CLAUDE_CODE_REMOTE": "true"}, cwd=d) == (home, "ephemeral"), "a cloud session outside any repository"
        os.makedirs(os.path.join(d, "repo", ".git")); os.makedirs(os.path.join(d, "repo", "sub"))
        sub, rl = os.path.join(d, "repo", "sub"), os.path.join(d, "repo", "ledger")
        assert ledger_target(None, env={}, cwd=sub)[1] == "home", "on the laptop a repository with no ledger/ changes nothing"
        assert ledger_target(None, env={"CLAUDE_CODE_REMOTE": "true"}, cwd=sub) == (rl, "repo"), "a cloud session uses the repository's ledger/"
        os.makedirs(os.path.join(d, "ledger"))
        assert ledger_target(None, env={}, cwd=d) == (os.path.abspath(os.path.join(d, "ledger")), "repo")
        os.makedirs(rl)
        assert ledger_target(None, env={}, cwd=sub) == (os.path.abspath(rl), "repo"), "ledger/ at the repository top is found from a subfolder"
        # one file per run; the merged read keeps the resolved copy of a row met twice
        rows = [dict(id=i, decision="demo", kind="event", p=p, group="demo:outcomes", status="open")
                for i, p in (("O1", "0.55"), ("O2", "0.25"), ("O3", "0.15"), ("OX", "0.05"))]
        path = write_run_file(rows, rl, "demo 2026/10/18 L1", "proj")
        assert os.path.basename(path) == "demo-2026-10-18-L1.csv" and len(read_ledger(rl)) == 4 and outcome_sets(read_ledger(rl)) == []
        done = [dict(r, run="demo 2026/10/18 L1", status="resolved", outcome=("1" if r["id"] == "O2" else "0")) for r in rows]
        write_csv(os.path.join(rl, "LEDGER.csv"), done + [dict(run="r2", id="P1", kind="event", p="0.6", status="open")], LEDGER_COLUMNS)
        merged = read_ledger(os.path.join(rl, "LEDGER.csv"))
        assert len(merged) == 5 and sum(r["status"] == "resolved" for r in merged) == 4
        s = outcome_sets(merged)[0]
        assert abs(s["p_realized"] - 0.25) < 1e-9 and abs(s["brier"] - (0.55 ** 2 + 0.75 ** 2 + 0.15 ** 2 + 0.05 ** 2)) < 1e-9
        assert s["other"] == (0.05, 0.0) and s["even"] == 0.75 and s["k"] == 4
        assert [is_headline(r) for r in merged if r["id"] in ("O1", "O2", "P1")] == [True, False, True]
    print("ledger_store smoke test: ok (folder order and kinds, repository top, run files, merged read, outcome sets, headline rows)")


if __name__ == "__main__":
    _smoke()
