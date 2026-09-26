"""C1-B1 reference: two 40Ar atoms, kick-drift-kick, exact pair geometry (designer 11th ed.).

docs/current/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md (contract section). This module DEFINES the
two-atom dynamics; it is slow on purpose and is not a world executor. It does not change the frozen C1-A
contract (a_reference/ar2_lang2024.py): it reads its constants, checks the frozen parameter fingerprint, and
evaluates the same V_real at an ALGEBRAIC input R = sqrt(R^2) (an input-representation extension, not a new
potential).

State per atom: position r (3 components), momentum p (3 components), species "Ar40" -- all position and
momentum components are raw values of a POSITION profile and a MOMENTUM profile (typed, designer 13th ed.; the
same profile when untyped: A-Binary64-Finite or FX(W, F)). No velocity is
stored; the mass comes from the species contract.

One step (Delta t, exact rational, atomic time units):
  1. half kick at the current positions
  2. full drift
  3. half kick at the new positions
Kick: Delta r = r_j - r_i EXACTLY (no rounding), R^2 = Delta r . Delta r EXACTLY, and for each component
      J_k = round( F_real(R) * Delta r_k / R * (Delta t / 2) )     -- rounded ONCE, R = sqrt(R^2) never rounded
      p_j <- round(p_j + J),  p_i <- round(p_i - J)                  -- the same J for both atoms
      (F_real = -dV_real/dR, the frozen C1-A model with retardation ON.)
Drift: delta r = round_pos(p * Delta t / m) per component -- the DISPLACEMENT rounded once to the position grid
      (Delta t / m is never pre-rounded) -- then r <- r + delta r, an exact integer move on the grid (designer
      14th ed.). Rounding r + p dt/m as a whole made an exact half-unit tie follow the parity of the absolute
      position, breaking translation invariance; the displacement alone has no origin. Away from ties both
      definitions give the same bits. A position that leaves the profile's range is ExecutorLimitExceeded,
      never wrapped or saturated. (Binary64 positions, disqualified in the 12th ed., round r + delta r again.)
Guard: after every drift the exact minimum of |Delta r_old + s (Delta r_exact_new - Delta r_old)|^2 over
      s in [0, 1] -- the relative straight line the drift describes before the positions are rounded -- and the
      stored new R^2 must both be >= r_min^2; otherwise PhysicsDomainExceeded (no clamp, no reflection, no
      step rejection, no interpolation).
If the enclosure of J cannot decide one rounded value within MAX_PRECISION_BITS: ReferenceUndecided.

The second half kick of a step and the first half kick of the next act on the same positions, so the same J;
`run` reuses it (the value is identical by definition -- a cache, not an approximation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as Q
from math import isqrt

import a_reference.ar2_lang2024 as L
from a_numeric.exp import enclosure as _exp_enclosure
from a_numeric.profiles import VMHalt

CONTRACT_VERSION = "c1b1-two-atom-v2"          # v2: the drift rounds the displacement (14th ed.)
FROZEN_C1A_FINGERPRINT = "ada6153be05af3e582139fdc81b5697fffaf18d12f9f2de6e8d5ac2fdfe0839e"
if L.parameter_fingerprint() != FROZEN_C1A_FINGERPRINT or L.CONTRACT_VERSION != "c1a-ar2-lang2024-v1":
    raise ImportError("the frozen C1-A contract changed -- C1-B1 is defined on c1a-ar2-lang2024-v1 only")

# --- species contract: 40Ar (designer 11th ed., D1). Source-versioned for C1-B1, nominal values only. -------
AR40_MASS_U = Q("39.9623831237")                 # NIST Atomic Weights and Isotopic Compositions
AR40_MASS_U_UNCERTAINTY = "39.9623831237(24) u"  # provenance only: measurement uncertainty is not rounding error
ELECTRON_MASS_U = Q("5.485799090441e-4")         # CODATA 2022
ELECTRON_MASS_U_UNCERTAINTY = "5.485799090441(97)e-4 u"
MASS_SOURCES = "m(40Ar): NIST Atomic Weights and Isotopic Compositions; u -> m_e: CODATA 2022 (C1-B1 only)"
AR40_MASS_ME = AR40_MASS_U / ELECTRON_MASS_U     # exact rational, in electron masses
SPECIES_MASS = {"Ar40": AR40_MASS_ME}

R_MIN2 = L.R_MIN_BOHR ** 2
START_PRECISION_BITS = 128
MAX_PRECISION_BITS = 1 << 14

# --- three kinds of refusal, never merged (designer 13th ed. item 2) -----------------------------------------
PhysicsDomainExceeded = L.PhysicsDomainExceeded      # the physics contract (Lang 2024, r >= 1.2 A) does not cover it


class IntegratorDomainExceeded(Exception):
    """The physics is defined, but the integrator contract (dt = 40 a.u., validated for E_rel <= 10 De) does not
    vouch for it -- e.g. a 1.01 V(r_min) head-on collision that dt = 40 would silently reflect above r_min."""
    reason = "integrator_domain_exceeded"


class ExecutorLimitExceeded(Exception):
    """An implementation capability ran out (precision cap, number width, native range)."""
    reason = "executor_limit_exceeded"


class ReferenceUndecided(ExecutorLimitExceeded, L.ReferenceUndecided):
    """The enclosure never separated from a rounding boundary within MAX_PRECISION_BITS."""
    reason = "executor_limit_exceeded"


# --- integrator contract (designer 12th / 13th ed.) -------------------------------------------------------------
DT_DEFAULT = Q(40)                                   # a.u.; 10 and 20 kept for convergence audits, 80 / 160 coarse
DE_CONTRACT = Q("0.000451995775")                    # the frozen model's well depth, 12 digits (hartree)
INTEGRATOR_E_MAX = 10 * DE_CONTRACT                  # validated: relative energy E_rel <= 10 De (inclusive)
INTEGRATOR_DOMAIN = "c1b1-v1: two 40Ar atoms, E_rel = K_rel + V_real <= 10 De (De = 0.000451995775 hartree)"


# --- fixed-point intervals at 2^-M: (lo, hi) ints, the real value in [lo, hi] / 2^M ---------------------------

def _mul(a, b, M):
    p = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return min(p) >> M, -((-max(p)) >> M)


def _add(a, b):
    return a[0] + b[0], a[1] + b[1]


def _neg(a):
    return -a[1], -a[0]


def _const(c: Q, M):
    n = c.numerator << M
    return n // c.denominator, -((-n) // c.denominator)


def _scale(a, c: Q):
    """a * c for an exact rational c (the scale 2^M is kept)."""
    x, y = a[0] * c.numerator, a[1] * c.numerator
    lo, hi = min(x, y), max(x, y)
    return lo // c.denominator, -((-hi) // c.denominator)


def _div_small(a, d: int):
    return a[0] // d, -((-a[1]) // d)


def _div_pos(a, b, M):
    """a / b for b > 0."""
    q = [(x << M) for x in a]
    c = [q[i] // b[j] for i in (0, 1) for j in (0, 1)]
    d = [-((-q[i]) // b[j]) for i in (0, 1) for j in (0, 1)]
    return min(c), max(d)


def _exp_neg(x, M):
    """e^-x for x = [lo, hi] / 2^M >= 0."""
    if x[0] >= 4096 << M:
        return 0, 1
    def enc(end):
        return _exp_enclosure(Q(-end, 1 << M), M, max(0, end.bit_length() - M + 1) + 8)
    return enc(x[1])[0], enc(x[0])[1]     # the larger argument gives the lower end


def _const_cache(M, cache={}):
    if M not in cache:
        comps = {}
        for name, (short, (eta, C, kadd)) in L.COMPONENTS.items():
            shorts = [(_const(alpha, M), alpha, {i: c for i, c in coefs.items()}) for alpha, coefs in short.values()]
            comps[name] = (shorts, _const(eta, M), eta, kadd, C)
        cache[M] = comps
    return cache[M]


def _model(R2: Q, M: int, ret: bool):
    """Enclosures (V, dV/dR, 1/R) at 2^-M for R = sqrt(R2), R2 rational >= r_min^2."""
    s = R2 * (1 << (2 * M))
    lo = isqrt(s.numerator // s.denominator)
    hi = isqrt(-((-s.numerator) // s.denominator))
    if hi * hi < -((-s.numerator) // s.denominator):
        hi += 1
    return _model_R((lo, hi), M, ret)                          # R * 2^M, outward


def _model_R(R: tuple, M: int, ret: bool):
    """Enclosures (V, dV/dR, 1/R) at 2^-M valid for EVERY R in [R[0], R[1]] / 2^M (interval arithmetic throughout;
    R[0] > 0). _model passes the enclosure of one sqrt(R2); interval audits pass a whole cell."""
    lo, hi = R
    one = 1 << M
    pw = {0: (one, one), 1: R}
    for i in range(2, 7):
        pw[i] = _mul(pw[i - 1], R, M)
    inv = {n: ((1 << (M * (n + 1))) // (hi ** n), -((-(1 << (M * (n + 1)))) // (lo ** n))) for n in range(1, 18)}

    def power(i):                                              # R^i, any integer i in [-17, 6]
        return pw[i] if i >= 0 else inv[-i]

    V = dV = (0, 0)
    for name, (shorts, eta_iv, eta, kadd, C) in _const_cache(M).items():
        for alpha_iv, alpha, coefs in shorts:
            E = _exp_neg(_mul(alpha_iv, R, M), M)
            P = dP = (0, 0)
            for i, c in coefs.items():
                if c == 0:
                    continue
                P = _add(P, _scale(power(i), c))
                if i:
                    dP = _add(dP, _scale(power(i - 1), c * i))
            V = _add(V, _mul(E, P, M))
            dV = _add(dV, _mul(E, _add(dP, _neg(_scale(P, alpha))), M))
        x = _mul(eta_iv, R, M)
        E = _exp_neg(x, M)
        piece = total = (one, one)
        done = 0
        kmin = min(C)
        for k in sorted(C):
            n = 2 * k + kadd
            for i in range(done + 1, n + 1):
                piece = _div_small(_mul(piece, x, M), i)
                total = _add(total, piece)
            done = n
            T = _mul(E, total, M)                              # e^-x sum_{i<=n} x^i/i!
            dD = _scale(_mul(E, piece, M), eta)                # d f_n(eta R)/dR = eta e^-x x^n/n!
            if ret and k == kmin and name == "BO":             # g + f - 1 = g - T
                N = Dn = (one, one)
                dN = dDn = (0, 0)
                for m, a in enumerate(L.RET_A):
                    N = _add(N, _scale(pw[m + 1], a))
                    dN = _add(dN, _scale(pw[m], a * (m + 1)))
                for m, b in enumerate(L.RET_B):
                    Dn = _add(Dn, _scale(pw[m + 1], b))
                    dDn = _add(dDn, _scale(pw[m], b * (m + 1)))
                g = _div_pos(N, Dn, M)
                dg = _div_pos(_add(_mul(dN, Dn, M), _neg(_mul(N, dDn, M))), _mul(Dn, Dn, M), M)
                D = _add(g, _neg(T))
                dD = _add(dD, dg)
            elif ret and k == kmin and name == "REL":          # f - 1 = -T
                D = _neg(T)
            else:
                D = _add((one, one), _neg(T))
            c = C[k]
            V = _add(V, _neg(_scale(_mul(D, power(-2 * k), M), c)))
            dV = _add(dV, _neg(_scale(_mul(dD, power(-2 * k), M), c)))
            dV = _add(dV, _scale(_mul(D, power(-2 * k - 1), M), c * 2 * k))
    return V, dV, inv[1]


@dataclass(frozen=True)
class _Halt:
    reason: str


def _decide(profile, value_at):
    """Round the quantity once: refine the enclosure until both ends round alike."""
    M = START_PRECISION_BITS
    while M <= MAX_PRECISION_BITS:
        lo, hi = value_at(M)
        try:
            a = profile.from_exact(lo)
        except VMHalt as h:
            a = _Halt(h.reason)
        try:
            b = profile.from_exact(hi)
        except VMHalt as h:
            b = _Halt(h.reason)
        if a == b:
            if isinstance(a, _Halt):
                raise VMHalt(a.reason)
            return a
        M *= 2
    raise ReferenceUndecided(f"not decided within {MAX_PRECISION_BITS} bits")


def potential(R2: Q, profile, retardation: bool = True):
    """round(V_real(sqrt(R2))) -- the algebraic-input extension of the frozen C1-A V."""
    R2 = Q(R2)
    if R2 < R_MIN2:
        raise PhysicsDomainExceeded(f"R^2 = {float(R2):.6g} < r_min^2")

    def at(M):
        V = _model(R2, M, retardation)[0]
        return Q(V[0], 1 << M), Q(V[1], 1 << M)
    return _decide(profile, at)


def radial_force(R2: Q, profile, retardation: bool = True):
    """round(-dV_real/dR at sqrt(R2)) -- diagnostic; the world kick never stores it."""
    R2 = Q(R2)
    if R2 < R_MIN2:
        raise PhysicsDomainExceeded(f"R^2 = {float(R2):.6g} < r_min^2")

    def at(M):
        dV = _model(R2, M, retardation)[1]
        return Q(-dV[1], 1 << M), Q(-dV[0], 1 << M)
    return _decide(profile, at)


def impulse(dr: tuple, dt_kick: Q, profile) -> tuple:
    """J_k = round(F_real(R) dr_k / R * dt_kick) for each component, R = sqrt(dr . dr), retardation ON."""
    R2 = sum((x * x for x in dr), Q(0))
    if R2 < R_MIN2:
        raise PhysicsDomainExceeded(f"R^2 = {float(R2):.6g} < r_min^2")
    cache = {}

    def G(M):                                                  # F / R = -dV/dR * (1/R), enclosure at 2^-M
        if M not in cache:
            _, dV, inv1 = _model(R2, M, L.WORLD_RETARDATION)
            cache[M] = _mul(_neg(dV), inv1, M)
        return cache[M]
    out = []
    for x in dr:
        c = x * dt_kick
        if c == 0:
            out.append(profile.from_exact(0))
            continue

        def at(M, c=c):
            lo, hi = G(M)
            a, b = Q(lo, 1 << M) * c, Q(hi, 1 << M) * c
            return min(a, b), max(a, b)
        out.append(_decide(profile, at))
    return tuple(out)


# --- state and stepping -------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Atom:
    species: str
    r: tuple            # 3 raw values of the POSITION profile
    p: tuple            # 3 raw values of the MOMENTUM profile


@dataclass
class Run:
    pos: object         # position profile
    mom: object         # momentum profile (J is a momentum quantity: rounded to this profile)
    dt: Q
    atoms: tuple        # (atom i, atom j)
    t_steps: int = 0
    J_cache: tuple | None = field(default=None, repr=False)
    validated_only: bool = True
    drift: str = "v2"   # "v2" (interim default) or "v1" -- for the drift comparison (14th ed.) only

    @property
    def profile(self):
        """The single profile of an untyped run (position and momentum alike). Typed runs must say which."""
        if self.pos is not self.mom:
            raise AttributeError("typed run: use run.pos or run.mom")
        return self.pos


def exact(profile, raws) -> tuple:
    return tuple(profile.to_exact(v) for v in raws)


def relative(profile, a: Atom, b: Atom) -> tuple:
    """Delta r = r_b - r_a, exact (profile = the POSITION profile)."""
    return tuple(y - x for x, y in zip(exact(profile, a.r), exact(profile, b.r)))


def _kick(mom, atoms, J):
    i, j = atoms
    pi = tuple(_limit(mom.from_exact, p - q) for p, q in zip(exact(mom, i.p), exact(mom, J)))
    pj = tuple(_limit(mom.from_exact, p + q) for p, q in zip(exact(mom, j.p), exact(mom, J)))
    return Atom(i.species, i.r, pi), Atom(j.species, j.r, pj)


def _limit(fn, *args):
    """Run a profile operation; a range halt is an implementation capability running out."""
    try:
        return fn(*args)
    except VMHalt as h:
        raise ExecutorLimitExceeded(f"{h.reason} in {getattr(fn, '__name__', fn)}") from h


def drift_momentum(mom, raws) -> tuple:
    """The momentum the drift moves with: the stored value, except for a carry profile (its coarse part only)."""
    f = getattr(mom, "drift_exact", None)
    return tuple(f(v) for v in raws) if f else exact(mom, raws)


def displacement(pos, mom, a: Atom, dt: Q) -> tuple:
    """delta r = round_pos(p dt / m) per component (raw values of the position profile)."""
    m = SPECIES_MASS[a.species]
    return tuple(_limit(pos.from_exact, p * dt / m) for p in drift_momentum(mom, a.p))


def _drift(pos, mom, a: Atom, dt: Q, rule: str = "v2"):
    """(new atom, exact unrounded end point r + p dt / m). The end point feeds only the r_min segment guard.
    rule "v1" is the retired round(r + p dt / m), kept only for the drift comparison (designer 14th ed.)."""
    m = SPECIES_MASS[a.species]
    exact_new = tuple(r + p * dt / m for r, p in zip(exact(pos, a.r), drift_momentum(mom, a.p)))
    if rule == "v1":
        r_new = tuple(_limit(pos.from_exact, x) for x in exact_new)
    elif rule == "v2":
        r_new = tuple(_limit(pos.add, r, d) for r, d in zip(a.r, displacement(pos, mom, a, dt)))
    else:
        raise ValueError(f"unknown drift rule {rule!r}")
    return Atom(a.species, r_new, a.p), exact_new


def _half_even(num: int, den: int) -> int:
    """round(num / den) to nearest, ties to even (den > 0); odd-symmetric: round(-x) = -round(x)."""
    q, r = divmod(num, den)
    if 2 * r > den or (2 * r == den and q & 1):
        q += 1
    return q


class CarryMomentum:
    """Momentum-comparison candidate (designer 15th ed.): a COARSE momentum on the 2^-48 grid (int64, what the drift
    moves with) plus a RESIDUAL on a fine 2^-FINE grid that keeps every sub-grid impulse. Raw value = (c, r),
    exact value c 2^-48 + r 2^-FINE, |r| <= half a coarse unit (2^(FINE-49)). Every kick lands exactly on the fine
    grid, then the total is split again (c = round-half-even of the total on the coarse grid) -- so impulses too
    small for the coarse grid accumulate instead of vanishing, and a whole coarse unit is carried when they add up.
    The split is odd-symmetric (+-J give exactly opposite states) and done once per kick on an exact integer total
    (order-independent when several pair impulses are summed first). Not a VM profile, not a contract."""
    COARSE = 48

    def __init__(self, fine: int = 111, width: int = 64) -> None:
        self.fine, self.width = fine, width
        self.unit = 1 << (fine - self.COARSE)                     # one coarse unit in fine raws
        self.name = f"CARRY(FX({width},{self.COARSE})+2^-{fine})"

    def _split(self, v: int) -> tuple:
        c = _half_even(v, self.unit)
        if not -(1 << (self.width - 1)) <= c < (1 << (self.width - 1)):
            raise VMHalt("overflow")
        return c, v - c * self.unit

    def from_exact(self, value) -> tuple:
        x = Q(value)
        return self._split(_half_even(x.numerator << self.fine, x.denominator))

    def to_exact(self, v) -> Q:
        return Q(v[0] * self.unit + v[1], 1 << self.fine)

    def drift_exact(self, v) -> Q:
        return Q(v[0], 1 << self.COARSE)

    def neg(self, v) -> tuple:
        return -v[0], -v[1]


class ExactPosition:
    """Drift-comparison candidate 3 (designer 14th ed.): positions stored EXACTLY (rational), so the drift keeps
    every sub-grid remainder and never rounds -- equivalent to an integer position in units of the displacement
    quantum (2^-48 dt / m) with the remainder kept. Same range as FX(96,48) (|r| < 2^47 bohr). Not a VM profile and
    not a contract: a measurement device. v1 and v2 coincide on it (nothing is rounded)."""
    name = "EXACT"
    LIMIT = Q(1 << 47)

    def _check(self, v: Q) -> Q:
        if not -self.LIMIT <= v < self.LIMIT:
            raise VMHalt("overflow")
        return v

    def from_exact(self, value) -> Q:
        return self._check(Q(value))

    def to_exact(self, v) -> Q:
        return v

    def add(self, a, b) -> Q:
        return self._check(a + b)

    def neg(self, a) -> Q:
        return self._check(-a)


def segment_min_R2(a: tuple, d: tuple) -> Q:
    """min over s in [0, 1] of |a + s d|^2, exact."""
    dd = sum((x * x for x in d), Q(0))
    ad = sum((x * y for x, y in zip(a, d)), Q(0))
    aa = sum((x * x for x in a), Q(0))
    if dd == 0:
        return aa
    s = min(max(-ad / dd, Q(0)), Q(1))
    return aa + 2 * s * ad + s * s * dd


def step(run: Run) -> None:
    pos, mom, dt = run.pos, run.mom, run.dt
    half = dt / 2
    atoms = run.atoms
    J = run.J_cache if run.J_cache is not None else impulse(relative(pos, *atoms), half, mom)
    atoms = _kick(mom, atoms, J)
    a_old = relative(pos, *atoms)
    (ai, ei), (aj, ej) = (_drift(pos, mom, a, dt, rule=run.drift) for a in atoms)
    atoms = (ai, aj)
    d_exact = tuple(y - x - a for x, y, a in zip(ei, ej, a_old))
    if segment_min_R2(a_old, d_exact) < R_MIN2:
        raise PhysicsDomainExceeded(f"drift segment enters R < r_min at step {run.t_steps + 1}")
    rel = relative(pos, *atoms)
    if sum((x * x for x in rel), Q(0)) < R_MIN2:
        raise PhysicsDomainExceeded(f"stored positions at R < r_min at step {run.t_steps + 1}")
    J = impulse(rel, half, mom)
    run.atoms = _kick(mom, atoms, J)
    run.J_cache = J
    run.t_steps += 1


# --- relative energy and the integrator domain ----------------------------------------------------------------

def relative_kinetic(p_i: tuple, p_j: tuple, m_i: Q, m_j: Q) -> Q:
    """K_rel = |P|^2 / (2 mu), P = (m_i p_j - m_j p_i) / (m_i + m_j), mu = m_i m_j / (m_i + m_j). Exact.
    (Equal masses with p_i = -p_j: P = p_j and K_rel = |p_j|^2 / (2 mu) = |p_j|^2 / m.)"""
    M = m_i + m_j
    P = tuple((m_i * b - m_j * a) / M for a, b in zip(p_i, p_j))
    mu = m_i * m_j / M
    return sum((x * x for x in P), Q(0)) / (2 * mu)


def relative_energy_enclosure(run: Run, M: int) -> tuple:
    """[lo, hi] of E_rel = K_rel + V_real(sqrt(R^2)) (retardation ON), exact rationals."""
    i, j = run.atoms
    K = relative_kinetic(exact(run.mom, i.p), exact(run.mom, j.p), SPECIES_MASS[i.species], SPECIES_MASS[j.species])
    R2 = sum((x * x for x in relative(run.pos, i, j)), Q(0))
    V = _model(R2, M, L.WORLD_RETARDATION)[0]
    return K + Q(V[0], 1 << M), K + Q(V[1], 1 << M)


def check_integrator_domain(run: Run) -> None:
    """IntegratorDomainExceeded unless E_rel <= INTEGRATOR_E_MAX; decided on a refined enclosure, never guessed."""
    M = START_PRECISION_BITS
    while M <= MAX_PRECISION_BITS:
        lo, hi = relative_energy_enclosure(run, M)
        if hi <= INTEGRATOR_E_MAX:
            return
        if lo > INTEGRATOR_E_MAX:
            raise IntegratorDomainExceeded(
                f"E_rel = {float(lo):.6g} hartree = {float(lo / DE_CONTRACT):.10g} De > 10 De ({INTEGRATOR_DOMAIN})")
        M *= 2
    raise ReferenceUndecided("E_rel vs 10 De not decided")


def new_run(profile, dt: Q, r_i, p_i, r_j, p_j, species=("Ar40", "Ar40"), momentum_profile=None,
            validated_only: bool = True, drift: str = "v2") -> Run:
    """Atoms from exact-rational vectors: positions rounded once to `profile`, momenta to `momentum_profile`
    (default: the same profile). validated_only=False skips the integrator-domain check -- ONLY for the
    domain-guard stress tests, whose results are not A-world physics."""
    mom = momentum_profile or profile
    atoms = tuple(Atom(s, tuple(profile.from_exact(Q(x)) for x in r), tuple(mom.from_exact(Q(x)) for x in p))
                  for s, r, p in ((species[0], r_i, p_i), (species[1], r_j, p_j)))
    R2 = sum((x * x for x in relative(profile, *atoms)), Q(0))
    if R2 < R_MIN2:
        raise PhysicsDomainExceeded("initial state at R < r_min")
    run = Run(profile, mom, Q(dt), atoms, validated_only=validated_only, drift=drift)
    if validated_only:
        check_integrator_domain(run)
    return run


# --- diagnostics (exact where possible; never used by the dynamics) -----------------------------------------

def total_momentum(run: Run) -> tuple:
    return tuple(a + b for a, b in zip(exact(run.mom, run.atoms[0].p), exact(run.mom, run.atoms[1].p)))


def angular_momentum(run: Run) -> tuple:
    out = [Q(0)] * 3
    for a in run.atoms:
        r, p = exact(run.pos, a.r), exact(run.mom, a.p)
        c = (r[1] * p[2] - r[2] * p[1], r[2] * p[0] - r[0] * p[2], r[0] * p[1] - r[1] * p[0])
        out = [o + x for o, x in zip(out, c)]
    return tuple(out)


def kinetic(run: Run) -> Q:
    """Total kinetic energy sum |p|^2 / (2 m) (lab frame)."""
    return sum((sum((x * x for x in exact(run.mom, a.p)), Q(0)) / (2 * SPECIES_MASS[a.species])
                for a in run.atoms), Q(0))


def potential_high(R2: Q, M: int = 256) -> Q:
    """Midpoint of a tight enclosure of V_real(sqrt(R2)) (diagnostic energy, not rounded to a profile)."""
    V = _model(Q(R2), M, L.WORLD_RETARDATION)[0]
    return Q(V[0] + V[1], 2 << M)


def force_high(R2: Q, M: int = 256) -> Q:
    """Midpoint of a tight enclosure of F_real(sqrt(R2)) = -dV/dR (diagnostic only)."""
    dV = _model(Q(R2), M, L.WORLD_RETARDATION)[1]
    return -Q(dV[0] + dV[1], 2 << M)
