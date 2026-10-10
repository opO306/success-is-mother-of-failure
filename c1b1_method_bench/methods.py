"""Fixed-step splitting methods on the relative coordinate (mpmath). Coefficients written independently;
tests compare them with the sealed c1b1_integrator_benchmark values.

M0/M1 KDK (outer h = 40 / 20), M2 Yoshida4 (Forest-Ruth composition of three KDK), M3 Chin-Chen 4A.
"""
import mpmath as mm

from .potentials import force, gradient_force


def yoshida_weights():
    s = mm.cbrt(2)
    return 1 / (2 - s), -s / (2 - s)


def kdk(pot, q, p, h, mu):
    f = force(pot, q)
    p = [p[0] + h / 2 * f[0], p[1] + h / 2 * f[1]]
    q = [q[0] + h * p[0] / mu, q[1] + h * p[1] / mu]
    f = force(pot, q)
    return q, [p[0] + h / 2 * f[0], p[1] + h / 2 * f[1]]


def yoshida4(pot, q, p, h, mu):
    w, z = yoshida_weights()
    for c in (w, z, w):
        q, p = kdk(pot, q, p, c * h, mu)
    return q, p


def chin4a(pot, q, p, h, mu):
    f = force(pot, q)
    p = [p[0] + h / 6 * f[0], p[1] + h / 6 * f[1]]
    q = [q[0] + h / 2 * p[0] / mu, q[1] + h / 2 * p[1] / mu]
    g = gradient_force(pot, q, h, mu)
    p = [p[0] + 2 * h / 3 * g[0], p[1] + 2 * h / 3 * g[1]]
    q = [q[0] + h / 2 * p[0] / mu, q[1] + h / 2 * p[1] / mu]
    f = force(pot, q)
    return q, [p[0] + h / 6 * f[0], p[1] + h / 6 * f[1]]


METHODS = dict(kdk=kdk, yoshida4=yoshida4, chin4a=chin4a)
# force evaluations per outer step (adjacent-step reuse not counted): kdk 2 (1 with reuse), yoshida 6 (3), chin 3 + 1 gradient
COST = dict(kdk=1, yoshida4=3, chin4a=3)


def adaptive_kdk(pot, q, p, h, mu, tol, h_min, h_ref=40):
    """M4: step doubling on KDK. Compare one step h with two steps h/2 from the same state; accept the two
    half steps when |dq| + |dp| h / mu <= tol * h / h_ref, otherwise split into two adaptive half steps.
    Deterministic for the same inputs (exact mpmath comparisons on a fixed dyadic ladder down to h_min).
    Not symplectic and not time-reversible (known cost of variable steps)."""
    qc, pc = kdk(pot, q, p, h, mu)
    qm, pm = kdk(pot, q, p, h / 2, mu)
    qf, pf = kdk(pot, qm, pm, h / 2, mu)
    err = mm.sqrt((qf[0] - qc[0]) ** 2 + (qf[1] - qc[1]) ** 2) + \
        mm.sqrt((pf[0] - pc[0]) ** 2 + (pf[1] - pc[1]) ** 2) * h / mu
    if err <= tol * h / h_ref or h / 2 < h_min:
        return qf, pf
    q1, p1 = adaptive_kdk(pot, q, p, h / 2, mu, tol, h_min, h_ref)
    return adaptive_kdk(pot, q1, p1, h / 2, mu, tol, h_min, h_ref)
