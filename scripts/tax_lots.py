"""Tax lots for the equities pack (references/packs/equities.md section 6): read lots from a JSON list or an IBKR lots CSV,
pick the lots a sale takes by a lot method, split short- from long-term, compute the realized gain and the tax at the
owner's rates, list the lots that turn long-term soon, the wash-sale window, and print the six-line tax block. Standard
library only. Rates are the owner's facts and are printed marked [owner]; netting against other gains, state tax, the
$3,000 ordinary-loss limit and the ADR-versus-ordinary wash-sale question stay with the owner and a professional.

    py -3 tax_lots.py                                   # smoke test
    from tax_lots import read_lots_csv, select, realized, embedded, crossings, wash_window, tax_block

A lot is {"shares", "basis" (per share), "acquired" (YYYY-MM-DD), "id"}. Long-term means held more than one year:
the sale date is after the first anniversary of the acquisition (Pub. 550's rule; the statute is 26 USC 1222).
"""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_RATES = {"st": 0.37 + 0.038, "lt": 0.20 + 0.038, "state": 0.0}  # federal top brackets plus NIIT; [owner] overrides


def _d(s) -> date:
    return s if isinstance(s, date) else date.fromisoformat(str(s)[:10])


def anniversary(acquired: date) -> date:
    try:
        return acquired.replace(year=acquired.year + 1)
    except ValueError:  # 29 February
        return acquired.replace(year=acquired.year + 1, month=3, day=1)


def is_long_term(acquired, sale_date) -> bool:
    return _d(sale_date) > anniversary(_d(acquired))


def read_lots_csv(path: str, symbol: str) -> List[dict]:
    """IBKR lots CSV (symbol, acquired, qty, avg_price, ...) or any CSV with shares/basis/acquired columns."""
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            if symbol and r.get("symbol", symbol) != symbol:
                continue
            shares = float(r.get("qty") or r.get("shares") or 0)
            basis = float(r.get("avg_price") or r.get("basis") or (float(r["cost_basis"]) / shares if r.get("cost_basis") and shares else 0))
            out.append({"id": r.get("id") or f"L{i + 1}", "shares": shares, "basis": basis, "acquired": r["acquired"][:10]})
    return out


def rate_for(term: str, rates: Dict[str, float]) -> float:
    return float(rates.get(term, 0)) + float(rates.get("state", 0))


def select(lots: Sequence[dict], shares_to_sell: float, spot: float, sale_date, method: str = "hifo",
           rates: Optional[Dict[str, float]] = None) -> List[dict]:
    """The lots a sale of `shares_to_sell` takes, in order, each as {lot, shares, gain, term, tax}.
    Methods: hifo (highest basis first), fifo, lifo, mintax (lowest tax per share first, losses before gains)."""
    rates = rates or DEFAULT_RATES
    rows = []
    for lot in lots:
        term = "lt" if is_long_term(lot["acquired"], sale_date) else "st"
        gps = spot - float(lot["basis"])
        rows.append((lot, term, gps, gps * rate_for(term, rates)))
    keys = {"hifo": lambda r: -float(r[0]["basis"]), "fifo": lambda r: _d(r[0]["acquired"]), "lifo": lambda r: -_d(r[0]["acquired"]).toordinal(),
            "mintax": lambda r: r[3]}
    if method not in keys:
        raise ValueError(f"unknown lot method {method}; use hifo, fifo, lifo or mintax")
    rows.sort(key=keys[method])
    out, left = [], float(shares_to_sell)
    for lot, term, gps, tps in rows:
        if left <= 1e-9:
            break
        take = min(left, float(lot["shares"])); left -= take
        out.append({"lot": lot, "shares": take, "gain": take * gps, "term": term, "tax": take * tps})
    if left > 1e-6:
        raise ValueError(f"only {shares_to_sell - left:g} of {shares_to_sell:g} shares are held in the lots given")
    return out


def realized(selection: Sequence[dict]) -> Dict[str, float]:
    st = sum(s["gain"] for s in selection if s["term"] == "st"); lt = sum(s["gain"] for s in selection if s["term"] == "lt")
    return {"st_gain": st, "lt_gain": lt, "gain": st + lt, "tax": sum(s["tax"] for s in selection), "shares": sum(s["shares"] for s in selection)}


def embedded(lots: Sequence[dict], spot: float, as_of) -> Dict[str, float]:
    """Unrealized gain in the lots today, by term, and the basis of what is held."""
    out = {"st_gain": 0.0, "lt_gain": 0.0, "basis": 0.0, "shares": 0.0}
    for lot in lots:
        g = float(lot["shares"]) * (spot - float(lot["basis"]))
        out["lt_gain" if is_long_term(lot["acquired"], as_of) else "st_gain"] += g
        out["basis"] += float(lot["shares"]) * float(lot["basis"]); out["shares"] += float(lot["shares"])
    out["gain"] = out["st_gain"] + out["lt_gain"]
    return out


def crossings(lots: Sequence[dict], spot: float, as_of, within_days: int = 120, rates: Optional[Dict[str, float]] = None) -> List[dict]:
    """Short-term lots whose first anniversary falls within `within_days`: the date and the tax saved by waiting (gains only)."""
    rates = rates or DEFAULT_RATES; a = _d(as_of); out = []
    for lot in lots:
        ann = anniversary(_d(lot["acquired"]))
        if a <= ann <= a + timedelta(days=within_days):
            gain = float(lot["shares"]) * (spot - float(lot["basis"]))
            out.append({"lot": lot["id"], "lt_on": (ann + timedelta(days=1)).isoformat(), "gain": gain,
                        "tax_saved_by_waiting": max(0.0, gain) * (rate_for("st", rates) - rate_for("lt", rates))})
    return sorted(out, key=lambda r: r["lt_on"])


def wash_window(sale_date) -> Tuple[str, str]:
    """The 61-day wash-sale window around a sale at a loss (26 USC 1091): 30 days before to 30 days after, all accounts."""
    s = _d(sale_date)
    return ((s - timedelta(days=30)).isoformat(), (s + timedelta(days=30)).isoformat())


def tax_block(symbol: str, selection: Sequence[dict], rates: Dict[str, float], sale_date, lots: Sequence[dict], spot: float,
              lot_method: str, flags: Sequence[str] = ()) -> List[str]:
    """The six fixed lines of equities.md section 6, as strings."""
    r = realized(selection); lo, hi = wash_window(sale_date); xs = crossings(lots, spot, sale_date, rates=rates)
    lines = ["1. lots sold: " + ("; ".join(f"{s['lot']['id']} {s['shares']:g} sh @ {float(s['lot']['basis']):.2f} ({s['term'].upper()}, gain {s['gain']:+,.0f})"
                                           for s in selection) or "none"),
             f"2. federal tax now [owner rates st {rate_for('st', rates):.1%}, lt {rate_for('lt', rates):.1%}]: ${r['tax']:,.0f} on ST {r['st_gain']:+,.0f} / LT {r['lt_gain']:+,.0f}; state: add the owner's rate",
             f"3. lot method: {lot_method}; set or change it at the broker by 8:30 PM ET on the trade day (IBKR), or specific-lot ID before then",
             f"4. wash-sale window if any lot sells at a loss: {lo} to {hi}, all accounts including IRAs (Rev. Rul. 2008-5: a loss re-bought in an IRA is lost for good)",
             "5. sell now vs after 1 January: tax due with next April's return either way; ST lots turning LT soon: " + ("; ".join(f"{x['lot']} on {x['lt_on']} (saves ${x['tax_saved_by_waiting']:,.0f})" for x in xs) or "none within 120 days"),
             "6. professional review: " + ("; ".join(flags) if flags else "not flagged (flag any ADR vs ordinary line, option, straddle, constructive sale or PFIC)")]
    return [f"Tax block — {symbol}, sale {_d(sale_date).isoformat()}, spot {spot:,.2f}"] + lines


def _smoke() -> None:
    lots = [{"id": "A", "shares": 100, "basis": 180.0, "acquired": "2024-03-01"}, {"id": "B", "shares": 50, "basis": 450.0, "acquired": "2026-09-29"},
            {"id": "C", "shares": 30, "basis": 300.0, "acquired": "2025-10-20"}]
    assert is_long_term("2024-03-01", "2026-10-16") and not is_long_term("2025-10-20", "2026-10-16") and not is_long_term("2025-10-16", "2026-10-16")
    assert is_long_term("2025-10-16", "2026-10-17"), "long-term starts the day after the first anniversary"
    assert anniversary(date(2024, 2, 29)) == date(2025, 3, 1)
    sel = select(lots, 60, 413.0, "2026-10-16", "hifo")
    assert [s["lot"]["id"] for s in sel] == ["B", "C"] and sel[0]["shares"] == 50 and sel[1]["shares"] == 10, "HIFO takes the highest basis first"
    r = realized(sel)
    assert abs(r["gain"] - (50 * (413 - 450) + 10 * (413 - 300))) < 1e-6 and r["st_gain"] == r["gain"] and r["tax"] < 0, "a net loss is a tax benefit (netting is the owner's)"
    sel2 = select(lots, 100, 413.0, "2026-10-16", "fifo"); assert sel2[0]["lot"]["id"] == "A" and sel2[0]["term"] == "lt"
    assert abs(realized(sel2)["tax"] - 100 * (413 - 180) * rate_for("lt", DEFAULT_RATES)) < 1e-6
    sel3 = select(lots, 60, 413.0, "2026-10-16", "mintax"); assert sel3[0]["lot"]["id"] == "B", "mintax sells the loss lot first"
    try:
        select(lots, 500, 413.0, "2026-10-16"); raise AssertionError("over-selling must fail")
    except ValueError:
        pass
    e = embedded(lots, 413.0, "2026-10-16"); assert abs(e["gain"] - (100 * 233 - 50 * 37 + 30 * 113)) < 1e-6 and e["lt_gain"] == 100 * 233
    xs = crossings(lots, 413.0, "2026-10-16"); assert [x["lot"] for x in xs] == ["C"] and xs[0]["lt_on"] == "2026-10-21" and xs[0]["tax_saved_by_waiting"] > 0
    assert wash_window("2026-10-16") == ("2026-09-16", "2026-11-15")
    blk = tax_block("TSM", sel2, DEFAULT_RATES, "2026-10-16", lots, 413.0, "fifo", ["TSM vs 2330 (ADR vs ordinary line)"])
    assert len(blk) == 7 and "8:30 PM ET" in blk[3] and "IRAs" in blk[4] and "2026-10-21" in blk[5] and "2330" in blk[6]
    print("tax_lots smoke test: ok (holding period, HIFO/FIFO/mintax selection, realized and embedded gains, crossings, wash window, tax block)")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(json.dumps(read_lots_csv(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""), indent=1))
    else:
        _smoke()
