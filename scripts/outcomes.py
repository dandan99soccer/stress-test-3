"""Outcome percentages for the stress-test skill (references/outcomes.md): the Outcomes block every level prints under its
call, checked and rounded to 100 here, logged to the forecast ledger by outcomes_log.py, which also holds the command line
and which this file hands off to. Standard library only; the t fit is student_t.py in this folder.

    python3 outcomes.py                                   # smoke test
    python3 outcomes.py --decision <slug> --level <N> --call "<the call, in a few words>" --by <YYYY-MM-DD> \
        --outcome "Works: <success line>=<n>" --outcome "Partly: <between>=<n>" --outcome "Fails: <abandon line>=<n>" \
        --range <low>-<high> --base <k>/<n> --base-class "<named class>" --option "<other option>=<n>" --option "Do nothing=<n>" \
        --high "<why it may be too high>" --low "<why too low>" --source "<where it is read>" --log
    (no sample numbers here on purpose: a sample number becomes the pass's anchor)
    ... --sets "<set 1>" "<set 2>" "<set 3>"               # several blind sets in place of numbers on the rows: the median
                                                           # set, with the spread across the sets as each row's range
    ... --rows FORECASTS.csv                               # levels 4-6: put the rows in the run's file instead of --log
    ... --tsv                                              # print the ledger rows tab-separated, for a connected sheet
    ... --not-logged "chat keeps no files"                 # no ledger in reach: the Logged line says why
    ... --exhaustive                                       # the rows are cuts of one measured number: no Not listed row
    python3 outcomes.py --all-of 0.8,0.7,0.9               # a plan that needs every part: independent .. fully linked
    python3 outcomes.py --bins --q -0.25,-0.08,0.01,0.09,0.26 --cuts -0.15,0.10   # a quantile forecast as bucket percentages
    python3 outcomes.py --bins --dist 0.02,0.24,4 --cuts -0.15,0.10               # the same from a mean, an sd and t df

The first --outcome is the headline row (for a recommendation, the success line); the rest of 100 goes to "Not listed"
unless --other gives it. Refused, with nothing logged: rows that do not add to 100, a row under 5% or over 95% with no
--base-class behind it, less than 5% left for Not listed, a range that does not hold its number, a missing date. Printed as `Check:` lines for the pass to
answer or fix: a near-even split, a headline number outside its base rate's interval with no --reason, another option
with odds at least as good as the call's and no --why, a missing range or missing too-high and too-low reasons.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import statistics
import sys
from datetime import date
from typing import List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forecast_tools import wilson  # noqa: E402
from ledger_store import OUTCOME_GROUP  # noqa: E402
from student_t import Dist, t_cdf, t_quantile  # noqa: E402

OTHER_TEXT = "overtaken, dropped, unreadable, or something nobody named"
FLOOR, CEIL = 5, 95


def parse_row(s: str) -> Tuple[str, str, Optional[float]]:
    """'Label: text=55' -> (label, text, 55.0); the number and the text are optional."""
    body, pct = s.strip(), None
    m = re.search(r"=\s*(\d+(?:\.\d+)?)\s*%?\s*$", body)
    if m:
        pct, body = float(m.group(1)), body[:m.start()].strip()
    label, sep, text = body.partition(":")
    return (label.strip(), text.strip(), pct) if sep else (body, "", pct)


def round_to_100(vals: Sequence[float]) -> List[int]:
    """Whole percentages that add to exactly 100, by largest remainder."""
    tot = float(sum(vals))
    if tot <= 0:
        raise ValueError("nothing to round")
    raw = [v * 100.0 / tot for v in vals]
    out = [int(math.floor(x + 1e-9)) for x in raw]
    for i in sorted(range(len(raw)), key=lambda j: raw[j] - out[j], reverse=True)[:100 - sum(out)]:
        out[i] += 1
    return out


def median_set(sets: Sequence[Sequence[float]]) -> Tuple[List[int], List[Tuple[float, float]]]:
    """Several sets for the same rows -> the median set (rounded to 100) and each row's lowest and highest number."""
    cols = list(zip(*sets))
    return round_to_100([statistics.median(c) for c in cols]), [(min(c), max(c)) for c in cols]


def all_of(ps: Sequence[float]) -> Tuple[float, float]:
    """A plan that needs every part to hold: the product when the parts are independent, the smallest when one cause
    decides them all. Parts that tend to hold or fail together sit between the two."""
    ps = [p / 100.0 if p > 1 else p for p in ps]
    return math.prod(ps), min(ps)


def bins_from_quantiles(q: Sequence[float], cuts: Sequence[float], df: float = 4.0):
    """Mass between cut points of a two-piece scaled t fitted through q05, q50 and q95 (a parametric fit, never linear
    interpolation between the levels: references/forecast.md section 6). Returns the masses and the fitted q25 and q75."""
    q05, _, q50, _, q95 = q
    t95 = t_quantile(0.95, df)
    sl, sr = (q50 - q05) / t95, (q95 - q50) / t95

    def cdf(x: float) -> float:
        s = sl if x < q50 else sr
        return t_cdf((x - q50) / s, df) if s > 0 else float(x >= q50)
    edges = [cdf(c) for c in cuts]
    return [b - a for a, b in zip([0.0] + edges, edges + [1.0])], (q50 + sl * t_quantile(0.25, df), q50 + sr * t_quantile(0.75, df))


def bins_from_dist(mean: float, sd: float, df: float, cuts: Sequence[float]) -> List[float]:
    d = Dist(mean, sd, df)
    edges = [d.cdf(c) for c in cuts]
    return [b - a for a, b in zip([0.0] + edges, edges + [1.0])]


def bucket_labels(cuts: Sequence[float]) -> List[str]:
    return [f"below {cuts[0]:g}"] + [f"{a:g} to {b:g}" for a, b in zip(cuts, cuts[1:])] + [f"above {cuts[-1]:g}"]


def fmt_day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')} {d.year}"


def build(a) -> Tuple[Optional[dict], List[str], List[str]]:
    """Arguments -> (the set, errors, checks). A set with errors is never printed or logged."""
    errs, chk = [], []
    named = [parse_row(s) for s in a.outcome or []]
    if len(named) < 2:
        errs.append("give at least two --outcome rows; the first is the headline row")
    if len({n[0].lower() for n in named}) != len(named):
        errs.append("each --outcome needs its own label")
    if not 1 <= int(a.level) <= 6:
        errs.append("--level is 1 to 6")
    if not a.call:
        errs.append("--call names the call the rows belong to (with --fact, the check whose answers they are)")
    made = a.made or date.today().isoformat()
    try:
        if not a.by or date.fromisoformat(a.by) < date.fromisoformat(made):
            errs.append("--by is the date the rows are read on (YYYY-MM-DD), on or after the day the set is made")
    except ValueError:
        errs.append("--by and --made are dates as YYYY-MM-DD")
    spread: List[Optional[Tuple[float, float]]] = [None] * (len(named) + 1)
    if a.exhaustive and (a.sets or a.other):
        errs.append("--exhaustive rows are cuts of one measured number and add to 100 on their own: no --sets, no --other")
    if a.sets:
        if any(n[2] is not None for n in named):
            errs.append("give the numbers on the rows or as --sets, not both")
        try:
            sets = [[float(x) for x in s.replace("%", "").split(",") if x.strip()] for s in a.sets]
        except ValueError:
            sets = [[]]
        sets = [s + [100.0 - sum(s)] if len(s) == len(named) else s for s in sets]
        if any(len(s) != len(named) + 1 or min(s) < 0 or abs(sum(s) - 100) > 0.5 for s in sets):
            errs.append("each of --sets has one number per --outcome row (plus, optionally, the not-listed share) and adds to 100")
            pcts = [0] * (len(named) + 1)
        else:
            pcts, spread = median_set(sets)
    else:
        vals = [n[2] for n in named]
        if any(v is None for v in vals):
            errs.append("every --outcome needs its number: 'Label: text=<number>' (or pass --sets)")
            vals = [v or 0.0 for v in vals]
        other = 0.0 if a.exhaustive else (a.other if a.other is not None else 100.0 - sum(vals))
        if abs(sum(vals) + other - 100) > 0.5 or other < 0:
            errs.append(f"the rows add to {sum(vals) + max(other, 0):g}, not 100")
            pcts = [int(round(v)) for v in vals] + [int(round(max(other, 0)))]
        else:
            pcts = round_to_100(vals + [other])  # whole numbers that still add to exactly 100
    rows = [dict(id=f"O{i + 1}", label=n[0], text=n[1], pct=p, spread=sp) for i, (n, p, sp) in enumerate(zip(named, pcts, spread))]
    if not a.exhaustive:
        rows.append(dict(id="OX", label="Not listed", text=OTHER_TEXT, pct=pcts[-1], spread=spread[-1]))
    for r in rows:
        if r["id"] == "OX" and r["pct"] < FLOOR:
            errs.append(f"Not listed at {r['pct']}%: leave at least {FLOOR}% for what is not listed, whatever backs the other rows")
        elif not (FLOOR <= r["pct"] <= CEIL) and not a.base_class:
            errs.append(f"{r['label']} at {r['pct']}%: nothing under {FLOOR}% or over {CEIL}% without a named class behind it (--base-class)")
    head = rows[0]["pct"] if rows else 0
    base = None
    if a.base:
        m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", a.base)
        if not m or int(m.group(2)) == 0 or int(m.group(1)) > int(m.group(2)):
            errs.append("--base is the count that met the test over the cases, as k/n")
        else:
            k, n = int(m.group(1)), int(m.group(2))
            lo, hi = wilson(k, n)
            base = dict(k=k, n=n, rate=100.0 * k / n, lo=100 * lo, hi=100 * hi)
            if not (base["lo"] - 0.5 <= head <= base["hi"] + 0.5) and not a.reason:
                chk.append(f"{head}% sits outside the base rate's interval ({base['lo']:.0f}–{base['hi']:.0f}%): give the reason "
                           "this case differs (--reason) or move the number")
    elif a.base_rate is not None:
        base = dict(k=None, n=None, rate=float(a.base_rate), lo=None, hi=None)
        if abs(head - base["rate"]) > 15 and not a.reason:
            chk.append(f"{head}% is more than 15 points from the base rate ({base['rate']:g}%): give the reason (--reason) or move it")
    rng = None
    if a.range:
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*$", a.range)
        if not m or not float(m.group(1)) <= head <= float(m.group(2)):
            errs.append("--range is lowest-highest for the headline row, and holds its number")
        else:
            rng = (float(m.group(1)), float(m.group(2)))
    elif rows and rows[0]["spread"]:
        rng = (min(rows[0]["spread"][0], head), max(rows[0]["spread"][1], head))
    elif base and base["lo"] is not None:
        rng = (min(base["lo"], head), max(base["hi"], head))
    else:
        chk.append("give the headline row its range, the lowest and the highest plausible number written before the best one (--range lo-hi)")
    ps = [r["pct"] for r in rows if r["id"] != "OX"]
    if len(ps) >= 2 and max(ps) - min(ps) <= 10:
        chk.append("the named rows sit within 10 points of each other: an even split is what no information looks like; set each "
                   "from its base rate, or say that the record is silent")
    opts = [parse_row(o) for o in a.option or []]
    opts = [(l if not t else f"{l}: {t}", p) for l, t, p in opts]
    if any(p is None for _, p in opts):
        errs.append("every --option needs its number: 'Name=<number>'")
    better = [n for n, p in opts if p is not None and p >= head]
    if better and not a.why:
        chk.append(f"{', '.join(better)} has odds at least as good as the call's on this test: say what the call wins on (--why) or revisit the call")
    if not (a.high and a.low):
        (errs if (a.log or a.rows or a.tsv) else chk).append("give one reason the headline number may be too high (--high) and one it may be too low (--low)")
    if (a.log or a.rows or a.tsv) and not a.decision:
        errs.append("--decision names the decision the rows belong to")
    how = a.how or (f"median of {len(a.sets)} blind sets" if a.sets else "lead's judgment" + (", from the base rate" if base else ""))
    s = dict(rows=rows, head=head, rng=rng, base=base, opts=opts, made=made, by=a.by, call=a.call or "", level=int(a.level), how=how,
             decision=a.decision or "", source=a.source or "the owner, at the check date", fact=a.fact, base_class=a.base_class or "",
             reason=a.reason or "", why=(a.why or "") if better else "", high=a.high or "", low=a.low or "", cutoff=a.cutoff or "",
             forecaster=a.forecaster or ("aggregate" if a.sets else "lead"))
    return s, errs, chk


def basis_text(s: dict) -> str:
    b, cls = s["base"], s["base_class"]
    if b and b["n"]:
        txt = (f"{b['k']} of {b['n']} similar cases met the test ({cls + '; ' if cls else ''}90% interval {b['lo']:.0f}–{b['hi']:.0f}%"
               f"{', estimated' if b['n'] < 30 else ''})")
    elif b:
        txt = f"base rate {b['rate']:g}% ({cls + ', ' if cls else ''}estimated)"
    elif cls:
        txt = cls  # a named reference with no count of its own, such as a market-implied distribution
    else:
        txt = "judgment; no base rate found"
    if s["reason"]:
        txt += f"; set at {s['head']}% because {s['reason']}"
    return f"{txt}; level {s['level']}, {s['how']}"


def render(s: dict, logged: str = "", compact: bool = False) -> str:
    """The fixed block, pasted into the reply as printed."""
    rng = f" ({s['rng'][0]:.0f}–{s['rng'][1]:.0f})" if s["rng"] else ""
    opts = " · ".join(f"{n} {p:g}%" for n, p in s["opts"]) + (f" (the call wins on: {s['why']})" if s["why"] and s["opts"] else "")
    if compact:
        bits = [" · ".join(f"{r['label'].lower()} {r['pct']}%{rng if i == 0 else ''}" for i, r in enumerate(s["rows"]))]
        bits += [f"others on the same test: {opts}"] if opts else []
        bits += [f"basis: {basis_text(s)}"] + ([logged.replace("Logged:", "logged:").splitlines()[0]] if logged else [])
        return f"**Outcomes** by {fmt_day(s['by'])}: " + " | ".join(bits)
    head = (f"**Outcomes** — nothing decided yet; what the check will show ({s['call']}), by {fmt_day(s['by'])}" if s["fact"] else
            f"**Outcomes** — if the call is followed ({s['call']}), by {fmt_day(s['by'])}")
    L = [head] + [f"- **{r['pct']}%**{rng if i == 0 else ''} {r['label']}: {r['text']}" for i, r in enumerate(s["rows"])]
    L.append("")  # a blank line, or the lines below would be read as part of the last bullet
    if opts:
        L.append(f"Same test, other options: {opts}")
    L.append(f"Basis: {basis_text(s)}")
    return "\n".join(L + ([logged] if logged else []))


def ledger_rows(s: dict) -> List[dict]:
    """The set as event rows sharing one group, in the columns of references/forecast.md section 9. The group carries the
    decision, the day and the level, so two passes on one decision never share a group in the shared ledger."""
    b, alt = s["base"], "; ".join(f"{n} {p:g}" for n, p in s["opts"])
    out = []
    for i, r in enumerate(s["rows"]):
        p = r["pct"]
        lo, hi = (s["rng"] if i == 0 and s["rng"] else r["spread"] or (p - (15 if i == 0 else 10), p + (15 if i == 0 else 10)))
        lo, hi = max(0.0, min(lo, p)), min(100.0, max(hi, p))
        notes = "part of an outcome set; the reasons are on O1"
        if i == 0:
            notes = (f"too high: {s['high']}; too low: {s['low']}" + (f"; other options on the same test: {alt}" if alt else "")
                     + (f"; departs from the base rate because {s['reason']}" if s["reason"] else "")
                     + ("; estimated (base_n under 30)" if b and (b["n"] or 0) < 30 else ""))
        extreme = not (FLOOR <= p <= CEIL)
        frame = (f"what the check ({s['call']}) shows" if s["fact"] else f"if the call ({s['call']}) is followed")
        out.append(dict(id=r["id"], decision=s["decision"], made=s["made"], kind="event",
                        question=f"{r['label']}: {r['text']} — {frame}, by {s['by']}", criterion=r["text"] or r["label"],
                        source=s["source"], resolve_date=s["by"], p=f"{p / 100:.2f}", range_low=f"{lo / 100:.2f}", range_high=f"{hi / 100:.2f}",
                        forecaster=s["forecaster"], method=f"level {s['level']}: {s['how']}",
                        base_rate=(f"{b['rate'] / 100:.2f}" if b and i == 0 else ""), base_class=(s["base_class"] if (i == 0 and b) or extreme else ""),
                        base_n=(b["n"] if b and b["n"] and i == 0 else ""), group=f"{s['decision']}-{s['made']}-L{s['level']}{OUTCOME_GROUP}",
                        cluster=f"{s['made']}:{s['decision']}", model_cutoff=s["cutoff"], status="open", notes=notes))
    return out


def _ns(**k) -> argparse.Namespace:
    """Every argument of the command line at its default, for the smoke tests here and in outcomes_log.py."""
    return argparse.Namespace(**{**dict(decision="pilot", level=1, call="Pilot first", by="2027-03-31", made="2026-11-27", outcome=None, option=None,
                                        sets=None, other=None, range=None, base=None, base_rate=None, base_class=None, reason=None, why=None, high=None,
                                        low=None, source=None, cutoff="2026-06", how=None, forecaster=None, log=False, rows=None, tsv=False, to=None,
                                        run=None, project="demo", split=False, compact=False, fact=False, not_logged=None, exhaustive=False), **k})


THREE = ["Works: 20+ qualified leads a month=55", "Partly: leads up, under 20=25", "Fails: no lift, kill line hit=15"]


def _smoke() -> None:
    import forecast_ledger as FL
    assert parse_row("Works: 20+ leads a month=55") == ("Works", "20+ leads a month", 55.0)
    assert parse_row("Fails: CPA = $90 for two weeks = 15%") == ("Fails", "CPA = $90 for two weeks", 15.0) and parse_row("Do nothing=10")[::2] == ("Do nothing", 10.0)
    assert round_to_100([55, 25, 15, 5]) == [55, 25, 15, 5] and round_to_100([1, 1, 1]) == [34, 33, 33] and sum(round_to_100([52.5, 27.5, 13.3, 6.7])) == 100
    med, spr = median_set([[55, 25, 15, 5], [45, 30, 20, 5], [60, 25, 10, 5]])
    assert med == [55, 25, 15, 5] and spr[0] == (45, 60)
    ind, linked = all_of([0.8, 0.7, 0.9]); assert abs(ind - 0.504) < 1e-9 and linked == 0.7 and all_of([80, 70]) == (0.5599999999999999, 0.7)
    m, (f25, f75) = bins_from_quantiles([-0.25, -0.08, 0.0, 0.08, 0.25], [-0.25, 0.0, 0.25])
    assert abs(m[0] - 0.05) < 1e-6 and abs(m[1] - 0.45) < 1e-6 and abs(m[3] - 0.05) < 1e-6 and abs(sum(m) - 1) < 1e-9 and f25 < 0 < f75
    skew, _ = bins_from_quantiles([-0.10, -0.03, 0.0, 0.10, 0.40], [0.0, 0.40]); assert abs(skew[0] - 0.5) < 1e-9 and abs(skew[2] - 0.05) < 1e-6
    d = bins_from_dist(0.0, 1.0, 4, [0.0]); assert abs(d[0] - 0.5) < 1e-9 and bucket_labels([-1, 2]) == ["below -1", "-1 to 2", "above 2"]
    ns, three = _ns, THREE
    s, errs, chk = build(ns(outcome=three, range="40-70", base="3/6", base_class="in-house launches 2024-26", option=["Full launch now=40", "Do nothing=10"],
                            high="the pilot region is the best one", low="the list is warmer than last year", log=True))
    assert errs == [] and chk == [], (errs, chk)
    txt = render(s, "Logged: 4 rows → x")
    assert "- **55%** (40–70) Works: 20+ qualified leads a month" in txt and "- **5%** Not listed: " in txt and "3 of 6 similar cases met the test" in txt
    assert "Same test, other options: Full launch now 40% · Do nothing 10%" in txt and txt.splitlines()[0].endswith("by 31 Mar 2027") and "level 1, lead's judgment" in txt
    assert render(s, compact=True).startswith("**Outcomes** by 31 Mar 2027: works 55% (40–70) · partly 25% · fails 15% · not listed 5% | others")
    rows = ledger_rows(s)
    assert FL.check_run(rows) == [], FL.check_run(rows)
    assert [r["id"] for r in rows] == ["O1", "O2", "O3", "OX"] and rows[0]["group"] == "pilot-2026-11-27-L1:outcomes" and rows[0]["base_n"] == 6 and "estimated" in rows[0]["notes"]
    assert rows[0]["method"].startswith("level 1:") and "other options on the same test: Full launch now 40; Do nothing 10" in rows[0]["notes"]
    # refusals: a sum off 100, an extreme row with no class, no room for what is not listed, numbers given twice
    assert any("not 100" in e for e in build(ns(outcome=three, other=10.0))[1])
    assert any("without a named class" in e for e in build(ns(outcome=["Works: x=97", "Fails: y=3"], other=0.0))[1])
    assert any("at least 5%" in e for e in build(ns(outcome=["Works: x=60", "Fails: y=38"], base_class="a named class"))[1])
    assert build(ns(outcome=["Works: x=92", "Fails: y=3"], base_class="a named class", range="85-97", high="h", low="l"))[1] == []
    assert any("not both" in e for e in build(ns(outcome=three, sets=["55,25,15,5"]))[1])
    assert any("adds to 100" in e for e in build(ns(outcome=["Works: a", "Fails: b"], sets=["55,x,5"]))[1]) and any("--call" in e for e in build(ns(outcome=three, call=None))[1])
    assert [r["pct"] for r in build(ns(outcome=["Works: a=52.5", "Partly: b=27.5", "Fails: c=14.5"], other=5.5))[0]["rows"]] == [53, 28, 14, 5], "decimals are rounded so the rows still add to exactly 100"
    assert any("--high" in e for e in build(ns(outcome=three, log=True))[1]) and any("--high" in c for c in build(ns(outcome=three))[2])
    # --why is printed only when another option's odds match or beat the call's
    assert "wins on" not in render(build(ns(outcome=three, option=["Other=40"], why="cost", range="40-70", high="h", low="l"))[0])
    assert "Other 60% (the call wins on: cost)" in render(build(ns(outcome=three, option=["Other=60"], why="cost", range="40-70", high="h", low="l"))[0])
    # rows cut from one measured number (level 6): nothing is left unlisted, and they still add to 100
    s3, e3, _ = build(ns(outcome=["Bear: below -15%=19", "Base: -15% to +10%=48", "Bull: above +10%=33"], exhaustive=True, range="14-24", high="h", low="l"))
    assert e3 == [] and [r["id"] for r in s3["rows"]] == ["O1", "O2", "O3"] and "Not listed" not in render(s3) and FL.check_run(ledger_rows(s3)) == []
    assert basis_text(build(ns(outcome=three, base_class="market reference, t df 4", level=6, how="reference bins"))[0]) == "market reference, t df 4; level 6, reference bins"
    assert any("not 100" in e for e in build(ns(outcome=["Bear: x=19", "Bull: y=33"], exhaustive=True))[1])
    # checks: an even split, a number outside its base rate's interval, a better alternative, a missing range
    c = build(ns(outcome=["Works: x=35", "Partly: y=30", "Fails: z=30"], option=["Other plan=50"], base="1/20", high="h", low="l"))[2]
    assert any("even split" in x for x in c) and any("outside the base rate" in x for x in c) and any("Other plan has odds" in x for x in c)
    assert not any("outside the base rate" in x for x in build(ns(outcome=three, base="1/10", reason="the list is opt-in", high="h", low="l"))[2])
    assert any("--range" in x for x in build(ns(outcome=three, high="h", low="l"))[2])
    # several blind sets: the median set, and the spread as the headline range
    s2, e2, c2 = build(ns(outcome=["Works: a", "Partly: b", "Fails: c"], sets=["55,25,15,5", "45,30,20,5", "60,25,10"], level=2, high="h", low="l"))
    assert e2 == [] and s2["head"] == 55 and s2["rng"] == (45, 60) and s2["forecaster"] == "aggregate" and "median of 3 blind sets" in basis_text(s2)
    print("outcomes smoke test: ok (parsing, rounding to 100, median of sets, conjunction bounds, bins by t fit, the block and its "
          "compact form, refusals, checks, ledger rows pass forecast_ledger.check_run)")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        _smoke()
    else:
        from outcomes_log import main
        raise SystemExit(main())
