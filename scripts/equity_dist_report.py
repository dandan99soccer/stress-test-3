"""The printed report and the command line for equity_dist.py (the equities pack): the market reference per horizon, the
per-weight after-tax table paired against hold, the trim break-even lines, the drawdown rows and the sizing line, plus the
scenario header when a transmission graph was run. Standard library only.

    py -3 equity_dist_report.py                     # smoke test (renders the example case)
    py -3 equity_dist.py case.json [--json out.json] [--scenario GRAPH.json (--shock NODE=size[:days] ... | --scenario-name NAME)]
    py -3 equity_dist.py --example                  # print the example case as JSON
"""
from __future__ import annotations

import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from equity_dist import EXAMPLE, analyze, apply_scenario  # noqa: E402


def _f(x: float) -> str:
    return f"{x:+,.0f}"


def render(out: dict, scenario=None) -> str:
    L = [f"equity_dist — {out['name']} as of {out['as_of']}: spot {out['spot']:,.2f}, NAV ${out['nav']:,.0f}, {out['shares']:g} sh = {out['weight_now']:.1%} of NAV; "
         f"proceeds to {out['destination']}; eventual rate {out['eventual_rate']:.1%}; bid-ask width of the IV quote {out['bid_ask_width']}"]
    if scenario:
        scen, resp, g = scenario
        L.append(f"Scenario {scen['name']!r} through the graph (no noise, calm regime, {g.H}d): " + "; ".join(f"{n} {r[g.H]:+.1%}" for n, r in resp.items())
                 + f"; position {out['shares'] * out['spot'] * resp[g.subject][g.H]:+,.0f} = {out['weight_now'] * resp[g.subject][g.H]:+.1%} of NAV")
    for H, blk in out["horizons"].items():
        m, dd = blk["reference"], out["drawdown"][H]
        L += ["", f"Market reference, {H}d: non-event vol {m['sig_ne_annual']:.1%} a year (vol_ratio {m['vol_ratio']:.2f}), idiosyncratic {m['sig_idio_annual']:.1%}, "
              f"event sigma {m['sig_event']:.1%} x {m['n_events']} event(s); horizon sd name {m['sig_name']:.1%}, excess {m['sig_e']:.1%}; "
              f"centre name {m['mu_name']:+.1%}, excess {m['alpha']:+.1%}; t df {m['df']:g}",
              "  excess vs beta-matched benchmark, vol units: " + " ".join(f"{k} {v:+.2f}" for k, v in blk["excess_vol_units"].items())
              + "; in return: " + " ".join(f"{k} {v:+.1%}" for k, v in blk["excess_quantiles"].items()),
              "  name drawdown within the horizon, terminal / path (reflection approx.): "
              + ", ".join(f"{float(x):.0%}: {v['terminal']:.2f} / {v['path']:.2f}" for x, v in dd["corrected"].items())
              + ("" if m["vol_ratio"] == 1 else "; raw IV path: " + ", ".join(f"{v['path']:.2f}" for v in dd["raw"].values())),
              "  weight | sold sh | tax now | net tax | after-tax dNAV q05 / q25 / q50 / q75 / q95 | CVaR10 | P(loss>tol) | mean vs hold [band] | P(>hold) | regret vs hold"]
        for r in blk["weights"]:
            q = r["quantiles"]; hold = r["weight"] == out["weight_now"]
            L.append(f"  {r['weight']:6.1%}{'*' if hold else ' '}| {r['shares_sold']:7.1f} | {_f(r['tax_now']):>9} | {_f(r['net_tax_cost']):>9} | "
                     f"{_f(q['q05'])} / {_f(q['q25'])} / {_f(q['q50'])} / {_f(q['q75'])} / {_f(q['q95'])} | {_f(r['cvar10'])} | {r['p_loss_over_tolerance']:.3f} | "
                     f"{_f(r['mean_vs_hold'])} [{_f(r['band_vs_hold'][0])}, {_f(r['band_vs_hold'][1])}]{' indistinguishable' if r['indistinguishable'] and not hold else ''} | "
                     f"{r['p_better_than_hold']:.2f} | {_f(r['regret_vs_hold'])}")
        tb = [r for r in blk["weights"] if "dollars_trimmed" in r]
        if tb:
            L.append("  trim break-even: " + "; ".join(f"to {r['weight']:.0%}: trims ${r['dollars_trimmed']:,.0f}, net tax ${r['net_tax_cost']:,.0f}, "
                                                        f"bear $ avoided ${r['bear_dollars_avoided']:,.0f}, break-even P(bear) {r['breakeven_p_bear']:.2f}, "
                                                        f"needs underperformance {r['required_underperformance']:.1%}" for r in tb))
    s = out["sizing"]
    L += ["", f"Sizing: loss budget w_max = {s['tolerance']:.0%} tolerance / {s['shock_drop']:.0%} drop ({s['shock_label']}) = {s['loss_budget_w']:.1%} of NAV; "
          + "sensitivity " + ", ".join(f"{k} drop: {v:.0%}" for k, v in s["sensitivity"].items())
          + f"; Kelly half at alpha {s['alpha']:+.1%} ± {s['alpha_se']:.1%} a year (k {s['kelly_shrink_k']:.2f}): {s['kelly_half_w']:.1%} — a sensitivity line, never the size",
          "* = the weight held now (hold). Means indistinguishable where the band from alpha's standard error contains zero: the choice is risk against tax."]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", nargs="?"); ap.add_argument("--json"); ap.add_argument("--example", action="store_true")
    ap.add_argument("--scenario"); ap.add_argument("--shock", action="append"); ap.add_argument("--scenario-name")
    a = ap.parse_args(argv)
    if a.example:
        print(json.dumps(EXAMPLE, indent=1)); return 0
    if not a.case:
        ap.error("a case.json is needed (or --example)")
    with open(a.case, encoding="utf-8") as fh:
        c = json.load(fh)
    scen = None
    if a.scenario:
        if not (a.shock or a.scenario_name):
            ap.error("--scenario needs --shock NODE=size[:days] (repeatable) or --scenario-name")
        with open(a.scenario, encoding="utf-8") as fh:
            spec = json.load(fh)
        c, s, resp, g = apply_scenario(c, spec, a.shock, a.scenario_name); scen = (s, resp, g)
    out = analyze(c); print(render(out, scen))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=str)
    return 0


def _smoke() -> None:
    txt = render(analyze(EXAMPLE))
    assert "trim break-even" in txt and "loss budget" in txt and "Market reference, 63d" in txt and "Market reference, 252d" in txt and "*|" in txt
    from propagate import DEMO
    c2, s, resp, g = apply_scenario(EXAMPLE, DEMO, ["M=-0.10:5"]); txt2 = render(analyze(c2), (s, resp, g))
    assert "Scenario" in txt2 and "via propagate.py" in txt2
    print("equity_dist_report smoke test: ok (report renders the example case with and without a scenario)")


if __name__ == "__main__":
    _smoke()
