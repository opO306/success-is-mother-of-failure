"""C1-A reference evaluator for the Ar-Ar potential of Lang, Przybytek, Lesiuk (Phys. Rev. A 109, 052803, 2024).

docs/current/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md (v2) and the C0 numeric plan 11.6 (designer 8th ed.):

  V_real(R)  = V_BO + V_rel + V_QED as the paper's analytic formula, parameters taken as the EXACT
               decimals printed in the published Fortran (not their binary64 roundings);
  A value    = round_profile(V_real(R)): the exact value rounded ONCE. Term order, Horner form,
               cancellation-avoiding branches, CPU/GPU cannot change it.
  force      = -dV_real/dR, derived analytically (the published code has no derivative), rounded once.
  domain     = R >= 1.2 A: every component has ab initio data there. Below it: physics_domain_exceeded
               -- no clamping, no substitute repulsion, no extrapolation claimed as real Ar.

Units: R in bohr, energy in hartree, force in hartree/bohr (the paper's atomic units). Slow on purpose:
this defines the answer, it is not a world executor.

The bohr/angstrom factor BOHR_ANGSTROM (CODATA 2018, the paper's ref. [39]) is a SOURCE-VERSIONED conversion
of this contract only (designer 9th ed.): it reproduces Lang 2024's data and converts the 1.2 A limit.
It does NOT fix A's general angstrom<->bohr constant -- which CODATA edition A uses is decided separately.
The physical meaning of r_min stays "the smallest distance at which all of Lang 2024's V_BO + V_rel + V_QED
have direct ab initio data = 1.2 A".

Method: every transcendental factor e^{-x} is enclosed by the VM's verified integer EXP enclosure;
everything else is exact rational arithmetic. The enclosure of the whole value is tightened until
both ends round to the same profile value. Lindemann-Weierstrass makes an exact tie impossible unless
all transcendental coefficients vanish together; a precision cap turns that case into
ReferenceUndecided instead of a guess.
"""
from __future__ import annotations

from fractions import Fraction as Q
from math import factorial, isqrt

from a_numeric.exp import enclosure as _exp_enclosure
from a_numeric.profiles import VMHalt

# the contract: formula + exact published parameters + r_min + "round once" (+ this source-versioned a0)
CONTRACT_VERSION = "c1a-ar2-lang2024-v1"
# the A world's physics uses retardation ON (frozen, designer 10th ed.); retardation=False is kept only for
# audits and comparison and is not a physics choice of A
WORLD_RETARDATION = True
BOHR_ANGSTROM = Q("0.529177210903")          # CODATA 2018, the paper's ref. [39] -- this contract only, not A's
BOHR_ANGSTROM_SOURCE = "CODATA 2018 (Lang 2024 ref. [39]); source-versioned for c1a-ar2-lang2024-v1 only"
R_MIN_ANGSTROM = Q("1.2")
R_MIN_BOHR = R_MIN_ANGSTROM / BOHR_ANGSTROM
START_PRECISION_BITS = 128
MAX_PRECISION_BITS = 1 << 15


class PhysicsDomainExceeded(Exception):
    reason = "physics_domain_exceeded"


class ReferenceUndecided(Exception):
    """The enclosure never separated from a rounding boundary within MAX_PRECISION_BITS."""


# --- parameters: exact decimals of S2_ar2_pot.f90 (arXiv:2304.14719v2 ancillary file) -------------

def _q(*xs):
    return tuple(Q(x) for x in xs)


# short range: {j: (alpha_j, {i: a_ij})}
BO_SHORT = {1: (Q("6.92639712"), {-1: Q("2.19578828e4"), 0: Q("6.77672149e4"), 1: Q("8.52129476e4"), 2: Q("9.53252754e4")}),
            2: (Q("2.34781022"), {-1: Q("-2.16338828e4"), 0: Q("3.18311293e4"), 1: Q("-8.18603449e3"), 2: Q("8.37564742e2")})}
REL_SHORT = {1: (Q("1.66833595"), {0: Q("-3.55673715e0"), 1: Q("7.59367220e-1"), 2: Q("-4.19874548e-2")}),
             2: (Q("3.07137482"), {0: Q("-2.83560129e1"), 1: Q("1.64892143e1"), 2: Q("7.19542232e0")})}
QED_SHORT = {1: (Q("1.64936036"), {0: Q("-1.2621862e-1"), 1: Q("1.176436e-2"), 2: Q("0")}),
             2: (Q("2.29848003"), {0: Q("0"), 1: Q("0"), 2: Q("6.921721e-2")})}
# long range: (eta, {k: C_2k}, Kadd)  -- the term -C_2k f_{2k+Kadd}(eta R) / R^{2k}
BO_LONG = (Q("3.65946625"), {3: Q("64.2295222"), 4: Q("1503.45262"), 5: Q("49033"), 6: Q("1828012"),
                             7: Q("81913453"), 8: Q("4294913366")}, 1)
REL_LONG = (Q("1.05249333"), {2: Q("-9.43594504e-4"), 3: Q("1.76276088e-1"), 4: Q("3.99787449e-1")}, 0)
QED_LONG = (Q("3.91638946"), {3: Q("-1.949525e-2"), 4: Q("-4.8877359e-1")}, 0)
# retardation factor g(R) = (1 + sum A_m R^m) / (1 + sum B_m R^m)
RET_A = _q("3.064827731712776e-01", "4.843969950480238e-03", "7.793815409352866e-06",
           "1.031221966985517e-14", "4.204140311858030e-12")
RET_B = _q("3.064827731712776e-01", "4.858660928580025e-03", "1.156839432134599e-05",
           "1.670845939899731e-08", "2.151070686307512e-17", "8.769598859882065e-15")
# uncertainty functions sigma_Y = s0 e^{-a0 R} + sum_i s_i e^{-a_i R^2}: ((a0, s0), (a1, s1), ...)
SIGMA_BO = ((Q("1.9"), Q("6.29130076e-1")), (Q("6.81313900e-1"), Q("9.85423065e-1")),
            (Q("5.76343421e-3"), Q("2.56799977e-8")), (Q("2.56907367e-2"), Q("2.93856722e-6")))
SIGMA_REL = ((Q("1.05"), Q("6.76919448e-5")), (Q("1.16451516e-2"), Q("1.95220703e-8")),
             (Q("2.58221232e-1"), Q("1.89517999e-3")), (Q("2.00658289e-3"), Q("6.75730842e-10")))

COMPONENTS = {"BO": (BO_SHORT, BO_LONG), "REL": (REL_SHORT, REL_LONG), "QED": (QED_SHORT, QED_LONG)}


# --- exact interval arithmetic ---------------------------------------------------------------------

class Iv:
    """A closed interval [lo, hi] of exact rationals."""
    __slots__ = ("lo", "hi")

    def __init__(self, lo, hi=None):
        self.lo, self.hi = Q(lo), Q(lo if hi is None else hi)

    def __add__(self, o):
        o = o if isinstance(o, Iv) else Iv(o)
        return Iv(self.lo + o.lo, self.hi + o.hi)

    __radd__ = __add__

    def __neg__(self):
        return Iv(-self.hi, -self.lo)

    def __sub__(self, o):
        return self + (-(o if isinstance(o, Iv) else Iv(o)))

    def __mul__(self, o):
        o = o if isinstance(o, Iv) else Iv(o)
        p = (self.lo * o.lo, self.lo * o.hi, self.hi * o.lo, self.hi * o.hi)
        return Iv(min(p), max(p))

    __rmul__ = __mul__


def _exp_neg(x: Q, M: int) -> Iv:
    """Enclosure of e^{-x}, x >= 0 rational."""
    if x == 0:
        return Iv(1)
    y = -x
    b = max(0, y.numerator.bit_length() - y.denominator.bit_length() + 1)
    lo, hi = _exp_enclosure(y, M, b + 8)
    return Iv(Q(lo, 1 << M), Q(hi, 1 << M))


def _partial_exp_sum(x: Q, n: int) -> Q:
    return sum((x ** i / factorial(i) for i in range(n + 1)), Q(0))


def _damp(n, x, M):
    """f_n(x) = 1 - e^{-x} sum_{i<=n} x^i/i!  and its complement  f_n - 1."""
    t = _exp_neg(x, M) * _partial_exp_sum(x, n)
    return Iv(1) - t, -t


def _damp_deriv(n, x, M):
    """d f_n / dx = e^{-x} x^n / n!  (also the derivative of f_n - 1)."""
    return _exp_neg(x, M) * (x ** n / factorial(n))


def _poly(coefs: dict, R: Q) -> Q:
    return sum((c * R ** i for i, c in coefs.items()), Q(0))


def _poly_deriv(coefs: dict, R: Q) -> Q:
    return sum((i * c * R ** (i - 1) for i, c in coefs.items() if i), Q(0))


def _g(R: Q):
    num = 1 + sum(a * R ** (m + 1) for m, a in enumerate(RET_A))
    den = 1 + sum(b * R ** (m + 1) for m, b in enumerate(RET_B))
    dnum = sum((m + 1) * a * R ** m for m, a in enumerate(RET_A))
    dden = sum((m + 1) * b * R ** m for m, b in enumerate(RET_B))
    return num / den, (dnum * den - num * dden) / (den * den)


# --- the model: enclosures of V and dV/dR ------------------------------------------------------------

def _component(name: str, R: Q, M: int, retarded: bool, deriv: bool) -> Iv:
    short, (eta, C, kadd) = COMPONENTS[name]
    out = Iv(0)
    for alpha, coefs in short.values():
        e = _exp_neg(alpha * R, M)
        out = out + e * ((_poly_deriv(coefs, R) - alpha * _poly(coefs, R)) if deriv else _poly(coefs, R))
    x = eta * R
    kmin = min(C)
    for k, c in C.items():
        n = 2 * k + kadd
        f, f_minus_1 = _damp(n, x, M)
        if retarded and k == kmin and name == "BO":        # C6: g(R) + (f_7 - 1)
            g, dg = _g(R)
            D = f_minus_1 + g
            dD = _damp_deriv(n, x, M) * eta + dg
        elif retarded and k == kmin and name == "REL":     # C4: (f_4 - 1)
            D = f_minus_1
            dD = _damp_deriv(n, x, M) * eta
        else:
            D = f
            dD = _damp_deriv(n, x, M) * eta
        if deriv:   # d/dR [ -c D / R^{2k} ] = -c [ D' / R^{2k} - 2k D / R^{2k+1} ]
            out = out - c * (dD * (1 / R ** (2 * k)) - D * (Q(2 * k) / R ** (2 * k + 1)))
        else:
            out = out - c * D * (1 / R ** (2 * k))
    return out


def _sigma_component(params, R: Q, M: int) -> Iv:
    (a0, s0), *rest = params
    out = _exp_neg(a0 * R, M) * s0
    for a, s in rest:
        out = out + _exp_neg(a * R * R, M) * s
    return out


def _sqrt_iv(v: Iv, M: int) -> Iv:
    lo = max(v.lo, Q(0))
    scale = 1 << (2 * M)
    return Iv(Q(isqrt(lo.numerator * scale // lo.denominator), 1 << M),
              Q(isqrt(-(-v.hi.numerator * scale // v.hi.denominator)) + 1, 1 << M))


def enclose(quantity: str, R: Q, M: int, retardation: bool = True) -> Iv:
    """Enclosure of: 'V', 'dVdR', 'sigma', 'V+sigma', 'V-sigma', or a component 'BO' / 'REL' / 'QED'
    (unretarded, as the published V_BO / V_REL / V_QED functions)."""
    if quantity in COMPONENTS:
        return _component(quantity, R, M, False, False)
    if quantity in ("V", "dVdR"):
        d = quantity == "dVdR"
        return sum((_component(n, R, M, retardation, d) for n in COMPONENTS), Iv(0))
    s = _sqrt_iv(_sigma_component(SIGMA_BO, R, M) * _sigma_component(SIGMA_BO, R, M)
                 + _sigma_component(SIGMA_REL, R, M) * _sigma_component(SIGMA_REL, R, M), M)
    if quantity == "sigma":
        return s
    V = enclose("V", R, M, retardation)
    return V + s if quantity == "V+sigma" else V - s


# --- rounding once ----------------------------------------------------------------------------------

def _round(profile, v: Q):
    try:
        return "value", profile.from_exact(v)
    except VMHalt as h:
        return "halt", h.reason


def check_domain(R: Q) -> None:
    if R < R_MIN_BOHR:
        raise PhysicsDomainExceeded(f"R = {float(R):.6g} bohr < {float(R_MIN_BOHR):.6g} bohr (1.2 A)")


def evaluate(quantity: str, R, profile, retardation: bool = True):
    """round_profile(quantity_real(R)) for an exact R in bohr. Force is -dV/dR (radial)."""
    R = Q(R)
    check_domain(R)
    q, sign = ("dVdR", -1) if quantity == "F" else (quantity, 1)
    M = START_PRECISION_BITS
    while M <= MAX_PRECISION_BITS:
        iv = enclose(q, R, M, retardation)
        if sign < 0:
            iv = -iv
        a, b = _round(profile, iv.lo), _round(profile, iv.hi)
        if a == b:
            if a[0] == "halt":
                raise VMHalt(a[1])
            return a[1]
        M *= 2
    raise ReferenceUndecided(f"{quantity} at R = {R} not decided within {MAX_PRECISION_BITS} bits")


def potential(R, profile, retardation: bool = True):
    return evaluate("V", R, profile, retardation)


def force(R, profile, retardation: bool = True):
    """Radial force F(R) = -dV/dR; the force on atom j from atom i is F(R) (r_j - r_i) / R."""
    return evaluate("F", R, profile, retardation)


def parameter_fingerprint() -> str:
    """sha256 over every constant that defines the contract (exact decimals as reduced fractions)."""
    import hashlib

    parts = [CONTRACT_VERSION, str(BOHR_ANGSTROM), str(R_MIN_ANGSTROM)]
    for name in ("BO", "REL", "QED"):
        short, (eta, C, kadd) = COMPONENTS[name]
        for j in sorted(short):
            alpha, coefs = short[j]
            parts.append(f"{name}.short.{j}:{alpha}:" + ",".join(f"{i}={c}" for i, c in sorted(coefs.items())))
        parts.append(f"{name}.long:{eta}:{kadd}:" + ",".join(f"{k}={c}" for k, c in sorted(C.items())))
    parts.append("RET_A:" + ",".join(map(str, RET_A)))
    parts.append("RET_B:" + ",".join(map(str, RET_B)))
    for name, params in (("SIGMA_BO", SIGMA_BO), ("SIGMA_REL", SIGMA_REL)):
        parts.append(name + ":" + ",".join(f"{a}/{s}" for a, s in params))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()
