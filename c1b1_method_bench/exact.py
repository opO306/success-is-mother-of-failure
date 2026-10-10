"""Closed-form finite-radius scattering for the bench problems. Shares no code with the integrators.

Geometry: start at q0 = (R0, 0) moving inward with angular momentum L >= 0; the exact orbit is evaluated
at any outbound radius r1 (the integrator's actual exit radius), so no interpolation is needed.
Returns sweep (polar angle travelled), time, r_turn and the outbound momentum vector at r1.
"""
import mpmath as mm


def _out_momentum(V, mu, E, L, r1, sweep):
    pr = mm.sqrt(2 * mu * (E - V(r1)) - L * L / (r1 * r1))
    pt = L / r1
    c, s = mm.cos(sweep), mm.sin(sweep)
    return [pr * c - pt * s, pr * s + pt * c]


def free(mu, E, L, R0, r1):
    """Straight line from geometry (independent of the 1/r^2 formula with alpha = 0)."""
    p = mm.sqrt(2 * mu * E)
    pr0 = mm.sqrt(p * p - (L / R0) ** 2)
    q0, v = [mm.mpf(R0), mm.mpf(0)], [-pr0 / mu, L / R0 / mu]
    vv = v[0] ** 2 + v[1] ** 2
    qv = q0[0] * v[0] + q0[1] * v[1]
    t = (-qv + mm.sqrt(qv * qv - vv * (R0 * R0 - r1 * r1))) / vv
    q1 = [q0[0] + v[0] * t, q0[1] + v[1] * t]
    sweep = mm.atan2(q1[1], q1[0])
    if L > 0 and sweep < 0:
        sweep += 2 * mm.pi
    return dict(sweep=sweep, time=t, r_turn=L / p, p_out=[mu * v[0], mu * v[1]])


def inv_square(alpha, mu, E, L, R0, r1):
    p = mm.sqrt(2 * mu * E)
    K = mm.sqrt(L * L + 2 * mu * alpha)
    sweep = (L / K) * (mm.acos(K / (p * R0)) + mm.acos(K / (p * r1)))
    time = mu / p ** 2 * (mm.sqrt(p * p * R0 * R0 - K * K) + mm.sqrt(p * p * r1 * r1 - K * K))
    V = lambda r: alpha / r ** 2
    return dict(sweep=sweep, time=time, r_turn=K / p, p_out=_out_momentum(V, mu, E, L, r1, sweep))


def coulomb(alpha, mu, E, L, R0, r1):
    p = mm.sqrt(2 * mu * E)
    ma = mu * alpha
    r_turn = (ma + mm.sqrt(ma * ma + p * p * L * L)) / (p * p)
    if L == 0:
        sweep = mm.mpf(0)
    else:
        A = mm.sqrt(p * p + ma * ma / (L * L))
        w = lambda r: L / r + ma / L
        sweep = mm.acos(w(R0) / A) + mm.acos(w(r1) / A)
    def t(r):
        Q = p * p * r * r - 2 * ma * r - L * L
        Q = Q if Q > 0 else mm.mpf(0)
        return mu * (mm.sqrt(Q) / p ** 2 + ma / p ** 3 *
                     mm.log((2 * p * mm.sqrt(Q) + 2 * p * p * r - 2 * ma) / (2 * p * p * r_turn - 2 * ma)))
    V = lambda r: alpha / r
    return dict(sweep=sweep, time=t(R0) + t(r1), r_turn=r_turn, p_out=_out_momentum(V, mu, E, L, r1, sweep))
