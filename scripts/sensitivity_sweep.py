"""Sensitivity sweep harness for levels 2-4 of the stress-test skill.

Define the decision model as a plain function of named inputs, give each
uncertain input a (low, base, high) range, and this prints the base case,
a tornado-ranked table of one-at-a-time swings, and — on request — the
break-even value of one input (where the output crosses a target).

Usage from a few lines of your own code:

    from sensitivity_sweep import sweep, breakeven

    def model(price, churn, customers):
        return customers * (1 - churn) * price          # any number

    inputs = {
        "price":     (90, 100, 110),      # (low, base, high) — mark each: measured/estimated/inferred
        "churn":     (0.05, 0.10, 0.20),
        "customers": (1000, 1000, 1000),  # fixed: low == base == high
    }
    sweep(model, inputs)
    breakeven(model, inputs, var="churn", target=85_000)   # churn at which output == target

To compare strategies, write one model per strategy (or one model taking a
`strategy` input) and sweep each; an input whose range flips which strategy
leads is a critical uncertainty — the thing worth another lookup.
Run from a copy of this file's directory, or add it to sys.path.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

Range = Tuple[float, float, float]  # (low, base, high)


def _base_kwargs(inputs: Dict[str, Range]) -> Dict[str, float]:
    return {k: v[1] for k, v in inputs.items()}


def sweep(model: Callable[..., float], inputs: Dict[str, Range], label: str = "output") -> Dict[str, Tuple[float, float]]:
    """Print the base case and a tornado-ranked table of one-at-a-time swings.

    Returns {input_name: (value_at_low, value_at_high)} for further use.
    """
    base_kwargs = _base_kwargs(inputs)
    base = model(**base_kwargs)
    print(f"Base case {label}: {base:,.4g}")
    rows = []
    for name, (lo, _, hi) in inputs.items():
        if lo == hi:
            continue  # fixed input, no swing
        kw = dict(base_kwargs)
        kw[name] = lo
        at_lo = model(**kw)
        kw[name] = hi
        at_hi = model(**kw)
        rows.append((abs(at_hi - at_lo), name, at_lo, at_hi))
    rows.sort(reverse=True)
    print(f"\nTornado (swing in {label} across each input's low..high, others at base):")
    for swing, name, at_lo, at_hi in rows:
        print(f"  {name:28s} swing {swing:>12,.4g}   at low {at_lo:>12,.4g}   at high {at_hi:>12,.4g}")
    if rows and rows[0][0] > 0:
        print(f"\nTop-ranked uncertainty: {rows[0][1]} — the fact worth resolving before deciding.")
    return {name: (at_lo, at_hi) for _, name, at_lo, at_hi in rows}


def breakeven(model: Callable[..., float], inputs: Dict[str, Range], var: str, target: float = 0.0,
              lo: float | None = None, hi: float | None = None, iters: int = 80) -> float | None:
    """Find the value of `var` (others at base) where model output crosses `target`, by bisection.

    Searches between `lo` and `hi` (defaults: the input's own low..high range). Returns None if the
    output does not cross the target inside the range — which is itself a finding: the call does not
    flip on this input within its plausible range.
    """
    base_kwargs = _base_kwargs(inputs)
    r = inputs[var]
    lo = r[0] if lo is None else lo
    hi = r[2] if hi is None else hi

    def f(x: float) -> float:
        kw = dict(base_kwargs)
        kw[var] = x
        return model(**kw) - target

    f_lo, f_hi = f(lo), f(hi)
    if f_lo == 0:
        print(f"Break-even {var} = {lo:,.4g}"); return lo
    if f_hi == 0:
        print(f"Break-even {var} = {hi:,.4g}"); return hi
    if (f_lo > 0) == (f_hi > 0):
        print(f"No break-even for {var} within [{lo:,.4g}, {hi:,.4g}]: output stays "
              f"{'above' if f_lo > 0 else 'below'} {target:,.4g} across the whole range.")
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (f_lo > 0):
            lo, f_lo = mid, f(mid)
        else:
            hi = mid
    x = (lo + hi) / 2
    print(f"Break-even {var} = {x:,.4g}  (output crosses {target:,.4g} there; others at base)")
    return x


if __name__ == "__main__":
    # Smoke test with a neutral toy model; replace with your own model in a few lines.
    def toy(a, b, c):
        return a * (1 - b) - c

    demo = {"a": (80.0, 100.0, 120.0), "b": (0.05, 0.10, 0.25), "c": (10.0, 10.0, 10.0)}
    sweep(toy, demo)
    breakeven(toy, demo, var="b", target=75.0)
