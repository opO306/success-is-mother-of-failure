"""Independent radial-quadrature reference for central-force scattering (no integrator code).

A one-degree-of-freedom description is enough: p_r^2(r), dtheta/dr and dt/dr as functions of r.
Used for the true Hamiltonian H (T4 and later problems without a closed form) and for the KDK modified
Hamiltonian H~ = H + h^2 H3 (M7 error predictor). The first turning point reached from outside is used; an orbiting
barrier is handled by a split point at its top (S3) and by the narrow-band check in turning() (S3 fix).
"""
import mpmath as mm

DPS = 80
R0 = 20


def turning(pr2, r_start, r_low='0.005', scan=3000, bisect=320):
    """First root of p_r^2 below r_start; returns the bracket end with p_r^2 > 0 (integrand stays real)."""
    r_low = mm.mpf(r_low)
    prev = mm.mpf(r_start)
    for k in range(1, scan + 1):
        r = r_start * (r_low / r_start) ** (mm.mpf(k) / scan)
        if pr2(r) <= 0:
            lo, hi = r, prev
            break
        prev = r
    else:
        raise ValueError('no turning point above r_low')
    # Just outside an orbiting barrier the forbidden band at the barrier top is ~sqrt(rho) wide and can be narrower
    # than one scan step (S3: rho = +1e-6 band 0.43-0.78 steps; 3 of 6 inputs stepped over it to the inner wall).
    # The band sits at an interior minimum of p_r^2, which the scan cannot miss as a basin: if the outermost such
    # minimum above the bracket's low end is <= 0, the first root is between it and r_start (single crossing above
    # it: a second crossing would need another non-positive minimum further out). The search starts at lo, not at
    # the bracket top, because a band can also lie inside the bracket the scan just found.
    neg = [m for m in minima(pr2, lo, mm.mpf(r_start)) if pr2(m) <= 0]
    if neg:
        lo, hi = max(neg), mm.mpf(r_start)
    # The returned point must stay above the root at ANY precision mpmath.quad later uses. A root fixed at the
    # working precision gave p_r^2 < 0 at higher precision (S2: T3, 2 De, b = 6, h = 40), and an 80-digit root
    # handed to a 60-digit integrand was rounded below the root (S2 fix attempt 1: silent tiny imaginary parts).
    # So: bisect with guard digits, round to the working precision, then add a margin of 1e-(dps-10) relative.
    # The sweep error this adds is O(sqrt(margin)) ~ 1e-35 at 80 digits.
    with mm.workdps(mm.mp.dps + 20):
        for _ in range(bisect + 70):
            mid = (lo + hi) / 2
            if pr2(mid) > 0: hi = mid
            else: lo = mid
    margin = mm.mpf(10) ** (-(mm.mp.dps - 10))
    rt = +hi * (1 + margin)                       # unary + rounds to the working precision
    for _ in range(1000):
        with mm.workdps(mm.mp.dps + 40):
            ok = pr2(rt) > 0
        if ok:
            return rt
        rt = +rt * (1 + margin)
    raise ValueError('turning point not resolved at elevated precision')


def minima(pr2, a, b, n=600, golden=240):
    """Interior local minima of p_r^2 on (a, b): near-orbiting passes have a sharp peak of 1/p_r at the barrier top,
    which the quadrature must see as a subinterval endpoint (S3)."""
    rs = [a + (b - a) * mm.mpf(k) / n for k in range(n + 1)]
    vs = [pr2(r) for r in rs]
    out = []
    phi = (mm.sqrt(5) - 1) / 2
    for k in range(1, n):
        if vs[k] < vs[k - 1] and vs[k] <= vs[k + 1]:
            lo, hi = rs[k - 1], rs[k + 1]
            for _ in range(golden):
                c, d = hi - phi * (hi - lo), lo + phi * (hi - lo)
                if pr2(c) < pr2(d): hi = d
                else: lo = c
            out.append((lo + hi) / 2)
    return out


def legs(pr2, dtheta, dtime, r_start, r1, time=True):
    """Sweep and time from r_start in to the turning point and out to r1. dtheta/dtime take (r, p_r).
    Fails closed when the quadrature error estimate exceeds 10^(-dps/2). time=False skips the time legs (None)."""
    rt = turning(pr2, r_start)
    mins = minima(pr2, rt, max(r_start, r1))
    def leg(R, f):
        s = mm.sqrt(R - rt)
        pts = sorted(set([mm.mpf(0), s / 8, s / 4, s / 2, s] + [mm.sqrt(m - rt) for m in mins if rt < m < R]))
        g = lambda u: 2 * u * f(rt + u * u, mm.sqrt(pr2(rt + u * u)))
        val, err = mm.quad(g, pts, error=True)
        if err > mm.mpf(10) ** (-(mm.mp.dps // 2)):
            raise ValueError(f'quadrature error estimate {mm.nstr(err, 3)} too large')
        return val
    out = (leg(r_start, dtheta) + leg(r1, dtheta), leg(r_start, dtime) + leg(r1, dtime) if time else None, rt)
    if any(isinstance(x, mm.mpc) for x in out[:2]):
        raise ValueError('complex quadrature: p_r^2 < 0 inside the integration range')   # fail closed
    return out


def reference(pot, mu, E, L, r1, r_start=R0, time=True):
    """True-Hamiltonian scattering at finite radius (same output keys as c1b1_method_bench.exact)."""
    with mm.workdps(DPS):
        E, L, r1 = mm.mpf(E), mm.mpf(L), mm.mpf(r1)
        pr2 = lambda r: 2 * mu * (E - pot.V(r)) - L * L / (r * r)
        sweep, t, rt = legs(pr2, lambda r, pr: L / (r * r * pr), lambda r, pr: mu / pr, mm.mpf(r_start), r1, time)
        pr = mm.sqrt(pr2(r1)); pt = L / r1
        c, s = mm.cos(sweep), mm.sin(sweep)
        return dict(sweep=sweep, time=t, r_turn=rt, p_out=[pr * c - pt * s, pr * s + pt * c])


def kdk_modified(pot, mu, q0, p0, h, r1, time=True):
    """Sweep/time along the flow of H~ = H + h^2 H3 (kick-drift-kick, Hairer-Lubich-Wanner 2003 corrected sign):
    H3 = U''(r) p_r^2 / (12 mu^2) + U'(r) L^2 / (12 mu^2 r^3) - U'(r)^2 / (24 mu)   (central force).
    Initial value H~0 from the integrator's own start state (q0, p0)."""
    with mm.workdps(DPS):
        q0, p0, h, r1 = [mm.mpf(x) for x in q0], [mm.mpf(x) for x in p0], mm.mpf(h), mm.mpf(r1)
        r0 = mm.sqrt(q0[0] ** 2 + q0[1] ** 2)
        L = q0[0] * p0[1] - q0[1] * p0[0]
        prr0 = (q0[0] * p0[0] + q0[1] * p0[1]) / r0
        U, d1, d2 = pot.V, pot.dV, pot.d2V
        h2 = h * h
        def c(r): return 1 / (2 * mu) + h2 * d2(r) / (12 * mu * mu)
        def W(r): return L * L / (2 * mu * r * r) + U(r) + h2 * (d1(r) * L * L / (12 * mu * mu * r ** 3) - d1(r) ** 2 / (24 * mu))
        Ht = c(r0) * prr0 ** 2 + W(r0)
        pr2 = lambda r: (Ht - W(r)) / c(r)
        dtheta = lambda r, pr: (L / (mu * r * r) + h2 * d1(r) * L / (6 * mu * mu * r ** 3)) / (2 * c(r) * pr)
        dtime = lambda r, pr: 1 / (2 * c(r) * pr)
        sweep, t, rt = legs(pr2, dtheta, dtime, r0, r1, time)
        return dict(sweep=sweep, time=t, r_turn=rt)
