"""Reports for the propagation engine (propagate.py, stress-test-3): the markdown summary a packet quotes from, the
FORECASTS.csv rows in the ledger format of references/forecast.md, and the command line. Standard library only.

    py -3 propagate_report.py                               # smoke test (rows pass forecast_ledger.check_run)
    py -3 propagate.py GRAPH.json [--md SIM.md] [--json SIM.json] [--paths N] [--seed S] [--no-sens]
    py -3 propagate.py GRAPH.json --rows FORECASTS.csv --decision <slug> --made YYYY-MM-DD [--cutoff 2026-06]
        [--resolve-dates d1,d2 (one per horizon)] [--source "price panel"]

Rows carry forecaster "model" and method "simulation propagate.py <graph hash>"; the panel base rates graph_fit.py wrote go
in base_rate, base_class and base_n, and the range is the spread of the number across the sensitivity variants. The lead
fills the "too high because / too low because" notes before forecast_ledger.py --check.
"""
from __future__ import annotations

import argparse, csv, json, math, os, sys
from datetime import date, timedelta
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from propagate import DEMO, Graph, decision_stat, graph_hash, response, run, sensitivity, summarize, variance_shares  # noqa: E402

COLUMNS = ["id", "decision", "made", "kind", "question", "criterion", "source", "resolve_date", "p", "q05", "q25", "q50", "q75",
           "q95", "range_low", "range_high", "forecaster", "method", "base_rate", "base_class", "base_n", "group", "node",
           "cluster", "ref_value", "model_cutoff", "status", "outcome", "score", "score_kind", "resolved_on", "notes"]


def spread(alts: List[dict], h, key, sub=None):
    vals = [(a["horizons"][h][key] if sub is None else a["horizons"][h][key][sub]) if h else a[key][sub] for a in alts]
    return min(vals), max(vals)


def _approx(made: str, h: int) -> str:
    return (date.fromisoformat(made) + timedelta(days=math.ceil(h * 7 / 5))).isoformat()


def ledger_rows(g: Graph, summ: dict, alts: List[dict], a, hsh: str) -> List[dict]:
    pbr, made, rows = g.spec.get("panel_base_rates", {}), a.made, []
    rd = dict(zip(map(str, g.horizons), a.resolve_dates.split(","))) if a.resolve_dates else {}
    base = dict(decision=a.decision, made=made, source=a.source, forecaster="model", method=f"simulation propagate.py {hsh}",
                model_cutoff=a.cutoff or "", status="open", group="", node="", ref_value="")
    note = "simulation; too high because: <fill>; too low because: <fill>"
    approx = "; resolve date approximated from trading days, confirm on the exchange calendar"
    for h in g.horizons:
        S = summ["horizons"][h]; br = pbr.get(str(h), {}); d = rd.get(str(h)); dn = "" if d else approx; d = d or _approx(made, h)
        lo, hi = spread(alts, h, "p_beats"); n_ind = br.get("independent_n")
        est = "; estimated (base_n under 30)" if br and (n_ind or 0) < 30 else ""
        rows.append(dict(base, id=f"S{h}-beats", kind="event", question=f"{g.subject} beats {g.bench} over {h} trading days from {made}",
                         criterion=f"simple return of {g.subject} minus {g.bench}, close of {made} to the close {h} trading days later, > 0",
                         resolve_date=d, p=f"{S['p_beats']:.4f}", range_low=f"{min(lo, S['p_beats']):.4f}", range_high=f"{max(hi, S['p_beats']):.4f}",
                         base_rate=br.get("p_beats", ""), base_class=br.get("class", "") if br else "", base_n=n_ind or "",
                         cluster=f"{made}:{g.subject}:{h}", notes=note + est + dn))
        q = S["excess"]; lo, hi = spread(alts, h, "excess", "q50")
        rows.append(dict(base, id=f"S{h}-excess", kind="quantity", question=f"{g.subject} minus {g.bench}, simple return, {h} trading days from {made}",
                         criterion="difference of simple returns at the horizon close", resolve_date=d, range_low=f"{lo:.4f}", range_high=f"{hi:.4f}",
                         cluster=f"{made}:{g.subject}:{h}", notes=note + dn, **{k: f"{v:.4f}" for k, v in q.items()}))
    H = g.H; dh = rd.get(str(H)) or _approx(made, H); top = pbr.get(str(H), {}); brd, n_dd = top.get("dd_worse", {}), top.get("dd_independent_n")
    for x, p in summ["p_dd_worse"].items():
        lo, hi = spread(alts, None, "p_dd_worse", x); known = brd.get(x) is not None
        est = "; estimated (base_n under 30)" if known and (n_dd or 0) < 30 else ""
        rows.append(dict(base, id=f"SDD{int(round(float(x) * 100))}", kind="event", resolve_date=dh, p=f"{p:.4f}",
                         question=f"{g.subject} closes more than {float(x):.0%} below its {made} close within {H} trading days",
                         criterion=f"lowest close of {g.subject} in the window divided by the {made} close, minus one, < -{x}",
                         range_low=f"{min(lo, p):.4f}", range_high=f"{max(hi, p):.4f}", base_rate=brd.get(x, ""),
                         base_class=top.get("class", "") if known else "", base_n=n_dd or "", cluster=f"{made}:{g.subject}:{H}", notes=note + est))
    return rows


def render(g: Graph, hsh: str, paths: int, seed: int, summ: dict, shares, resp, scen: list, sens: list, dec, base_stat) -> str:
    k, n = sum(1 for _, m in g.links() if not m.startswith("measured")), len(g.links())
    L = [f"# Simulation: {g.subject} vs {g.bench}, graph {hsh}, {paths} paths, seed {seed}",
         f"Links: {n} ({n - k} measured, {k} estimated or assumed), made-up share {k / n:.0%}" if n else "Links: none",
         f"Shocks: {'block bootstrap of ' + g.spec['residuals'] if g.resid else 't draws'}; stress regime p = {float((g.regime or {}).get('p', 0)):.2f}", "",
         "## Base run", "| horizon | subject q05 / q50 / q95 | excess q05 / q25 / q50 / q75 / q95 | P(beats) | CVaR10 excess |", "|---|---|---|---|---|"]
    for h, S in summ["horizons"].items():
        s, e = S["subject"], S["excess"]
        L.append(f"| {h} | {s['q05']:+.1%} / {s['q50']:+.1%} / {s['q95']:+.1%} | {e['q05']:+.1%} / {e['q25']:+.1%} / {e['q50']:+.1%} / {e['q75']:+.1%} / {e['q95']:+.1%} | {S['p_beats']:.2f} | {S['cvar10_excess']:+.1%} |")
    L.append(f"P(close more than x below start within {g.H} days): " + ", ".join(f"{float(x):.0%}: {p:.3f}" for x, p in summ["p_dd_worse"].items()))
    if dec:
        L.append(f"Decision statistic {dec['stat']} (threshold {dec.get('threshold', 0)}, horizon {dec.get('horizon', g.H)}): **{base_stat:.3f}**, flip at {dec.get('flip_at', 'n/a')}")
    L += ["", f"## Where {g.subject}'s variance comes from (calm regime, analytic)", f"| source | share | cumulative response at {g.H} days to a unit own shock |", "|---|---|---|"]
    L += [f"| {s} | {v:.1%} | {resp[s]:+.3f} |" for s, v in sorted(shares.items(), key=lambda kv: -kv[1])]
    if scen:
        x0 = list(summ["p_dd_worse"])[0]
        L += ["", "## Scenarios: cause and effect", f"| scenario | effect on {g.subject} by horizon | effect on {g.bench} | P(beats) | excess q50 | P(worse than {float(x0):.0%} drawdown) |", "|---|---|---|---|---|---|"]
        for s in scen:
            r, S, H = s["response"], s["summary"], g.H; hs = " / ".join(f"{h}d {r[g.subject][h]:+.1%}" for h in g.horizons)
            L.append(f"| {s['name']} | {hs} | {r[g.bench][H]:+.1%} | {S['horizons'][H]['p_beats']:.2f} | {S['horizons'][H]['excess']['q50']:+.1%} | {S['p_dd_worse'][x0]:.3f} |")
    if sens:
        L += ["", "## Sensitivity of the decision statistic to each link's range", "| link | mark | range | at low | at high | swing | crosses flip |", "|---|---|---|---|---|---|---|"]
        L += [f"| {r['link']} | {r['mark']} | {r['range'][0]}..{r['range'][1]} | {r['stat_low']:.3f} | {r['stat_high']:.3f} | {r['swing']:.3f} | {'yes' if r.get('crosses_flip') else 'no'} |" for r in sens]
        q = [r["link"] for r in sens if r.get("crosses_flip")]
        L.append("Research questions (the range crosses the flip): " + ("; ".join(q) if q else "none; the call holds across every link's range."))
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("graph"); ap.add_argument("--md"); ap.add_argument("--json"); ap.add_argument("--paths", type=int)
    ap.add_argument("--seed", type=int); ap.add_argument("--no-sens", action="store_true"); ap.add_argument("--rows")
    ap.add_argument("--decision", default=""); ap.add_argument("--made"); ap.add_argument("--cutoff"); ap.add_argument("--resolve-dates")
    ap.add_argument("--source", default="price panel")
    a = ap.parse_args(argv)
    with open(a.graph, encoding="utf-8") as fh:
        spec = json.load(fh)
    g = Graph(spec); paths = a.paths or int(spec.get("paths", 2000)); seed = a.seed if a.seed is not None else int(spec.get("seed", 7))
    hsh, dec = graph_hash(spec), spec.get("decision")
    res, dd = run(g, paths, seed); summ = summarize(g, res, dd); base_stat = decision_stat(g, res, dd, dec) if dec else None
    shares, _, resp = variance_shares(g)
    scen = [{"name": s["name"], "response": response(g, s), "summary": summarize(g, *run(g, paths, seed, s))} for s in spec.get("scenarios", [])]
    sens, alts = ([], [summ]) if a.no_sens else sensitivity(g, max(500, paths // 2), seed, dec, base_stat, summ)
    md = render(g, hsh, paths, seed, summ, shares, resp, scen, sens, dec, base_stat)
    print(md)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as fh:
            fh.write(md)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"graph": hsh, "paths": paths, "seed": seed, "base": summ, "decision_stat": base_stat, "variance_shares": shares,
                       "scenarios": scen, "sensitivity": sens}, fh, indent=1, default=str)
    if a.rows:
        if not a.made:
            ap.error("--rows needs --made (and --decision)")
        rows = ledger_rows(g, summ, alts, a, hsh)
        with open(a.rows, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
        print(f"wrote {len(rows)} rows to {a.rows}; fill the too high / too low notes, then forecast_ledger.py --check")
    return 0


def _smoke() -> None:
    import types
    g = Graph(DEMO); res, dd = run(g, 600, 3); summ = summarize(g, res, dd); bs = decision_stat(g, res, dd, DEMO["decision"])
    sens, alts = sensitivity(g, 300, 3, DEMO["decision"], bs, summ); shares, _, resp = variance_shares(g)
    a = types.SimpleNamespace(made="2026-10-18", decision="demo", source="panel", cutoff="2026-06", resolve_dates=None)
    rows = ledger_rows(g, summ, alts, a, graph_hash(DEMO))
    assert len(rows) == 7 and all(float(r["range_low"]) <= float(r["p"]) <= float(r["range_high"]) for r in rows if r["kind"] == "event")
    assert all(r["method"].startswith("simulation propagate.py") and r["cluster"] for r in rows)
    from forecast_ledger import check_run
    probs = check_run(rows); assert probs == [], probs
    md = render(g, graph_hash(DEMO), 600, 3, summ, shares, resp, [{"name": "demo", "response": response(g, DEMO["scenarios"][0]),
                                                                   "summary": summ}], sens, DEMO["decision"], bs)
    assert "## Scenarios" in md and "crosses flip" in md and "made-up share" in md
    print(f"propagate_report smoke test: ok ({len(rows)} ledger rows pass forecast_ledger.check_run; markdown has base, shares, scenarios, sensitivity)")


if __name__ == "__main__":
    _smoke()
