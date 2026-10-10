"""Independent radial-quadrature reference for central-force scattering (no integrator code).

A one-degree-of-freedom description is enough: p_r^2(r), dtheta/dr and dt/dr as functions of r.
Used for the true Hamiltonian H (T4 and later problems without a closed form) and for the KDK modified
Hamiltonian H~ = H + h^2 H3 (M7 error predictor). Single accessible turning point only (no orbiting barrier).
"""
import mpmath as mm

DPS = 60
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
    # Bisect with 20 guard digits and accept hi only if p_r^2(hi) > 0 also at 40 guard digits: mpmath.quad raises
    # the working precision internally, and a root fixed at the working precision gave p_r^2 < 0 there
    # (S2 failure: T3, 2 De, b = 6, h = 40: +5.5e-60 at 60 digits, -2.4e-60 at 70+ digits).
    with mm.workdps(mm.mp.dps + 20):
        for _ in range(bisect + 70):
            mid = (lo + hi) / 2
            if pr2(mid) > 0: hi = mid
            else: lo = mid
        step = hi * mm.mpf(10) ** (-(mm.mp.dps - 2))
    with mm.workdps(mm.mp.dps + 40):
        for _ in range(1000):
            if pr2(hi) > 0:
                return hi
            hi += step
    raise ValueError('turning point not resolved at elevated precision')


def legs(pr2, dtheta, dtime, r_start, r1):
    """Sweep and time from r_start in to the turning point and out to r1. dtheta/dtime take (r, p_r)."""
    rt = turning(pr2, r_start)
    def leg(R, f):
        s = mm.sqrt(R - rt)
        g = lambda u: 2 * u * f(rt + u * u, mm.sqrt(pr2(rt + u * u)))
        return mm.quad(g, [0, s / 8, s / 4, s / 2, s])
    out = (leg(r_start, dtheta) + leg(r1, dtheta), leg(r_start, dtime) + leg(r1, dtime), rt)
    if any(isinstance(x, mm.mpc) for x in out[:2]):
        raise ValueError('complex quadrature: p_r^2 < 0 inside the integration range')   # fail closed
    return out


def reference(pot, mu, E, L, r1, r_start=R0):
    """True-Hamiltonian scattering at finite radius (same output keys as c1b1_method_bench.exact)."""
    with mm.workdps(DPS):
        E, L, r1 = mm.mpf(E), mm.mpf(L), mm.mpf(r1)
        pr2 = lambda r: 2 * mu * (E - pot.V(r)) - L * L / (r * r)
        sweep, time, rt = legs(pr2, lambda r, pr: L / (r * r * pr), lambda r, pr: mu / pr, mm.mpf(r_start), r1)
        pr = mm.sqrt(pr2(r1)); pt = L / r1
        c, s = mm.cos(sweep), mm.sin(sweep)
        return dict(sweep=sweep, time=time, r_turn=rt, p_out=[pr * c - pt * s, pr * s + pt * c])


def kdk_modified(pot, mu, q0, p0, h, r1):
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
        sweep, time, rt = legs(pr2, dtheta, dtime, r0, r1)
        return dict(sweep=sweep, time=time, r_turn=rt)
