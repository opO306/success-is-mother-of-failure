"""Continuous reference for several exit radii of ONE collision (T7, survey_only), built on c1b1_cont2.

Every state T7 verifies (level 0, each ladder pair's fine run, the accepted output and its base-grid round-back)
belongs to the same collision and differs only in the exit radius r_e (all just outside R0 = 20). cont2.scatter would
repeat the turning point, the barrier-top search and both radial legs for each of them (28-93 s per Ar call). Here:
    sweep(r_e) = 2 A(R0) + int_{R0}^{r_e} L / (r^2 p_r) dr,   time(r_e) = 2 T(R0) + int_{R0}^{r_e} mu / p_r dr
A(R0), T(R0) are cont2's radial legs from the turning point to the start radius R0 (the outgoing leg to R0 is the
same integral); the short tail R0 -> r_e is far from the turning point (p_r^2 > 0, smooth). Requires r0 = |q| (the
start radius) and r_e within (r0 - 1, r0 + 5). Fail closed (cont2.Unresolved) as cont2: tail quadrature error above
10^-(dps/2), or (check=True) any result changing by more than 10^-(dps/2) between dps and dps + 20 digits.
"""
import mpmath as mm

from c1b1_cont2 import scatter as c2

Unresolved = c2.Unresolved


def _once(V, mu, q, p, r_exits, dps):
    with mm.workdps(dps):
        q, p = [mm.mpf(x) for x in q], [mm.mpf(x) for x in p]
        mu = mm.mpf(mu)
        r0 = mm.sqrt(q[0] ** 2 + q[1] ** 2)
        if q[0] * p[0] + q[1] * p[1] >= 0:
            raise Unresolved('requires an inbound start')
        H = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + V(r0)
        L = q[0] * p[1] - q[1] * p[0]
        if L < 0:
            raise Unresolved('negative L not supported')
        g = lambda r: 2 * mu * (H - V(r)) - L * L / (r * r)
        rt, mins = c2.turning_point(g, r0, dps)
        with mm.workdps(dps + 20):
            taylor = [mm.diff(g, rt, n) / mm.factorial(n) for n in range(1, 8)]
        a0, _ = c2._leg(g, rt, r0, mins, lambda r: L / (r * r), dps, taylor)
        t0, _ = c2._leg(g, rt, r0, mins, lambda r: mu, dps, taylor)
        out = []
        for re in r_exits:
            re = mm.mpf(re)
            if not r0 - 1 < re < r0 + 5:
                raise Unresolved('exit radius outside the tail range')
            fa = lambda r: L / (r * r * mm.sqrt(g(r)))
            ft = lambda r: mu / mm.sqrt(g(r))
            da, ea = mm.quad(fa, [r0, re], error=True)
            dt, et = mm.quad(ft, [r0, re], error=True)
            if isinstance(da, mm.mpc) or isinstance(dt, mm.mpc) or max(ea, et) > mm.mpf(10) ** (-dps / 2):
                raise Unresolved('tail quadrature not resolved')
            out.append((2 * a0 + da, 2 * t0 + dt))
        return out, rt, H, L


def scatter_many(V, mu, q, p, r_exits, dps=40, check=True):
    """List of dict(sweep, time) (strings at dps digits) for each exit radius, plus r_min and precision_diff."""
    a, rt, H, L = _once(V, mu, q, p, r_exits, dps)
    diff = None
    if check:
        b, _, _, _ = _once(V, mu, q, p, r_exits, dps + 20)
        with mm.workdps(dps + 20):
            diff = max(max(abs(x[0] - y[0]), abs(x[1] - y[1]) / y[1]) for x, y in zip(a, b))
        if diff > mm.mpf(10) ** (-dps / 2):
            raise Unresolved(f'result changes by {mm.nstr(diff, 3)} between {dps} and {dps + 20} digits')
    with mm.workdps(dps):
        return dict(exits=[dict(sweep=mm.nstr(s, dps), time=mm.nstr(t, dps)) for s, t in a],
                    r_min=mm.nstr(rt, dps), H=mm.nstr(H, dps), L=mm.nstr(L, dps),
                    precision_diff=mm.nstr(diff, 6) if diff is not None else None)
