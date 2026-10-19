"""Forecast math for stress-test-3: scores, intervals, likelihood-ratio updates, aggregation, coherence checks,
a cluster bootstrap and calibration tables. Standard library only. The ledger commands (check, score, append,
calibrate, init) are in forecast_ledger.py, which imports this file.

    py -3 forecast_tools.py          # smoke test
    from forecast_tools import brier, log_score, quantile_score, wilson, lr_update, replay_updates, \
        aggregate_binary, extremize, dispersion_logodds, cluster_bootstrap, calibration_table

Conventions (references/forecast.md): p is P(the event as worded); for a name against a benchmark it is
P(name beats the benchmark over the horizon), as in the IBKR scorecard. Quantities carry q05..q95 and are
scored by the mean pinball loss over the five levels. Lower scores are better; climatology Brier is 0.25.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

EPS = 1e-6
QLEVELS = (0.05, 0.25, 0.50, 0.75, 0.95)


def clamp(p: float, eps: float = EPS) -> float:
    return min(max(float(p), eps), 1.0 - eps)


def logit(p: float) -> float:
    p = clamp(p)
    return math.log(p / (1.0 - p))


def expit(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# ---------- scores ----------
def brier(p: float, outcome: int) -> float:
    return (float(p) - float(outcome)) ** 2


def log_score(p: float, outcome: int) -> float:
    p = clamp(p)
    return -(outcome * math.log(p) + (1 - outcome) * math.log(1.0 - p))


def hit(p: float, outcome: int) -> Optional[int]:
    """Directional hit; None when p is exactly one half (an explicit no-view is not a call)."""
    if abs(float(p) - 0.5) < 1e-9:
        return None
    return int((float(p) >= 0.5) == (int(outcome) == 1))


def pinball(q: float, y: float, tau: float) -> float:
    d = float(y) - float(q)
    return max(tau * d, (tau - 1.0) * d)


def quantile_score(quantiles: Dict[float, float], y: float) -> float:
    """Mean pinball loss over the quantile levels given (an approximation of CRPS)."""
    return statistics.fmean(pinball(q, y, tau) for tau, q in sorted(quantiles.items()))


def skill_score(scores: Sequence[float], reference: Sequence[float] | float = 0.25) -> float:
    """1 - mean(score) / mean(reference): positive beats the reference (climatology 0.25 by default)."""
    ref = reference if isinstance(reference, (int, float)) else statistics.fmean(reference)
    return 1.0 - statistics.fmean(scores) / float(ref)


# ---------- intervals ----------
def wilson(k: int, n: int, z: float = 1.645) -> Tuple[float, float]:
    """Wilson score interval for k successes in n trials (z 1.645 is 90%, 1.96 is 95%)."""
    if n <= 0:
        return (0.0, 1.0)
    ph = k / n
    den = 1.0 + z * z / n
    cen = (ph + z * z / (2 * n)) / den
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, cen - half), min(1.0, cen + half))


# ---------- updates ----------
def lr_update(p: float, lr: float, cap_log: Optional[float] = math.log(3)) -> float:
    """Posterior after one likelihood ratio, applied in log-odds with an optional cap on |ln lr|."""
    step = math.log(float(lr))
    if cap_log is not None:
        step = max(-cap_log, min(cap_log, step))
    return expit(logit(p) + step)


def replay_updates(prior: float, lrs: Iterable[float], cap_log: Optional[float] = math.log(3),
                   question_cap_log: Optional[float] = math.log(4)) -> float:
    """Posterior from the prior and the full list of ratios; each capped, and the total move capped per question."""
    total = 0.0
    for lr in lrs:
        step = math.log(float(lr))
        if cap_log is not None:
            step = max(-cap_log, min(cap_log, step))
        total += step
    if question_cap_log is not None:
        total = max(-question_cap_log, min(question_cap_log, total))
    return expit(logit(prior) + total)


# ---------- aggregation ----------
def aggregate_binary(ps: Sequence[float], method: str = "median", trim: float = 0.1) -> float:
    ps = [clamp(p) for p in ps]
    if not ps:
        raise ValueError("no forecasts to aggregate")
    if method == "median":
        return statistics.median(ps)
    if method == "mean":
        return statistics.fmean(ps)
    if method == "trimmed_logodds":
        xs = sorted(logit(p) for p in ps)
        k = int(len(xs) * trim)
        xs = xs[k:len(xs) - k] if len(xs) - 2 * k >= 1 else xs
        return expit(statistics.fmean(xs))
    raise ValueError(f"unknown method {method}")


def extremize(p: float, a: float = 1.5) -> float:
    """Push p away from one half in log-odds by factor a. Report it beside the aggregate; never apply it silently."""
    return expit(a * logit(p))


def dispersion_logodds(ps: Sequence[float]) -> float:
    """Inter-quartile spread of the forecasters in log-odds (0 when fewer than two)."""
    xs = sorted(logit(p) for p in ps)
    if len(xs) < 2:
        return 0.0
    qs = statistics.quantiles(xs, n=4, method="inclusive")
    return qs[2] - qs[0]


def quantile_average(sets: Sequence[Dict[float, float]]) -> Dict[float, float]:
    levels = sorted(set().union(*[s.keys() for s in sets]))
    return {t: statistics.fmean(s[t] for s in sets if t in s) for t in levels}


# ---------- coherence ----------
def check_partition(ps: Sequence[float], tol: float = 0.01) -> bool:
    return abs(sum(float(p) for p in ps) - 1.0) <= tol


def check_quantiles(qs: Sequence[float]) -> bool:
    return all(float(a) <= float(b) for a, b in zip(qs, qs[1:]))


def check_conditionals(marginal: float, conditionals: Sequence[float], weights: Sequence[float], tol: float = 0.02) -> bool:
    """P(A) should equal the sum of P(A | B_i) P(B_i) within tol."""
    return abs(sum(float(c) * float(w) for c, w in zip(conditionals, weights)) - float(marginal)) <= tol


# ---------- bootstrap and calibration ----------
def cluster_bootstrap(values_by_cluster: Dict[str, Sequence[float]], stat=statistics.fmean, n_boot: int = 2000,
                      ci: float = 0.80, seed: int = 7) -> Tuple[float, float, float]:
    """Resample clusters (decisions) with replacement; (point, lo, hi) of stat over the pooled values."""
    clusters = [list(v) for v in values_by_cluster.values() if len(v)]
    pooled = [x for c in clusters for x in c]
    if not pooled:
        return (float("nan"), float("nan"), float("nan"))
    point = stat(pooled)
    if len(clusters) < 2:
        return (point, float("nan"), float("nan"))
    rng = random.Random(seed)
    boots = sorted(stat([x for c in (rng.choice(clusters) for _ in clusters) for x in c]) for _ in range(n_boot))
    return (point, boots[int((1 - ci) / 2 * (n_boot - 1))], boots[int((1 + ci) / 2 * (n_boot - 1))])


def calibration_table(pairs: Sequence[Tuple[float, int]], bins: int = 10, z: float = 1.645) -> List[dict]:
    rows = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        sel = [(p, o) for p, o in pairs if (lo <= float(p) < hi) or (b == bins - 1 and float(p) == 1.0)]
        n, k = len(sel), sum(int(o) for _, o in sel)
        w = wilson(k, n, z) if n else (float("nan"), float("nan"))
        rows.append({"bin_lo": lo, "bin_hi": hi, "n": n, "mean_p": statistics.fmean(p for p, _ in sel) if n else float("nan"),
                     "freq": k / n if n else float("nan"), "wilson_lo": w[0], "wilson_hi": w[1]})
    return rows


def _smoke() -> None:
    assert abs(brier(0.7, 1) - 0.09) < 1e-9 and abs(brier(0.7, 0) - 0.49) < 1e-9
    assert hit(0.5, 1) is None and hit(0.6, 1) == 1 and hit(0.6, 0) == 0
    lo, hi = wilson(7, 10)
    assert 0.4 < lo < 0.7 < hi < 0.9
    assert abs(lr_update(0.5, 2.0, cap_log=None) - 2 / 3) < 1e-9
    assert abs(lr_update(0.5, 9.0) - 0.75) < 1e-9, "per-item cap ln 3 should bind"
    assert abs(replay_updates(0.5, [3, 3, 3]) - 0.8) < 1e-9, "per-question cap ln 4 should bind"
    assert abs(aggregate_binary([0.2, 0.5, 0.8]) - 0.5) < 1e-9
    assert abs(aggregate_binary([0.2, 0.5, 0.8], "trimmed_logodds") - 0.5) < 1e-9
    assert extremize(0.7) > 0.7 and extremize(0.3) < 0.3
    assert dispersion_logodds([0.4, 0.5, 0.6]) > 0 and dispersion_logodds([0.5]) == 0
    assert check_partition([0.2, 0.3, 0.5]) and not check_partition([0.2, 0.3, 0.6])
    assert check_quantiles([1, 2, 2, 3, 5]) and not check_quantiles([1, 3, 2, 4, 5])
    assert check_conditionals(0.5, [0.8, 0.2], [0.5, 0.5])
    q = {0.05: 0, 0.25: 1, 0.5: 2, 0.75: 3, 0.95: 4}
    assert abs(quantile_score(q, 2.0) - statistics.fmean(pinball(q[t], 2.0, t) for t in q)) < 1e-9
    pt, lo, hi = cluster_bootstrap({"a": [0.1, 0.2], "b": [0.3, 0.4]}, n_boot=200)
    assert lo <= pt <= hi
    assert sum(r["n"] for r in calibration_table([(0.1, 0), (0.6, 1), (1.0, 1)])) == 3
    print("forecast_tools smoke test: ok (scores, Wilson, LR caps, aggregation, dispersion, coherence, bootstrap, calibration table)")


if __name__ == "__main__":
    _smoke()
