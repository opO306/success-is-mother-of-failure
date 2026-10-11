"""S3b: how the per-collision KDK error near an orbiting edge shows up in a viscosity-type cross section.

Finite-range definition, the same for every method so that only the integrator difference is measured:
  start inbound at R0 with impact parameter b, stop outbound at R0;  chi_fin = sweep + 2 alpha - pi,
  alpha = atan2(L / R0, |p_r(R0)|) (the same for the true flow and for the KDK modified flow, which starts from the
  same state and conserves H~, so |p_r(R0)| out = in);  Q2_fin = 2 pi int_0^b_cap sin^2(chi_fin) b db.
The tail beyond R0 and b > b_cap are excluded identically for all methods (this is not the physical Q^(2)).

KDK is represented by its modified Hamiltonian H~ = H + h^2 H3 (M7; S2/S3 measured/predicted 0.99999-1.00025).
The b integral uses s = -ln|rho| around b_orb (rho = b/b_orb - 1): the log winding of chi near the orbit becomes a
steady oscillation in s, and db = b_orb e^-s ds. |rho| < rho_min is excluded and bounded separately.
Gauss-Kronrod 7/15 per panel; G7 vs K15 is the per-panel error estimate.
"""
import mpmath as mm

from . import orbit, quadref
from .potentials import MU
from .run import R0, initial

# QUADPACK qk15 abscissae (non-negative half) and weights; Gauss 7 uses xgk[1], xgk[3], xgk[5], xgk[7].
# Used ONLY as Newton starting values and as an outside cross-check: typed from memory, one of them is wrong near
# digit 27 (S3b test run 1: x^2 moment off by 3e-27). The rule itself is computed from its definition in _rule().
XGK = ['0.991455371120812639206854697526329', '0.949107912342758524526189684047851',
       '0.864864423359769072789712788640926', '0.741531185599394439863864773280788',
       '0.586087235467691130294144845693013', '0.405845151377397166906606412076961',
       '0.207784955007898467600689403773245', '0']
WGK = ['0.022935322010529224963732008058970', '0.063092092629978553290700663189204',
       '0.104790010322250183839876322541518', '0.140653259715525918745189590510238',
       '0.169004726639267902826583426598550', '0.190350578064785409913256402421014',
       '0.204432940075298892414161999234649', '0.209482141084727828012999174891714']
WG = ['0.129484966168869693270611432679082', '0.279705391489276667901467771423780',
      '0.381830050505118944950369775488975', '0.417959183673469387755102040816327']


_RULES = {}


def _rule(dps):
    """(x >= 0, Kronrod weight, Gauss weight) from the definitions, at dps digits (+20 guard):
    Gauss 7: roots of P7, w = 2 (1 - x^2) / (49 P6(x)^2)  (from P7' = 7 (P6 - x P7) / (1 - x^2) at a root).
    Kronrod 15: the 15-point rule containing the G7 nodes that integrates x^0..x^22 exactly (8 new nodes, by symmetry
    4 positive nodes + 8 weights = 12 unknowns for the 12 even moments), solved by Newton from the QUADPACK values."""
    if dps in _RULES:
        return _RULES[dps]
    with mm.workdps(dps + 20):
        g = [mm.findroot(lambda t: mm.legendre(7, t), mm.mpf(XGK[i])) for i in (1, 3, 5)] + [mm.mpf(0)]
        wg = [2 * (1 - x * x) / (49 * mm.legendre(6, x) ** 2) for x in g]
        def eqs(*u):
            bs, w = u[:4], u[4:]              # w: weights of g1, g2, g3, 0, b1..b4
            out = []
            for m in range(0, 23, 2):
                s = (w[3] if m == 0 else 0) + 2 * sum(w[i] * g[i] ** m for i in range(3)) + \
                    2 * sum(w[4 + j] * bs[j] ** m for j in range(4))
                out.append(s - mm.mpf(2) / (m + 1))
            return out
        x0 = [mm.mpf(XGK[i]) for i in (0, 2, 4, 6)] + [mm.mpf(WGK[i]) for i in (1, 3, 5, 7)] + \
             [mm.mpf(WGK[i]) for i in (0, 2, 4, 6)]
        u = mm.findroot(eqs, x0)
        bs, w = [u[i] for i in range(4)], [u[i] for i in range(4, 12)]
        rule = [(g[i], w[i], wg[i]) for i in range(4)] + [(bs[j], w[4 + j], mm.mpf(0)) for j in range(4)]
    _RULES[dps] = rule
    return rule


def gk15(a, b):
    """Nodes on [a, b] with Kronrod and Gauss weights (Gauss weight 0 on Kronrod-only nodes)."""
    a, b = mm.mpf(a), mm.mpf(b)
    c, h = (a + b) / 2, (b - a) / 2
    out = []
    for x, wk, wg in _rule(mm.mp.dps):
        for sgn in ((1,) if x == 0 else (-1, 1)):
            out.append((c + sgn * h * x, h * wk, h * wg))
    return out


def panels(E_frac, pot, b_cap, rho_min, width):
    """Panel list [(side, a, b)] in the variable of each side. side 'in'/'out': s-variable; 'plain': b itself."""
    E = orbit.e_max(pot) * mm.mpf(E_frac)
    if mm.mpf(E_frac) >= 1:
        n = int(mm.ceil(b_cap / width))
        return E, None, [('plain', b_cap * k / n, b_cap * (k + 1) / n) for k in range(n)]
    b_orb = orbit.orbit(pot, MU, E)['b_orb']
    if not b_orb < b_cap:
        raise ValueError('b_orb beyond b_cap')
    S = -mm.log(rho_min)
    out = []
    for side, s0 in (('in', mm.mpf(0)), ('out', -mm.log(b_cap / b_orb - 1))):
        k = 0
        while s0 + k * width < S:
            out.append((side, s0 + k * width, min(s0 + (k + 1) * width, S)))
            k += 1
    return E, b_orb, out


def b_of(side, x, b_orb):
    """Impact parameter and Jacobian db/dx (positive orientation of the b integral)."""
    if side == 'plain':
        return x, mm.mpf(1)
    e = mm.exp(-x)
    return (b_orb * (1 - e), b_orb * e) if side == 'in' else (b_orb * (1 + e), b_orb * e)


def node(pot, E, b, hs=(40, 20)):
    """sin^2(chi_fin) for the true flow and for each KDK modified flow at impact parameter b."""
    with mm.workdps(quadref.DPS):
        q0, p0, L = initial(pot, MU, mm.mpf(E), mm.mpf(b))
        alpha = mm.atan2(p0[1], -p0[0])
        true = quadref.reference(pot, MU, E, L, mm.mpf(R0), time=False)['sweep']
        mods = {h: quadref.kdk_modified(pot, MU, q0, p0, h, mm.mpf(R0), time=False)['sweep'] for h in hs}
        s2 = lambda sw: mm.sin(sw + 2 * alpha - mm.pi) ** 2
        return dict(sin2_true=s2(true), sin2={h: s2(m) for h, m in mods.items()},
                    d_sweep={h: mods[h] - true for h in hs}, sweep_true=true)
