"""Fit a transmission graph's sizes from a price panel (stress-test-3, references/level-6-simulation.md). Reads a closes CSV
(a Date column plus one column per instrument), cuts it at --asof (the look-ahead guard), turns it into daily log returns,
and for every node that names a series writes: the own-shock vol and a t degrees-of-freedom from its kurtosis; for every
node with parents, the OLS betas of its return on its parents' returns (lagged where the edge says so), each with a
block-bootstrap 80% range, the residual vol as the node's own-shock vol and the R squared; the down-market beta beside
each; and the panel's own base rates for the subject against the benchmark at each horizon (P(beats), excess quantiles,
drawdown frequencies, with the independent n). Everything it writes is marked measured (computed) with the rows used.
Standard library only.

    py -3 graph_fit.py                                                        # smoke test
    py -3 graph_fit.py closes.csv --graph GRAPH.json --asof 2026-08-03 --out GRAPH.fit.json [--years 5] [--resid RESID.csv]

A node reads the column of its own name, or the column named by its "series" key. Nodes without a series (an event, a
quantity no panel holds) keep the sizes the lead wrote and their marks. The residual file holds each series node's own
shocks (regression residuals; demeaned returns for a root node) for propagate.py's block bootstrap.
"""
from __future__ import annotations

import argparse, copy, csv, json, math, random, statistics
from typing import Dict, List, Sequence, Tuple


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def pct(xs: Sequence[float], q: float) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def wilson(k: int, n: int, z: float = 1.2816) -> Tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def solve(A: List[List[float]], b: List[float]) -> List[float]:
    n = len(A); M = [row[:] + [bi] for row, bi in zip(A, b)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        if abs(M[i][i]) < 1e-14:
            raise ValueError("singular design: two parents move together, or a series is constant")
        for r in range(n):
            if r != i and M[r][i]:
                f = M[r][i] / M[i][i]; M[r] = [a - f * c for a, c in zip(M[r], M[i])]
    return [M[i][n] / M[i][i] for i in range(n)]


def ols(y: Sequence[float], X: Sequence[Sequence[float]]):
    """y on the columns of X with an intercept: (betas, intercept, residuals, r2)."""
    cols = [[1.0] * len(y)] + [list(x) for x in X]; k = len(cols)
    A = [[sum(a * b for a, b in zip(cols[i], cols[j])) for j in range(k)] for i in range(k)]
    c = solve(A, [sum(a * yy for a, yy in zip(cols[i], y)) for i in range(k)])
    res = [yy - sum(ci * col[t] for ci, col in zip(c, cols)) for t, yy in enumerate(y)]
    ybar = mean(y); sst = sum((yy - ybar) ** 2 for yy in y) or 1.0
    return c[1:], c[0], res, 1 - sum(r * r for r in res) / sst


def boot_ranges(y, X, reps: int = 200, block: int = 10, seed: int = 1) -> List[List[float]]:
    """Block-bootstrap 80% range per beta (blocks of 10 days keep the clustering of volatile weeks)."""
    rng = random.Random(seed); n = len(y); out = [[] for _ in X]
    for _ in range(reps):
        idx = []
        while len(idx) < n:
            s = rng.randrange(n); idx += [(s + k) % n for k in range(block)]
        idx = idx[:n]
        try:
            bs = ols([y[i] for i in idx], [[x[i] for i in idx] for x in X])[0]
        except ValueError:
            continue
        for j, b in enumerate(bs):
            out[j].append(b)
    return [[round(pct(o, 0.10), 4), round(pct(o, 0.90), 4)] for o in out]


def df_from_kurtosis(xs: Sequence[float]) -> float:
    m = mean(xs); m2 = mean([(x - m) ** 2 for x in xs]); m4 = mean([(x - m) ** 4 for x in xs])
    k = m4 / (m2 * m2) - 3 if m2 else 0.0
    return round(min(30.0, max(3.0, 4 + 6 / k)), 1) if k > 0.3 else 30.0


def read_panel(path: str, cols: Sequence[str], asof: str, years: int):
    """Rows on or before asof and inside the window where every needed series has a value (weekends and holidays drop out)."""
    start = f"{int(asof[:4]) - years}{asof[4:]}"; rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = r.get("Date") or r.get("date") or ""
            if not d or d > asof or d < start:
                continue
            try:
                rows.append((d, {c: float(r[c]) for c in cols}))
            except (KeyError, ValueError, TypeError):
                continue
    rows.sort()
    if len(rows) < 60:
        raise SystemExit(f"only {len(rows)} usable rows for {list(cols)} up to {asof}; check the column names and the window")
    return rows


def panel_base_rates(S: List[float], B: List[float], horizons: Sequence[int], drawdowns: Sequence[float], cls: str) -> dict:
    out = {}
    for H in horizons:
        ex = [(S[t + H] / S[t] - 1) - (B[t + H] / B[t] - 1) for t in range(len(S) - H)]
        if not ex:
            continue
        k, n = sum(1 for x in ex if x > 0), len(ex); n_ind = max(1, n // H); lo, hi = wilson(round(k / n * n_ind), n_ind)
        dd = {str(x): round(mean([min(S[t + 1:t + H + 1]) / S[t] - 1 < -x for t in range(len(S) - H)]), 4) for x in drawdowns}
        out[str(H)] = {"p_beats": round(k / n, 4), "n_windows": n, "independent_n": n_ind, "wilson80_on_independent": [round(lo, 3), round(hi, 3)],
                       "excess_q": {f"q{int(q * 100):02d}": round(pct(ex, q), 4) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
                       "dd_worse": dd, "dd_independent_n": n_ind, "class": f"{cls}, {H}-row windows"}
    return out


def fit(spec: dict, csv_path: str, asof: str, years: int = 5, resid_path: str = "") -> dict:
    out = copy.deepcopy(spec); nodes, edges = out["nodes"], out.get("edges", [])
    series = {n: nd.get("series", n) for n, nd in nodes.items() if nd.get("kind") != "event" and nd.get("series", n)}
    rows = read_panel(csv_path, list(set(series.values())), asof, years)
    dates = [d for d, _ in rows]; px = {c: [v[c] for _, v in rows] for c in set(series.values())}
    ret = {n: [math.log(px[c][t] / px[c][t - 1]) for t in range(1, len(rows))] for n, c in series.items()}
    maxlag = max([int(e.get("lag", 0)) for e in edges] + [0]); T = len(dates) - 1 - maxlag
    src = f"{csv_path.replace(chr(92), '/').split('/')[-1]} rows {dates[0]}..{dates[-1]} (n={len(dates)}, cut at {asof})"
    bench = out.get("benchmark"); down = None
    if bench in ret:
        b = ret[bench][maxlag:]; sd = statistics.pstdev(b); down = [t for t, x in enumerate(b) if x < -1.5 * sd]
    resid: Dict[str, List[float]] = {}
    for n in series:
        y = ret[n][maxlag:]; par = [e for e in edges if e["to"] == n and e["from"] in series]
        if not par:
            m = mean(y); resid[n] = [v - m for v in y]
            nodes[n].update(vol=round(statistics.pstdev(y), 5), df=df_from_kurtosis(y), mark="measured (computed)", source=src); continue
        X = [ret[e["from"]][maxlag - int(e.get("lag", 0)):maxlag - int(e.get("lag", 0)) + T] for e in par]
        betas, _, res, r2 = ols(y, X); rngs = boot_ranges(y, X); resid[n] = res
        bd = ols([y[t] for t in down], [[x[t] for t in down] for x in X])[0] if down and len(down) >= 30 else None
        for j, e in enumerate(par):
            e.update(beta=round(betas[j], 4), range=rngs[j], mark="measured (computed)", source=src)
            if bd:
                e["beta_down"] = round(bd[j], 4); e["n_down"] = len(down)
        nodes[n].update(vol=round(statistics.pstdev(res), 5), df=df_from_kurtosis(res), r2=round(r2, 3), mark="measured (computed)", source=src)
    sub = out["subject"]
    if sub in series and bench in series:
        out["panel_base_rates"] = panel_base_rates(px[series[sub]], px[series[bench]], [int(h) for h in out.get("horizons", [63])],
                                                   out.get("drawdowns", [0.15, 0.25, 0.40]), f"{sub} vs {bench}, panel {dates[0]}..{dates[-1]}")
    out["fit"] = {"csv": csv_path, "asof": asof, "years": years, "rows_used": len(dates), "first_row": dates[0], "last_row": dates[-1],
                  "down_market_days": len(down) if down else 0, "note": "betas are contemporaneous OLS on daily log returns unless the edge "
                  "states a lag; beta_down is the same regression on days the benchmark fell more than 1.5 standard deviations; "
                  "the range is a block-bootstrap 80% interval"}
    if resid_path:
        names = list(resid)
        with open(resid_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh); w.writerow(["Date"] + names)
            for t in range(T):
                w.writerow([dates[1 + maxlag + t]] + [f"{resid[n][t]:.6f}" for n in names])
        out["residuals"] = resid_path
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?"); ap.add_argument("--graph"); ap.add_argument("--asof"); ap.add_argument("--out")
    ap.add_argument("--years", type=int, default=5); ap.add_argument("--resid", default="")
    a = ap.parse_args(argv)
    if not a.csv:
        _smoke(); return 0
    if not (a.graph and a.asof and a.out):
        ap.error("needs --graph, --asof and --out")
    with open(a.graph, encoding="utf-8") as fh:
        spec = json.load(fh)
    out = fit(spec, a.csv, a.asof, a.years, a.resid)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    for e in out.get("edges", []):
        print(f"{e['from']:>8} -> {e['to']:<8} beta {e.get('beta')}  range {e.get('range')}  down {e.get('beta_down', 'n/a')}  [{e.get('mark')}]")
    for n, nd in out["nodes"].items():
        if nd.get("kind") != "event":
            print(f"{n:>8}: own vol {nd.get('vol')}  df {nd.get('df')}  r2 {nd.get('r2', 'root')}")
    for h, b in out.get("panel_base_rates", {}).items():
        print(f"panel {h}d: P(beats) {b['p_beats']} (independent n {b['independent_n']}, Wilson80 {b['wilson80_on_independent']}), dd {b['dd_worse']}")
    print(f"wrote {a.out}" + (f" and {a.resid}" if a.resid else ""))
    return 0


def _smoke() -> None:
    import os, tempfile
    rng = random.Random(3); n = 900

    def t4():
        return rng.gauss(0, 1) / math.sqrt(rng.gammavariate(2, 2) / 4) * math.sqrt(0.5)
    m = [0.010 * t4() for _ in range(n)]; s = [1.3 * x + 0.006 * t4() for x in m]; x = [0.9 * a + 0.6 * b + 0.009 * t4() for a, b in zip(m, s)]
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "closes.csv"); pm = ps = pxx = 100.0
        with open(p, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["Date", "M", "S", "X", "OTHER"]); day0 = 738000
            for t in range(n):
                pm *= math.exp(m[t]); ps *= math.exp(s[t]); pxx *= math.exp(x[t])
                w.writerow([__import__("datetime").date.fromordinal(day0 + t).isoformat(), f"{pm:.4f}", f"{ps:.4f}", f"{pxx:.4f}", ""])
        last = __import__("datetime").date.fromordinal(day0 + n - 1).isoformat()
        spec = {"subject": "X", "benchmark": "M", "horizons": [21, 63], "nodes": {"M": {}, "S": {}, "X": {}, "EV": {"kind": "event", "hazard": 0.001, "size": -0.2, "mark": "assumed"}},
                "edges": [{"from": "M", "to": "S"}, {"from": "M", "to": "X"}, {"from": "S", "to": "X"}, {"from": "EV", "to": "X", "beta": 1.0, "mark": "assumed"}]}
        out = fit(spec, p, last, years=10, resid_path=os.path.join(d, "resid.csv"))
        got = {(e["from"], e["to"]): e for e in out["edges"]}
        for key, true in ((("M", "S"), 1.3), (("M", "X"), 0.9), (("S", "X"), 0.6)):
            e = got[key]; assert abs(e["beta"] - true) < 0.1, (key, e["beta"]); assert e["range"][0] - 0.1 < true < e["range"][1] + 0.1, (key, e["range"])
            assert e["mark"] == "measured (computed)" and "rows" in e["source"]
        assert got[("EV", "X")]["beta"] == 1.0 and got[("EV", "X")]["mark"] == "assumed" and out["nodes"]["EV"]["hazard"] == 0.001
        assert abs(out["nodes"]["X"]["vol"] - 0.009) < 0.002 and 3 <= out["nodes"]["X"]["df"] <= 30 and out["nodes"]["M"].get("r2") is None
        br = out["panel_base_rates"]["63"]; assert br["n_windows"] > 700 and 0 < br["p_beats"] < 1 and "0.15" in br["dd_worse"]
        with open(out["residuals"], newline="") as fh:
            hdr = next(csv.reader(fh)); assert hdr == ["Date", "M", "S", "X"], hdr
    print("graph_fit smoke test: ok (betas recovered within 0.1, ranges, marks, event node untouched, base rates, residual file)")


if __name__ == "__main__":
    raise SystemExit(main())
