"""C1-B1 reference: two 40Ar atoms, kick-drift-kick, exact pair geometry (designer 11th ed.).

docs/current/A_MICRO_V6_C1B1_TWO_ATOM_DYNAMICS_DESIGN_V1.md (contract section). This module DEFINES the
two-atom dynamics; it is slow on purpose and is not a world executor. It does not change the frozen C1-A
contract (a_reference/ar2_lang2024.py): it reads its constants, checks the frozen parameter fingerprint, and
evaluates the same V_real at an ALGEBRAIC input R = sqrt(R^2) (an input-representation extension, not a new
potential).

State per atom: position r (3 components), momentum p (3 components), species "Ar40" -- all position and
momentum components are raw values of one number profile (A-Binary64-Finite or FX(W, F)). No velocity is
stored; the mass comes from the species contract.

One step (Delta t, exact rational, atomic time units):
  1. half kick at the current positions
  2. full drift
  3. half kick at the new positions
Kick: Delta r = r_j - r_i EXACTLY (no rounding), R^2 = Delta r . Delta r EXACTLY, and for each component
      J_k = round( F_real(R) * Delta r_k / R * (Delta t / 2) )     -- rounded ONCE, R = sqrt(R^2) never rounded
      p_j <- round(p_j + J),  p_i <- round(p_i - J)                  -- the same J for both atoms
      (F_real = -dV_real/dR, the frozen C1-A model with retardation ON.)
Drift: r <- round(r + p * Delta t / m) per component, the right side exact, rounded once (Delta t / m is
      never pre-rounded).
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

CONTRACT_VERSION = "c1b1-two-atom-v1"
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

PhysicsDomainExceeded = L.PhysicsDomainExceeded
ReferenceUndecided = L.ReferenceUndecided


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
    R = (lo, hi)                                               # R * 2^M, outward
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


def _decide(profile, value_at):
    """Round the quantity once: refine the enclosure until both ends round alike."""
    M = START_PRECISION_BITS
    while M <= MAX_PRECISION_BITS:
        lo, hi = value_at(M)
        try:
            a = profile.from_exact(lo)
        except VMHalt as h:
            a = ("halt", h.reason)
        try:
            b = profile.from_exact(hi)
        except VMHalt as h:
            b = ("halt", h.reason)
        if a == b:
            if isinstance(a, tuple):
                raise VMHalt(a[1])
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
    r: tuple            # 3 raw profile values
    p: tuple            # 3 raw profile values


@dataclass
class Run:
    profile: object
    dt: Q
    atoms: tuple        # (atom i, atom j)
    t_steps: int = 0
    J_cache: tuple | None = field(default=None, repr=False)


def exact(profile, raws) -> tuple:
    return tuple(profile.to_exact(v) for v in raws)


def relative(profile, a: Atom, b: Atom) -> tuple:
    """Delta r = r_b - r_a, exact."""
    return tuple(y - x for x, y in zip(exact(profile, a.r), exact(profile, b.r)))


def _kick(profile, atoms, J):
    i, j = atoms
    pi = tuple(profile.from_exact(p - q) for p, q in zip(exact(profile, i.p), exact(profile, J)))
    pj = tuple(profile.from_exact(p + q) for p, q in zip(exact(profile, j.p), exact(profile, J)))
    return Atom(i.species, i.r, pi), Atom(j.species, j.r, pj)


def _drift(profile, a: Atom, dt: Q):
    m = SPECIES_MASS[a.species]
    exact_new = tuple(r + p * dt / m for r, p in zip(exact(profile, a.r), exact(profile, a.p)))
    return Atom(a.species, tuple(profile.from_exact(x) for x in exact_new), a.p), exact_new


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
    prof, dt = run.profile, run.dt
    half = dt / 2
    atoms = run.atoms
    J = run.J_cache if run.J_cache is not None else impulse(relative(prof, *atoms), half, prof)
    atoms = _kick(prof, atoms, J)
    a_old = relative(prof, *atoms)
    (ai, ei), (aj, ej) = _drift(prof, atoms[0], dt), _drift(prof, atoms[1], dt)
    atoms = (ai, aj)
    d_exact = tuple(y - x - a for x, y, a in zip(ei, ej, a_old))
    if segment_min_R2(a_old, d_exact) < R_MIN2:
        raise PhysicsDomainExceeded(f"drift segment enters R < r_min at step {run.t_steps + 1}")
    rel = relative(prof, *atoms)
    if sum((x * x for x in rel), Q(0)) < R_MIN2:
        raise PhysicsDomainExceeded(f"stored positions at R < r_min at step {run.t_steps + 1}")
    J = impulse(rel, half, prof)
    run.atoms = _kick(prof, atoms, J)
    run.J_cache = J
    run.t_steps += 1


def new_run(profile, dt: Q, r_i, p_i, r_j, p_j, species=("Ar40", "Ar40")) -> Run:
    """Atoms from exact-rational (or raw-convertible) vectors, each component rounded once to the profile."""
    atoms = tuple(Atom(s, tuple(profile.from_exact(Q(x)) for x in r), tuple(profile.from_exact(Q(x)) for x in p))
                  for s, r, p in ((species[0], r_i, p_i), (species[1], r_j, p_j)))
    R2 = sum((x * x for x in relative(profile, *atoms)), Q(0))
    if R2 < R_MIN2:
        raise PhysicsDomainExceeded("initial state at R < r_min")
    return Run(profile, Q(dt), atoms)


# --- diagnostics (exact where possible; never used by the dynamics) -----------------------------------------

def total_momentum(run: Run) -> tuple:
    return tuple(a + b for a, b in zip(exact(run.profile, run.atoms[0].p), exact(run.profile, run.atoms[1].p)))


def angular_momentum(run: Run) -> tuple:
    out = [Q(0)] * 3
    for a in run.atoms:
        r, p = exact(run.profile, a.r), exact(run.profile, a.p)
        c = (r[1] * p[2] - r[2] * p[1], r[2] * p[0] - r[0] * p[2], r[0] * p[1] - r[1] * p[0])
        out = [o + x for o, x in zip(out, c)]
    return tuple(out)


def kinetic(run: Run) -> Q:
    return sum((sum((x * x for x in exact(run.profile, a.p)), Q(0)) / (2 * SPECIES_MASS[a.species])
                for a in run.atoms), Q(0))


def potential_high(R2: Q, M: int = 256) -> Q:
    """Midpoint of a tight enclosure of V_real(sqrt(R2)) (diagnostic energy, not rounded to a profile)."""
    V = _model(Q(R2), M, L.WORLD_RETARDATION)[0]
    return Q(V[0] + V[1], 2 << M)


def force_high(R2: Q, M: int = 256) -> Q:
    """Midpoint of a tight enclosure of F_real(sqrt(R2)) = -dV/dR (diagnostic only)."""
    dV = _model(Q(R2), M, L.WORLD_RETARDATION)[1]
    return -Q(dV[0] + dV[1], 2 << M)
