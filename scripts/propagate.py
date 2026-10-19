"""Propagation engine for stress-test-3 (references/level-6-simulation.md): a transmission graph of what moves what, by how
much and with what lag; named shock scenarios propagated through it (cause and effect, first and second order); a Monte
Carlo of the subject against its benchmark; the share of the subject's variance each driver carries; and the sensitivity of
the decision statistic to every link's range, which names the research questions. Standard library only. Link sizes come
from graph_fit.py (measured on a price panel) or are written by the lead with a mark and a source; nothing here invents one.
The markdown report, the FORECASTS.csv rows and the command line are in propagate_report.py, which this file hands off to.

    py -3 propagate.py                                     # engine smoke test
    py -3 propagate.py GRAPH.json [--md SIM.md] [--json SIM.json] [--rows FORECASTS.csv --decision <slug> --made <date>]

GRAPH.json keys are listed in the reference (section 2) and shown in DEMO below. Returns are daily log returns with no
drift unless a node states one; the engine is linear in the shocks.
"""
from __future__ import annotations

import copy, csv, hashlib, json, math, os, random, statistics, sys
from typing import Dict, List, Optional, Sequence

QL = (0.05, 0.25, 0.50, 0.75, 0.95)


def mean(it) -> float:
    xs = list(it)
    return sum(xs) / len(xs) if xs else float("nan")


def quant(xs: Sequence[float]) -> Dict[str, float]:
    s = sorted(xs); n = len(s)
    return {f"q{int(q * 100):02d}": s[min(n - 1, int(round(q * (n - 1))))] for q in QL}


def cvar(xs: Sequence[float], tail: float = 0.10) -> float:
    s = sorted(xs); k = max(1, int(len(s) * tail))
    return sum(s[:k]) / k


def cum(logrets: Sequence[float]) -> List[float]:
    out, acc = [], 0.0
    for r in logrets:
        acc += r; out.append(math.exp(acc) - 1.0)
    return out


def topo(nodes, edges):
    """Order for lag-0 propagation; a lag-0 cycle is an error (a lagged edge may close a cycle)."""
    par = {n: [e["from"] for e in edges if e["to"] == n and int(e.get("lag", 0)) == 0] for n in nodes}
    order, seen = [], set()

    def visit(n, stack):
        if n in seen:
            return
        if n in stack:
            raise ValueError(f"lag-0 cycle through {n}")
        for p in par[n]:
            visit(p, stack | {n})
        seen.add(n); order.append(n)
    for n in nodes:
        visit(n, frozenset())
    return order


def read_resid(path: str) -> dict:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {k: [float(r[k]) for r in rows] for k in rows[0] if k.lower() != "date"}


class Graph:
    def __init__(self, spec: dict, resid: Optional[dict] = None):
        self.spec, self.nodes, self.edges = spec, spec["nodes"], spec.get("edges", [])
        for e in self.edges:
            if e["from"] not in self.nodes or e["to"] not in self.nodes:
                raise ValueError(f"edge {e} names an unknown node")
        self.order = topo(list(self.nodes), self.edges)
        self.subject, self.bench = spec["subject"], spec.get("benchmark")
        self.horizons = [int(h) for h in spec.get("horizons", [63])]; self.H = max(self.horizons)
        self.regime = (spec.get("regimes") or {}).get("stress")
        self.resid = resid if resid is not None else (read_resid(spec["residuals"]) if spec.get("residuals") else None)

    def links(self):
        ls = [(f"{e['from']}->{e['to']}", e.get("mark", "assumed")) for e in self.edges]
        return ls + [(f"{n} (event)", nd.get("mark", "assumed")) for n, nd in self.nodes.items() if nd.get("kind") == "event"]

    def own_shocks(self, rng: random.Random, stress: bool) -> Dict[str, List[float]]:
        """One path of own shocks per node: t draws scaled to vol, or a stationary block bootstrap (mean block 20 days) of
        the residual file by one day index for every node; event jumps by hazard with a triangular size."""
        H, out, rg = self.H, {}, (self.regime or {}) if stress else {}
        vm, hm = float(rg.get("vol_mult", 1)), float(rg.get("hazard_mult", 1))
        boot = None
        if self.resid:
            n, boot = len(next(iter(self.resid.values()))), []
            while len(boot) < H:
                i = rng.randrange(n); boot += [(i + k) % n for k in range(int(rng.expovariate(1 / 20)) + 1)]
            boot = boot[:H]
        for name, nd in self.nodes.items():
            if nd.get("kind") == "event":
                hz, fired, xs, mode = float(nd.get("hazard", 0)) * hm, False, [], float(nd["size"])
                lo, hi = nd.get("size_range", [mode, mode])
                for _ in range(H):
                    if not (fired and nd.get("once", True)) and rng.random() < hz:
                        s = rng.triangular(min(lo, hi), max(lo, hi), mode) if lo != hi else mode
                        xs.append(math.log1p(s)); fired = True
                    else:
                        xs.append(0.0)
                out[name] = xs; continue
            vol, drift, df = float(nd.get("vol", 0)) * vm, float(nd.get("drift", 0)), float(nd.get("df", 4))
            if boot is not None and name in self.resid:
                r = self.resid[name]; out[name] = [r[i] * vm + drift for i in boot]; continue
            sc = vol * math.sqrt((df - 2) / df) if df > 2 else vol
            out[name] = [drift + sc * rng.gauss(0, 1) / math.sqrt(rng.gammavariate(df / 2, 2) / df) for _ in range(H)]
        return out

    def propagate(self, shocks: Dict[str, List[float]], stress: bool = False) -> Dict[str, List[float]]:
        """r[n][t] = own shock + sum over incoming edges of beta * r[from][t - lag]."""
        bm = float((self.regime or {}).get("beta_mult", 1)) if stress else 1.0
        H, r = self.H, {n: [0.0] * self.H for n in self.nodes}
        inc = {n: [(e["from"], float(e["beta"]) * bm, int(e.get("lag", 0))) for e in self.edges if e["to"] == n] for n in self.nodes}
        for t in range(H):
            for n in self.order:
                v = shocks[n][t]
                for src, b, lag in inc[n]:
                    if t >= lag:
                        v += b * r[src][t - lag]
                r[n][t] = v
        return r


def impose(shocks: Dict[str, List[float]], scenario: dict) -> None:
    for s in scenario.get("shocks", []):
        days = int(s.get("days", 1)); per = math.log1p(float(s["size"])) / days; d0 = int(s.get("day", 1)) - 1
        for t in range(d0, min(d0 + days, len(shocks[s["node"]]))):
            shocks[s["node"]][t] += per


def response(g: Graph, scenario: dict) -> Dict[str, Dict[int, float]]:
    """Cause and effect without noise: the cumulative simple-return effect of the scenario's shocks on every node at each
    horizon, first- and second-order paths included, calm regime."""
    sh = {n: [0.0] * g.H for n in g.nodes}; impose(sh, scenario); r = g.propagate(sh)
    return {n: {h: cum(r[n])[h - 1] for h in g.horizons} for n in g.nodes}


def variance_shares(g: Graph):
    """Share of the subject's cumulative log-return variance at the longest horizon carried by each node's own shock (calm
    regime): var(shock per day) x the sum over shock days of the squared cumulative response. Exact in this linear model."""
    contrib, resp = {}, {}
    for src, nd in g.nodes.items():
        sh = {n: [0.0] * g.H for n in g.nodes}; sh[src][0] = 1.0
        ir, acc = [], 0.0
        for x in g.propagate(sh)[g.subject]:
            acc += x; ir.append(acc)
        if nd.get("kind") == "event":
            lo, hi = nd.get("size_range", [nd["size"], nd["size"]])
            v = float(nd.get("hazard", 0)) * mean(math.log1p(x) ** 2 for x in (lo, nd["size"], hi))
        else:
            v = float(nd.get("vol", 0)) ** 2
        contrib[src], resp[src] = v * sum(c * c for c in ir), ir[-1]
    tot = sum(contrib.values()) or 1.0
    return {k: v / tot for k, v in contrib.items()}, contrib, resp


def run(g: Graph, paths: int, seed: int, scenario: Optional[dict] = None):
    rng = random.Random(seed); p_st = float((g.regime or {}).get("p", 0))
    res, dd = {h: [] for h in g.horizons}, []
    for _ in range(paths):
        st = rng.random() < p_st; sh = g.own_shocks(rng, st)
        if scenario:
            impose(sh, scenario)
        r = g.propagate(sh, st); cs = cum(r[g.subject]); cb = cum(r[g.bench]) if g.bench else [0.0] * g.H
        for h in g.horizons:
            res[h].append((cs[h - 1], cb[h - 1]))
        dd.append(min(cs))
    return res, dd


def summarize(g: Graph, res, dd) -> dict:
    out = {"horizons": {}}
    for h, pairs in res.items():
        s, b = [a for a, _ in pairs], [c for _, c in pairs]; ex = [a - c for a, c in pairs]
        out["horizons"][h] = {"subject": quant(s), "benchmark": quant(b), "excess": quant(ex), "p_beats": mean(x > 0 for x in ex),
                              "cvar10_excess": cvar(ex),
                              "p_excess_below": {str(x): mean(v < -x for v in ex) for x in g.spec.get("losses", [0.15, 0.25])}}
    out["p_dd_worse"] = {str(x): mean(v < -x for v in dd) for x in g.spec.get("drawdowns", [0.15, 0.25, 0.40])}
    return out


def decision_stat(g: Graph, res, dd, dec: dict) -> float:
    h = int(dec.get("horizon", g.H)); ex = [a - c for a, c in res[h]]; th = float(dec.get("threshold", 0)); st = dec["stat"]
    if st == "p_beats":
        return mean(x > 0 for x in ex)
    if st == "p_excess_below":
        return mean(x < th for x in ex)
    if st == "p_dd_worse":
        return mean(v < -abs(th) for v in dd)
    if st == "median_excess":
        return statistics.median(ex)
    if st == "cvar10_excess":
        return cvar(ex)
    raise ValueError(f"unknown stat {st}")


def variants(g: Graph):
    """Every link with a range: (label, mark, (section, key, field, [low, high]))."""
    for i, e in enumerate(g.edges):
        if "range" in e:
            yield f"{e['from']}->{e['to']} beta {e['beta']}", e.get("mark", "assumed"), ("edges", i, "beta", e["range"])
    for n, nd in g.nodes.items():
        if nd.get("kind") == "event":
            for field, key in (("size", "size_range"), ("hazard", "hazard_range")):
                if key in nd:
                    yield f"{n} {field} {nd[field]}", nd.get("mark", "assumed"), ("nodes", n, field, nd[key])


def with_value(g: Graph, where, value: float) -> Graph:
    spec = copy.deepcopy(g.spec); sec, key, field, _ = where; spec[sec][key][field] = value
    if field == "size":
        spec[sec][key]["size_range"] = [value, value]
    return Graph(spec, resid=g.resid)


def sensitivity(g: Graph, paths: int, seed: int, dec: Optional[dict], base_stat, base_summ):
    """Re-run with every ranged link at each end of its range, same seed (common random numbers): the decision statistic
    at both ends, whether the flip value lies between them, and every summary number under each variant."""
    rows, alts = [], [base_summ]
    for label, mark, where in variants(g):
        lo, hi = where[3]; ends = []
        for v in (lo, hi):
            r, d = run(with_value(g, where, float(v)), paths, seed); alts.append(summarize(g, r, d))
            ends.append(decision_stat(g, r, d, dec) if dec else float("nan"))
        row = {"link": label, "mark": mark, "range": [lo, hi], "stat_low": ends[0], "stat_high": ends[1], "swing": abs(ends[1] - ends[0])}
        if dec and "flip_at" in dec:
            row["crosses_flip"] = min(ends + [base_stat]) <= float(dec["flip_at"]) <= max(ends + [base_stat])
        rows.append(row)
    rows.sort(key=lambda r: -(r["swing"] if r["swing"] == r["swing"] else -1))
    return rows, alts


def graph_hash(spec: dict) -> str:
    core = {k: spec.get(k) for k in ("nodes", "edges", "regimes", "subject", "benchmark", "horizons")}
    return hashlib.sha1(json.dumps(core, sort_keys=True).encode()).hexdigest()[:8]


DEMO = {"subject": "X", "benchmark": "M", "horizons": [21, 63], "seed": 3,
        "nodes": {"M": {"vol": 0.010, "df": 4, "mark": "measured (computed)"}, "S": {"vol": 0.008, "df": 4, "mark": "measured (computed)"},
                  "X": {"vol": 0.012, "df": 4, "mark": "measured (computed)"},
                  "SHOCK": {"kind": "event", "hazard": 0.002, "size": -0.30, "size_range": [-0.45, -0.15], "mark": "assumed"}},
        "edges": [{"from": "M", "to": "S", "beta": 1.3, "range": [1.1, 1.5], "mark": "measured (computed)"},
                  {"from": "M", "to": "X", "beta": 0.9, "range": [0.7, 1.1], "mark": "measured (computed)"},
                  {"from": "S", "to": "X", "beta": 0.6, "range": [0.4, 0.8], "mark": "measured (computed)"},
                  {"from": "SHOCK", "to": "X", "beta": 1.0, "mark": "assumed"}, {"from": "SHOCK", "to": "M", "beta": 0.2, "lag": 1, "mark": "assumed"}],
        "regimes": {"stress": {"p": 0.2, "vol_mult": 1.5, "beta_mult": 1.2}},
        "scenarios": [{"name": "M down 10% over 5 days", "shocks": [{"node": "M", "day": 1, "size": -0.10, "days": 5}]}],
        "decision": {"stat": "p_excess_below", "threshold": -0.15, "horizon": 63, "flip_at": 0.25},
        "panel_base_rates": {"63": {"p_beats": 0.55, "independent_n": 40, "class": "X vs M, 63-row windows, panel",
                                    "dd_worse": {"0.15": 0.2, "0.25": 0.08, "0.4": 0.02}, "dd_independent_n": 40}}}


def _smoke() -> None:
    g = Graph(DEMO)
    sh = {n: [0.0] * g.H for n in g.nodes}; sh["M"][0] = 1.0
    assert abs(sum(g.propagate(sh)["X"]) - 1.68) < 1e-9, "unit M shock reaches X as 0.9 + 1.3 * 0.6"
    assert abs(response(g, DEMO["scenarios"][0])["X"][63] - (0.9 ** 1.68 - 1)) < 1e-9, "a 10% fall in M is a 0.9^1.68 - 1 fall in X"
    try:
        Graph({"subject": "A", "nodes": {"A": {"vol": 0.01}, "B": {"vol": 0.01}}, "edges": [{"from": "A", "to": "B", "beta": 1}, {"from": "B", "to": "A", "beta": 1}]})
        raise AssertionError("a lag-0 cycle must be refused")
    except ValueError:
        pass
    shares, contrib, _ = variance_shares(g)
    assert abs(sum(shares.values()) - 1) < 1e-9 and shares["M"] > shares["S"] > 0
    res, dd = run(Graph({**DEMO, "regimes": {}}), 3000, 3)
    sim_var = statistics.pvariance([math.log1p(a) for a, _ in res[63]])
    assert abs(sim_var / sum(contrib.values()) - 1) < 0.3, f"simulated variance {sim_var:.5f} vs analytic {sum(contrib.values()):.5f}"
    summ = summarize(g, res, dd); bs = decision_stat(g, res, dd, DEMO["decision"])
    assert 0 < bs < 1 and summ["p_dd_worse"]["0.15"] >= summ["p_dd_worse"]["0.4"]
    sens, alts = sensitivity(g, 400, 3, DEMO["decision"], bs, summ)
    assert len(sens) == 4 and sens[0]["swing"] >= sens[-1]["swing"] and len(alts) == 9
    print("propagate smoke test: ok (responses, cycle guard, variance shares vs simulation, sensitivity with common random numbers)")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        _smoke()
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from propagate_report import main
        raise SystemExit(main())
