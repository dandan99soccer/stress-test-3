"""Analytic horizon distribution and per-weight payoffs for the equities pack (references/packs/equities.md, sections 4 and 6):
the market reference (implied vol split into event and non-event variance, centred at zero excess or beta times a stated
premium, Student-t tails at fixed degrees of freedom, bid-ask width recorded) and, per candidate weight, the after-tax NAV
change paired against hold, the trim break-even and the loss-budget size; plus a scenario mode that runs a named shock
through a transmission graph (propagate.py, references/level-6-simulation.md) and uses the subject's computed move as the
shock-case drop. Standard library only. The t math is in student_t.py, the lots in tax_lots.py, the printed report and
the command line in equity_dist_report.py, which this file hands off to. Nothing here is advice or an order.

    py -3 equity_dist.py                                  # smoke test
    py -3 equity_dist.py --example > case.json            # every input key, as a worked example
    py -3 equity_dist.py case.json [--json out.json]
    py -3 equity_dist.py case.json --scenario GRAPH.json --shock SMH=-0.15:5 [--shock EWT=-0.2] | --scenario-name "<name>"

All analytic: quantiles from the t inverse CDF; CVaR and regret from a 400-point quantile grid; the path drawdown probability
is the reflection approximation, 2 x P(terminal below the level). One t variable on the combined factor-plus-idiosyncratic
scale is an approximation the pack states; so is reading the implied move as 0.8 of a one-sigma event move.

Model, horizon H in trading days (tau = H/252), from the case keys: R_name = (rf + beta*premium + alpha)*tau + beta*sig_m*z_m
+ sig_e*z_e, with sig_m the index IV over the horizon, sig_e the idiosyncratic non-event vol over the horizon plus one event
variance per scheduled event; the excess against the beta-matched benchmark is alpha*tau + sig_e*z_e. After-tax NAV change
at weight w, proceeds in the destination (benchmark or cash): NAV*(1-e)*[w*R_name + (w0-w)*R_dest] - tax now - e*embedded
gain kept, e the eventual rate on gains never realized today. Paired against hold: NAV*(1-e)*(w-w0)*(R_name-R_dest) minus
the net tax cost (tax now less the eventual tax on the gain sold, discounted over deferral_years at rf).
"""
from __future__ import annotations

import json, math, os, sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tax_lots as TL  # noqa: E402
from student_t import Dist  # noqa: E402


def events_within(days_to_event, recur: int, H: int) -> int:
    """Scheduled events inside H trading days: the next one at days_to_event, then every recur days."""
    if days_to_event is None or int(days_to_event) > H:
        return 0
    return 1 + int((H - int(days_to_event)) // max(recur, 1))


def moments(c: dict, H: int, vol_ratio: Optional[float] = None) -> dict:
    """Horizon-H moments of the name, its benchmark and the beta-matched excess from the case's market inputs."""
    vr = float(c.get("vol_ratio", 1.0)) if vol_ratio is None else vol_ratio
    iv, T, beta, df = float(c["iv"]), int(c.get("iv_days", 30)), float(c["beta"]), float(c.get("df", 4))
    ev = c.get("event") or {}; m = float(ev.get("implied_move", 0))
    sig_ev = m / 0.8 if ev.get("convention", "straddle") == "straddle" else m
    d_ev, recur = ev.get("days_to_event"), int(ev.get("recur_days", 63))
    n_T = events_within(d_ev, recur, T) if m else 0
    var_ne = (iv * iv * T / 252 - n_T * sig_ev ** 2) * 252 / max(T - n_T, 1)
    if var_ne <= 0:
        raise ValueError("the event move implies more variance than the IV holds for its expiry; check iv_days and the move")
    var_ne *= vr * vr
    idx = float(c.get("index_iv", 0.16)); var_idio = max(var_ne - beta * beta * idx * idx, 0.25 * var_ne)
    tau, n_H = H / 252, (events_within(d_ev, recur, H) if m else 0)
    sig_m, sig_e = idx * math.sqrt(tau), math.sqrt(var_idio * tau + n_H * sig_ev ** 2)
    rf, prem, alpha = float(c.get("rf", 0.04)), float(c.get("premium", 0.04)), float(c.get("alpha", 0.0))
    return dict(H=H, tau=tau, beta=beta, df=df, sig_m=sig_m, sig_e=sig_e, sig_name=math.hypot(beta * sig_m, sig_e), n_events=n_H,
                mu_name=(rf + beta * prem + alpha) * tau, mu_bench=(rf + prem) * tau, rf=rf * tau, prem=prem * tau, alpha=alpha * tau,
                alpha_se=float(c.get("alpha_se", 0.0)) * tau, sig_ne_annual=math.sqrt(var_ne), sig_idio_annual=math.sqrt(var_idio),
                sig_event=sig_ev, vol_ratio=vr)


def lots_of(c: dict) -> List[dict]:
    if c.get("lots_csv"):
        return TL.read_lots_csv(c["lots_csv"], c.get("name", ""))
    return [dict(l, id=l.get("id", f"L{i + 1}")) for i, l in enumerate(c.get("lots", []))]


def weight_row(c: dict, mom: dict, w: float, w0: float, spot: float, nav: float, lots: List[dict], rates: dict, e_rate: float, dest: str) -> dict:
    """One candidate weight at one horizon: tax, after-tax NAV change, and the paired comparison against hold (w0)."""
    one_e, b_d, dw = 1 - e_rate, (1.0 if dest == "benchmark" else 0.0), w - w0
    sell_sh = max(0.0, -dw * nav / spot)
    sel = TL.select(lots, sell_sh, spot, c["as_of"], c.get("lot_method", "hifo"), rates) if sell_sh > 1e-9 else []
    r, emb = TL.realized(sel), TL.embedded(lots, spot, c["as_of"])
    net_tax = r["tax"] - e_rate * r["gain"] * (1 + float(c.get("rf", 0.04))) ** (-float(c.get("deferral_years", 0)))
    mean = nav * one_e * (w * mom["mu_name"] + (w0 - w) * (mom["mu_bench"] if b_d else mom["rf"])) - r["tax"] - e_rate * (emb["gain"] - r["gain"])
    at = Dist(mean, nav * one_e * math.hypot((w * mom["beta"] + (w0 - w) * b_d) * mom["sig_m"], w * mom["sig_e"]), mom["df"])
    mean_d = nav * one_e * dw * ((mom["beta"] - b_d) * mom["prem"] + mom["alpha"]) - net_tax
    sd_d = nav * one_e * abs(dw) * math.hypot((mom["beta"] - b_d) * mom["sig_m"], mom["sig_e"])
    D = Dist(mean_d, sd_d, mom["df"]) if sd_d > 0 else None
    band = nav * one_e * abs(dw) * mom["alpha_se"]; tol = float(c.get("tolerance", 0.15))
    name = Dist(mom["mu_name"], mom["sig_name"], mom["df"])
    row = dict(weight=w, shares_sold=sell_sh, tax_now=r["tax"], st_gain=r["st_gain"], lt_gain=r["lt_gain"], net_tax_cost=net_tax,
               quantiles=at.quantiles(), cvar10=at.cvar(0.10), p_loss_over_tolerance=(name.cdf(-tol / w) if w > 0 else 0.0),
               mean_vs_hold=mean_d, band_vs_hold=[mean_d - band, mean_d + band], p_better_than_hold=(1 - D.cdf(0) if D else 0.5),
               regret_vs_hold=(D.e_neg(0) if D else 0.0), indistinguishable=bool(abs(mean_d) <= band))
    if dw < 0:
        sh = c.get("shock") or {}; trimmed = -dw * nav
        avoided = trimmed * (float(sh.get("name_drop", 0.4)) - float(sh.get("benchmark_drop", 0.0)) * b_d)
        row.update(dollars_trimmed=trimmed, bear_dollars_avoided=avoided, breakeven_p_bear=(net_tax / avoided if avoided > 0 else float("nan")),
                   required_underperformance=net_tax / trimmed)
    return row


def sizing_lines(c: dict, mom: dict) -> dict:
    """The loss-budget size (primary) and the half-Kelly line (sensitivity only; zero at zero graded edge)."""
    sh = c.get("shock") or {}; drop, tol = float(sh.get("name_drop", 0.4)), float(c.get("tolerance", 0.15))
    alpha, se, s2 = float(c.get("alpha", 0)), float(c.get("alpha_se", 0)), mom["sig_idio_annual"] ** 2
    k = alpha * alpha / (alpha * alpha + se * se) if (alpha or se) else 0.0
    return dict(loss_budget_w=(tol / drop if drop > 0 else float("inf")), tolerance=tol, shock_drop=drop, shock_label=sh.get("label", "assumed"),
                sensitivity={f"{d:.0%}": tol / d for d in (0.3, 0.4, 0.5, 0.6)}, kelly_half_w=(0.5 * alpha * k / s2 if s2 > 0 else 0.0),
                kelly_shrink_k=k, alpha=alpha, alpha_se=se)


def analyze(c: dict) -> dict:
    lots = lots_of(c); spot, nav = float(c["spot"]), float(c["nav"])
    shares = float(c.get("shares") or sum(l["shares"] for l in lots)); w0 = round(shares * spot / nav, 6)
    tax = c.get("tax") or {}; rates = {**TL.DEFAULT_RATES, **{k: v for k, v in tax.items() if k != "eventual"}}
    e_rate = float(tax.get("eventual", rates["lt"] + rates.get("state", 0))); dest = c.get("destination", "benchmark")
    weights = sorted({w0, *[float(w) for w in c.get("weights", [])]}, reverse=True)
    out = dict(name=c.get("name"), as_of=c["as_of"], spot=spot, nav=nav, shares=shares, weight_now=w0, destination=dest, eventual_rate=e_rate,
               bid_ask_width=c.get("bid_ask_width"), horizons={}, drawdown={}, sizing=sizing_lines(c, moments(c, int(c.get("horizons", [63])[0]))))
    for H in c.get("horizons", [63, 252]):
        mom = moments(c, int(H))
        out["horizons"][str(H)] = dict(reference=mom, excess_quantiles=Dist(mom["alpha"], mom["sig_e"], mom["df"]).quantiles(),
                                       excess_vol_units=Dist(mom["alpha"] / mom["sig_e"], 1.0, mom["df"]).quantiles(),
                                       weights=[weight_row(c, mom, w, w0, spot, nav, lots, rates, e_rate, dest) for w in weights])
        dd = {}
        for label, vr in (("corrected", None), ("raw", 1.0)):
            m = moments(c, int(H), vr); d = Dist(m["mu_name"], m["sig_name"], m["df"])
            dd[label] = {str(x): dict(terminal=d.cdf(-float(x)), path=min(1.0, 2 * d.cdf(-float(x)))) for x in c.get("drawdown_levels", [0.15, 0.25, 0.40])}
        out["drawdown"][str(H)] = dd
    return out


def apply_scenario(c: dict, spec: dict, shocks: Optional[List[str]] = None, name: Optional[str] = None):
    """Run a named shock through the transmission graph (propagate.response, no noise, first- and second-order paths) and write
    the subject's move at the graph's longest horizon into the case's shock as the drop; returns (case, scenario, response, graph)."""
    from propagate import Graph, graph_hash, response
    g = Graph({k: v for k, v in spec.items() if k != "residuals"})  # the residual file feeds only the Monte Carlo, not response()
    if name:
        scen = next((s for s in spec.get("scenarios", []) if s["name"] == name), None)
        if not scen:
            raise SystemExit(f"no scenario named {name!r} in the graph")
    else:
        scen = {"name": "; ".join(shocks or []), "shocks": []}
        for s in shocks or []:
            node, rest = s.split("="); size, _, days = rest.partition(":")
            scen["shocks"].append({"node": node, "day": 1, "size": float(size), "days": int(days or 1)})
    resp, H = response(g, scen), g.H
    move, bmove = resp[g.subject][H], (resp[g.bench][H] if g.bench else 0.0)
    c2 = dict(c, shock=dict(name_drop=-move, benchmark_drop=-bmove, label=f"scenario {scen['name']!r} via propagate.py {graph_hash(spec)}, {H}d"))
    return c2, scen, resp, g


EXAMPLE = {"name": "TSM", "as_of": "2026-10-16", "spot": 413.0, "nav": 271603.0, "shares": 291, "benchmark": "SPY", "beta": 1.4, "index_iv": 0.16,
           "premium": 0.04, "rf": 0.04, "iv": 0.48, "iv_days": 45, "bid_ask_width": 0.10, "vol_ratio": 1.0, "df": 4,
           "event": {"implied_move": 0.07, "days_to_event": 20, "recur_days": 63, "convention": "straddle"}, "horizons": [63, 252],
           "alpha": 0.0, "alpha_se": 0.03, "weights": [0.25, 0.20, 0.15, 0.0], "destination": "benchmark",
           "lots": [{"id": "A", "shares": 200, "basis": 180.0, "acquired": "2024-03-01"}, {"id": "B", "shares": 91, "basis": 350.0, "acquired": "2026-09-29"}],
           "lot_method": "hifo", "tax": {"st": 0.408, "lt": 0.238, "state": 0.0, "eventual": 0.238}, "deferral_years": 10,
           "shock": {"name_drop": 0.40, "benchmark_drop": 0.10, "label": "strait shock, assumed"}, "tolerance": 0.15, "drawdown_levels": [0.15, 0.25, 0.40],
           "_comment": "example figures, not a reading of the account; iv_days and days_to_event are trading days; lots_csv may replace lots; "
                       "deferral_years discounts the eventual tax on a gain sold today (0 = no deferral value); tax rates are the owner's [owner]"}


def _smoke() -> None:
    from student_t import t_quantile
    out = analyze(EXAMPLE); h = out["horizons"]["63"]; rows = {r["weight"]: r for r in h["weights"]}
    hold = rows[out["weight_now"]]
    assert hold["tax_now"] == 0 and hold["mean_vs_hold"] == 0 and hold["regret_vs_hold"] == 0
    r25 = rows[0.25]; q = list(r25["quantiles"].values())
    assert all(a <= b for a, b in zip(q, q[1:])) and r25["tax_now"] > 0 and r25["st_gain"] > 0 and r25["lt_gain"] > 0, "HIFO sells the high-basis ST lot first, then part of the LT lot"
    assert 0 < r25["net_tax_cost"] < r25["tax_now"], "the net tax cost is the tax now less the discounted eventual tax on the same gain"
    assert abs(r25["required_underperformance"] - r25["net_tax_cost"] / r25["dollars_trimmed"]) < 1e-9 and 0 < r25["breakeven_p_bear"] < 1
    assert rows[0.15]["p_loss_over_tolerance"] < rows[0.25]["p_loss_over_tolerance"] < hold["p_loss_over_tolerance"]
    assert h["reference"]["n_events"] == 1 and out["horizons"]["252"]["reference"]["n_events"] == 4
    assert abs(out["sizing"]["loss_budget_w"] - 0.375) < 1e-9 and out["sizing"]["kelly_half_w"] == 0
    assert abs(h["excess_vol_units"]["q50"]) < 1e-9 and abs(h["excess_vol_units"]["q95"] - t_quantile(0.95, 4) * math.sqrt(0.5)) < 1e-6
    assert out["drawdown"]["63"]["corrected"]["0.15"]["path"] > out["drawdown"]["63"]["corrected"]["0.4"]["path"]
    c_cash = dict(EXAMPLE, destination="cash"); rc = {r["weight"]: r for r in analyze(c_cash)["horizons"]["63"]["weights"]}[0.25]
    assert rc["mean_vs_hold"] < r25["mean_vs_hold"], "with beta above one, moving to cash forgoes more premium than moving to the benchmark"
    from propagate import DEMO
    c2, scen, resp, g = apply_scenario(EXAMPLE, DEMO, ["M=-0.10:5"])
    assert abs(c2["shock"]["name_drop"] - (1 - 0.9 ** 1.68)) < 1e-9, "the scenario's subject move becomes the shock drop"
    assert abs(analyze(c2)["sizing"]["loss_budget_w"] - 0.15 / (1 - 0.9 ** 1.68)) < 1e-9
    print("equity_dist smoke test: ok (reference split, per-weight after-tax rows paired against hold, break-even, loss budget, cash vs benchmark, scenario via propagate)")


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        _smoke()
    else:
        from equity_dist_report import main
        raise SystemExit(main())
