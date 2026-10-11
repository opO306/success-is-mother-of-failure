"""Continuous reference V2 for planar central-force scattering by radial quadrature (no time stepping).

Why V2: the sealed c1b1_o1.continuous (hash-pinned by the O-1 input, cause-isolation and dt40-benchmark seals; left
unchanged) finds the turning point with a linear scan of ~0.0043 bohr and has no split point at the barrier top.
Just outside an orbiting barrier (rho -> +0) the forbidden band at the barrier top is ~sqrt(rho) wide; at
rho = +1e-8 ... +1e-10 it is narrower than that scan step, and continuous stopped (Unresolved) on 12 of 18 bench
inputs (method bench S3c, X check).

V2 (independent re-implementation; imports mpmath only, takes V as a callable, no force):
  * every interior minimum of p_r^2(r) = 2 mu (H - V) - L^2 / r^2 (the barrier tops of the effective potential) is
    located on a log grid and refined by bisection on the sign of d(p_r^2)/dr (mpmath.diff, guard digits);
  * the turning point is the first root of p_r^2 below the start radius: if the outermost interior minimum above the
    first non-positive grid point is itself <= 0, the root lies between that minimum and the grid point above it
    (single crossing on the rising side of the basin); otherwise it lies in the first non-positive grid bracket;
  * the root is returned on the allowed side, checked at +40 digits;
  * the radial quadrature in u (r = r_t + u^2) is split geometrically towards u = 0 and around every interior
    minimum; near u = 0 a Taylor series of p_r^2 about r_t is used;
  * fail closed (Unresolved): no turning point, non-positive or non-real integrand, quadrature error estimate above
    10^-(dps/2), or (check=True) sweep/time differing by more than 10^-(dps/2) between dps and dps + 20 digits.
Assumption (not proven): basin features of p_r^2 are wider than the log-grid step (n = 3000 between r_lo and r0);
the barrier-top basin of the bench and Ar potentials is ~1 bohr wide.
The callable V must evaluate at the working precision (construct parameterised potentials at >= dps + 40 digits).
"""
import mpmath as mm


class Unresolved(ValueError):
    pass


def _principal(x):
    return mm.atan2(mm.sin(x), mm.cos(x))


def _minima(g, rs, gv, guard):
    """Refined interior minima of g from grid values gv at radii rs (rs decreasing)."""
    out = []
    for k in range(1, len(rs) - 1):
        if gv[k] < gv[k - 1] and gv[k] <= gv[k + 1]:
            lo, hi = rs[k + 1], rs[k - 1]
            with mm.workdps(mm.mp.dps + guard):
                for _ in range(int((mm.mp.dps + guard) * 3.4) + 20):
                    mid = (lo + hi) / 2
                    if mm.diff(g, mid) > 0:
                        hi = mid
                    else:
                        lo = mid
            out.append(((lo + hi) / 2, k))
    return out


def _root(g, lo, hi, dps):
    """Root of g in (lo, hi) with g(lo) <= 0 < g(hi); returns a point just above it where g > 0 at +40 digits."""
    with mm.workdps(dps + 30):
        for _ in range(int((dps + 30) * 3.4) + 20):
            mid = (lo + hi) / 2
            if g(mid) > 0:
                hi = mid
            else:
                lo = mid
    rt = +hi
    step = mm.mpf(10) ** (-(dps - 5))
    for _ in range(200):
        with mm.workdps(dps + 40):
            if g(rt) > 0:
                return rt
        rt = +rt * (1 + step)
    raise Unresolved('turning point not on the allowed side at elevated precision')


def turning_point(g, r0, dps, r_lo=2, n=3000, use_minima=True):
    """(r_t, interior minima list) for the first root of g below r0. use_minima=False exists for fault injection."""
    r0, r_lo = mm.mpf(r0), mm.mpf(r_lo)
    rs = [r0 * (r_lo / r0) ** (mm.mpf(k) / n) for k in range(n + 1)]
    gv = [g(r) for r in rs]
    first = next((k for k in range(1, n + 1) if gv[k] <= 0), None)
    if first is None:
        raise Unresolved('no turning point above r_lo')
    mins = _minima(g, rs[:first + 2], gv[:first + 2], 20) if use_minima else []
    above = [(m, k) for m, k in mins if m > rs[first]]
    neg = [(m, k) for m, k in above if g(m) <= 0]
    if neg:
        m, k = max(neg, key=lambda t: t[0])
        hi = rs[k - 1]
        if not g(hi) > 0:
            raise Unresolved('no positive grid point above the outermost non-positive minimum')
        rt = _root(g, m, hi, dps)
    else:
        rt = _root(g, rs[first], rs[first - 1], dps)
    return rt, [m for m, _ in mins if m > rt]


def _leg(g, rt, R, mins, weight, dps, taylor):
    """Integral over r in (rt, R] of weight(r) / sqrt(g(r)) dr, with r = rt + u^2."""
    U = mm.sqrt(R - rt)
    pts = {mm.mpf(0), U}
    for k in range(1, 31):
        pts.add(U * mm.mpf(4) ** -k)
    for m in mins:
        if rt < m < R:
            um = mm.sqrt(m - rt)
            pts.add(um)
            for k in range(1, 21):
                for s in (1, -1):
                    x = um * (1 + s * mm.mpf(4) ** -k)
                    if 0 < x < U:
                        pts.add(x)
    pts = sorted(pts)
    small = mm.mpf(10) ** (-dps / 3)

    def f(u):
        dr = u * u
        if dr < small:
            z = sum(c * dr ** i for i, c in enumerate(taylor))
        else:
            z = g(rt + dr) / dr
        if isinstance(z, mm.mpc) or not z > 0:
            raise Unresolved('radial integrand non-positive or not real')
        return 2 * weight(rt + dr) / mm.sqrt(z)

    val, err = mm.quad(f, pts, error=True, maxdegree=8)
    if isinstance(val, mm.mpc) or not mm.isfinite(val) or err > mm.mpf(10) ** (-dps / 2):
        raise Unresolved(f'quadrature error estimate {mm.nstr(err, 3)} exceeds 10^-(dps/2)')
    return val, err


def _scatter_once(V, mu, q, p, r_exit, dps, use_minima):
    with mm.workdps(dps):
        q, p = [mm.mpf(x) for x in q], [mm.mpf(x) for x in p]
        mu, r_exit = mm.mpf(mu), mm.mpf(r_exit)
        r0 = mm.sqrt(q[0] ** 2 + q[1] ** 2)
        if q[0] * p[0] + q[1] * p[1] >= 0 or r_exit < r0:
            raise Unresolved('requires an inbound start and an outbound radius >= the start radius')
        H = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + V(r0)
        L = q[0] * p[1] - q[1] * p[0]
        if L < 0:
            raise Unresolved('negative L not supported')
        g = lambda r: 2 * mu * (H - V(r)) - L * L / (r * r)
        rt, mins = turning_point(g, r0, dps, use_minima=use_minima)
        with mm.workdps(dps + 20):
            taylor = [mm.diff(g, rt, n) / mm.factorial(n) for n in range(1, 8)]
        a0, e0 = _leg(g, rt, r0, mins, lambda r: L / (r * r), dps, taylor)
        a1, e1 = _leg(g, rt, r_exit, mins, lambda r: L / (r * r), dps, taylor)
        t0, e2 = _leg(g, rt, r0, mins, lambda r: mu, dps, taylor)
        t1, e3 = _leg(g, rt, r_exit, mins, lambda r: mu, dps, taylor)
        theta = a0 + a1
        radial, tangential = mm.sqrt(g(r_exit)), L / r_exit
        direction = _principal(theta + mm.atan2(tangential, radial) + mm.atan2(q[1], q[0]))
        po = [radial * mm.cos(theta) - tangential * mm.sin(theta), radial * mm.sin(theta) + tangential * mm.cos(theta)]
        return dict(r_min=rt, sweep=theta, time=t0 + t1, chi=_principal(direction - mm.atan2(p[1], p[0])),
                    direction=direction, H=H, L=L, p_out_x=po[0], p_out_y=po[1], quadrature_error=max(e0, e1, e2, e3),
                    barrier_tops=mins)


def scatter(V, mu, q, p, r_exit, dps=60, check=True, use_minima=True):
    """Same output keys as c1b1_o1.continuous.scatter (strings at dps digits) plus precision_diff and barrier_tops."""
    a = _scatter_once(V, mu, q, p, r_exit, dps, use_minima)
    diff = None
    if check:
        b = _scatter_once(V, mu, q, p, r_exit, dps + 20, use_minima)
        with mm.workdps(dps + 20):
            diff = max(abs(a['sweep'] - b['sweep']), abs(a['time'] - b['time']) / b['time'])
        if diff > mm.mpf(10) ** (-dps / 2):
            raise Unresolved(f'result changes by {mm.nstr(diff, 3)} between {dps} and {dps + 20} digits')
    with mm.workdps(dps):
        out = {k: mm.nstr(v, dps) for k, v in a.items() if k != 'barrier_tops'}
        out['barrier_tops'] = [mm.nstr(m, 30) for m in a['barrier_tops']]
        out['precision_diff'] = mm.nstr(diff, 6) if diff is not None else None
        return out
