"""Student-t distribution math for the equities pack (equity_dist.py): the regularized incomplete beta, the t CDF and
inverse CDF by bisection, and a scaled-t distribution object with quantiles, CDF, CVaR and partial expectations from a
400-point quantile grid. Standard library only.

    py -3 student_t.py                     # smoke test
    from student_t import Dist, t_cdf, t_quantile

Dist(mean, sd, df) is mean + scale * t_df with scale chosen so that sd is the standard deviation (df > 2). The grid runs
from p = 1/800 to 1 - 1/800, so grid moments understate the tails a little; quantiles themselves are exact to 1e-12.
"""
from __future__ import annotations

import math
from typing import Dict, List

QL, GRID = (0.05, 0.25, 0.50, 0.75, 0.95), 400


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes, betacf)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > tiny else tiny); h = d
    for m in range(1, 300):
        m2 = 2 * m; aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > tiny else tiny); c = 1 + aa / (c if abs(c) > tiny else tiny); h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > tiny else tiny); c = 1 + aa / (c if abs(c) > tiny else tiny); de = d * c; h *= de
        if abs(de - 1) < 3e-14:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t: float, df: float) -> float:
    """Uses y = t^2/(df + t^2) and the symmetry I_x(a,b) = 1 - I_{1-x}(b,a), so the CDF stays accurate for small |t|."""
    p = 0.5 * (1 - betai(0.5, df / 2, t * t / (df + t * t)))
    return 1 - p if t > 0 else p


def t_quantile(p: float, df: float) -> float:
    lo, hi = -500.0, 500.0
    for _ in range(70):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_cdf(mid, df) < p else (lo, mid)
    return (lo + hi) / 2


_TQ: Dict[float, List[float]] = {}


def t_grid(df: float) -> List[float]:
    """Standard t quantiles at the 400 grid midpoints, cached per df."""
    if df not in _TQ:
        _TQ[df] = [t_quantile((i + 0.5) / GRID, df) for i in range(GRID)]
    return _TQ[df]


class Dist:
    """mean + scale * t_df, with scale set so `sd` is the standard deviation (df > 2)."""

    def __init__(self, mean: float, sd: float, df: float = 4.0):
        self.mean, self.sd, self.df = float(mean), float(sd), float(df)
        self.scale = self.sd * math.sqrt((self.df - 2) / self.df)

    def q(self, p: float) -> float:
        return self.mean + self.scale * t_quantile(p, self.df)

    def cdf(self, x: float) -> float:
        return t_cdf((x - self.mean) / self.scale, self.df) if self.scale > 0 else float(x >= self.mean)

    def grid(self) -> List[float]:
        return [self.mean + self.scale * t for t in t_grid(self.df)]

    def cvar(self, tail: float = 0.10) -> float:
        """Mean of the worst `tail` share of outcomes (a negative number for a loss)."""
        g = self.grid(); k = max(1, int(GRID * tail)); return sum(g[:k]) / k

    def e_pos(self, a: float = 0.0) -> float:
        """E[max(0, X - a)]."""
        return sum(max(0.0, x - a) for x in self.grid()) / GRID

    def e_neg(self, a: float = 0.0) -> float:
        """E[max(0, a - X)]."""
        return sum(max(0.0, a - x) for x in self.grid()) / GRID

    def quantiles(self) -> Dict[str, float]:
        return {f"q{int(p * 100):02d}": self.q(p) for p in QL}


def _smoke() -> None:
    assert abs(t_quantile(0.975, 4) - 2.776) < 2e-3 and abs(t_quantile(0.95, 5) - 2.015) < 2e-3 and abs(t_quantile(0.995, 10) - 3.169) < 2e-3
    assert abs(t_cdf(0, 4) - 0.5) < 1e-12 and abs(t_cdf(2.776, 4) - 0.975) < 1e-4 and abs(t_cdf(-2.776, 4) - 0.025) < 1e-4
    assert abs(betai(1, 1, 0.3) - 0.3) < 1e-12, "I_x(1,1) is x"
    d = Dist(0, 1, 4); g = d.grid()
    assert abs(d.q(0.5)) < 1e-9 and abs(d.cdf(d.q(0.2)) - 0.2) < 1e-9 and d.cvar(0.1) < d.q(0.1) < 0
    sd_grid = math.sqrt(sum(x * x for x in g) / GRID)
    assert 0.75 < sd_grid < 1.0, f"grid sd {sd_grid:.3f} should sit a little under the stated 1.0 (truncated tails)"
    assert abs(d.e_pos(0) - d.e_neg(0)) < 1e-9 and d.e_pos(0) > 0, "symmetric about zero"
    m = Dist(5, 2, 6); assert abs(m.q(0.5) - 5) < 1e-9 and m.q(0.95) > m.q(0.75) > 5
    print(f"student_t smoke test: ok (t quantiles and CDF, incomplete beta, grid sd {sd_grid:.3f}, CVaR, partial expectations)")


if __name__ == "__main__":
    _smoke()
