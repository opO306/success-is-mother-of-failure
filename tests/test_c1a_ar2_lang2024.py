"""C1-A: the Ar-Ar reference evaluator (Lang, Przybytek, Lesiuk 2024) against independent routes.

docs/current/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md (v2), C0 numeric plan 11.6 (designer 8th ed.).
The reference defines the A value as round_profile(V_real(R)); the audit (audit/independent_physics)
parses the published Fortran, encloses V with mpmath intervals and differentiates numerically.
Tests needing the published files on D:\\reference skip when they are absent.
"""
from __future__ import annotations

import ast
import math
import struct
from fractions import Fraction as Q
from pathlib import Path

import pytest

import a_reference.ar2_lang2024 as L
from a_numeric import Binary64Finite, FixedPoint, VMHalt
from audit.independent_numeric.oracle import SIGN, _interval, value

F64 = Binary64Finite()
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(r"D:\reference\ar2_lang2024")
HAVE_DATA = (DATA / "S2_ar2_pot.f90").exists() and (DATA / "S1_abinitio.txt").exists()
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="published Lang 2024 files not on D:\\reference")
HARTREE_CM = Q("219474.6313632")            # CODATA 2018


def bits(x: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def R_of(angstrom: float) -> Q:
    """The binary64 value nearest to the distance in bohr, as the exact R the tests use."""
    return Q(float(Q(str(angstrom)) / L.BOHR_ANGSTROM))


GRID_A = ([1.2, 1.25, 1.4, 1.6, 1.8, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2, 3.4, 3.5, 3.6, 3.7, 3.76, 3.8, 3.9, 4.0, 4.2, 4.5,
           5.0, 5.5, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0, 50.0]
          + [1.2 + 0.137 * i for i in range(1, 60)])
GRID = [R_of(a) for a in GRID_A] + [Q(250), Q(1000), Q(10000)]


@pytest.fixture(scope="module")
def audit():
    if not HAVE_DATA:
        pytest.skip("published files absent")
    from audit.independent_physics.ar2_lang2024 import Model, parse_fortran
    return Model(parse_fortran())


def ref(q, R, retardation=True):
    return L.evaluate(q, R, F64, retardation)


def in_rounding_interval(x: Q, result: int) -> bool:
    m = result & ~SIGN
    lo, hi = _interval(m)
    return lo <= (-x if result >> 63 else x) <= hi


# --- independence and transcription --------------------------------------------------------------

def test_audit_imports_neither_reference_nor_vm() -> None:
    for path in (ROOT / "audit" / "independent_physics").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            for n in names:
                assert n.split(".")[0] not in ("a_reference", "a_numeric", "engine"), (path.name, n)


@needs_data
def test_parameters_are_the_published_decimals() -> None:
    from audit.independent_physics.ar2_lang2024 import parse_fortran
    p = parse_fortran()

    def short(d, comp, imin):
        alphas = [Q(s) for s in p[f"alpha_{comp}"]]
        a = [Q(s) for s in p[f"a_{comp}"]]
        per = len(a) // len(alphas)
        return {j + 1: (alphas[j], {imin + t: a[j * per + t] for t in range(per)}) for j in range(len(alphas))}

    assert L.BO_SHORT == short(p, "BO", -1)
    assert L.REL_SHORT == short(p, "REL", 0)
    assert L.QED_SHORT == short(p, "QED", 0)
    for comp, kmin, long in (("BO", 3, L.BO_LONG), ("REL", 2, L.REL_LONG), ("QED", 3, L.QED_LONG)):
        assert long[0] == Q(p[f"eta_{comp}"][0])
        assert long[1] == {kmin + t: Q(s) for t, s in enumerate(p[f"C_{comp}"])}
    assert L.RET_A == tuple(Q(s) for s in p["A"]) and L.RET_B == tuple(Q(s) for s in p["B"])
    for name, mine in (("aS_BO", L.SIGMA_BO), ("aS_REL", L.SIGMA_REL)):
        v = [Q(s) for s in p[name]]
        assert mine == tuple((v[2 * i], v[2 * i + 1]) for i in range(len(v) // 2))


# --- values: correctly rounded, retardation on and off, +-sigma ------------------------------------

@needs_data
@pytest.mark.parametrize("quantity", ["V", "sigma", "V+sigma", "V-sigma"])
def test_reference_is_correctly_rounded(quantity, audit) -> None:
    from audit.independent_physics.ar2_lang2024 import judge_b64
    for R in GRID:
        for ret in ((True, False) if quantity == "V" else (True,)):
            assert judge_b64(audit, quantity, R, ref(quantity, R, ret), ret) is None, (quantity, float(R), ret)


@needs_data
def test_components_reproduce_the_ab_initio_corrections(audit) -> None:
    """The fitted rel and QED corrections against the paper's own ab initio points (S1)."""
    from audit.independent_physics.ar2_lang2024 import judge_b64
    rows = [l.split() for l in (DATA / "S1_abinitio.txt").read_text().splitlines()[1:] if l.strip()]
    assert len(rows) == 37
    worst = {"REL": 0.0, "QED": 0.0}
    for r in rows:
        R = Q(r[0]) / L.BOHR_ANGSTROM
        for comp, col in (("REL", 7), ("QED", 9)):
            got = ref(comp, R)
            assert judge_b64(audit, comp, R, got) is None
            z = abs(float(value(got)) - float(r[col])) / float(r[col + 1])
            worst[comp] = max(worst[comp], z)
    assert worst["REL"] < 1 and worst["QED"] < 1          # measured: 0.33 and 0.66 data-sigmas


# --- the shape: minimum, repulsion, attraction, asymptotics ---------------------------------------

def _find_Re():
    lo, hi = 7.0, 7.3                     # bohr; F > 0 (repulsive) below R_e
    while True:
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            return lo, hi
        if value(ref("F", Q(mid))) > 0:
            lo = mid
        else:
            hi = mid


def test_minimum_position_and_depth() -> None:
    lo, hi = _find_Re()
    Re = Q(lo) * L.BOHR_ANGSTROM
    assert abs(Re - Q("3.7640")) <= Q("0.0014")                      # paper Table V: 3.7640(14) A
    De = value(ref("V", Q(lo))) * HARTREE_CM
    assert abs(De - Q("-99.20")) <= Q("0.37")                        # paper Table V: -99.20(37) cm^-1
    assert abs(De - Q("-99.201606")) < Q("1e-5")                     # 60-digit transcription check


def test_short_range_repulsion_and_long_range_attraction() -> None:
    Re = Q(_find_Re()[0])
    for R in GRID:
        F = value(ref("F", R))
        assert (F > 0) == (R < Re), float(R)
    assert value(ref("V", L.R_MIN_BOHR)) > 1                         # ~1.80 hartree at 1.2 A
    zero_cross = [R for R in GRID if R < Re and value(ref("V", R)) < 0]
    assert zero_cross and min(zero_cross) > R_of(3.3)


def test_long_range_asymptotics_and_retardation() -> None:
    # without retardation the relativistic R^-4 term dominates far away: V ~ -C4 / R^4
    C4 = L.REL_LONG[1][2]
    for R in (Q(10 ** 5), Q(10 ** 6)):
        assert abs(value(ref("V", R, False)) * R ** 4 / -C4 - 1) < Q(1, 100)
    # with retardation that unphysical term is gone and the potential falls faster than R^-6
    # (Casimir-Polder); what remains far out is the tiny unretarded QED R^-6 term (paper: not attempted)
    Rs = [Q(500), Q(1000), Q(2000), Q(4000)]
    scaled = [abs(value(ref("V", R))) * R ** 6 for R in Rs]
    assert all(a > b for a, b in zip(scaled, scaled[1:]))
    assert all(value(ref("V", R)) < 0 for R in Rs)


# --- analytic force against numerical differentiation -----------------------------------------------

@needs_data
def test_analytic_force_matches_numerical_derivative(audit) -> None:
    from audit.independent_physics.ar2_lang2024 import dVdR_numeric
    for R in GRID:
        for ret in (True, False):
            assert in_rounding_interval(dVdR_numeric(audit, R, 80, ret), ref("F", R, ret)), (float(R), ret)


# --- domain ------------------------------------------------------------------------------------------

def test_domain_boundary() -> None:
    ref("V", L.R_MIN_BOHR)                                            # exactly 1.2 A: allowed
    below = Q(math.nextafter(float(L.R_MIN_BOHR), 0))
    if below >= L.R_MIN_BOHR:
        below = Q(math.nextafter(float(below), 0))
    for q in ("V", "F", "sigma", "V+sigma", "REL"):
        with pytest.raises(L.PhysicsDomainExceeded) as info:
            ref(q, below)
        assert info.value.reason == "physics_domain_exceeded"
    with pytest.raises(L.PhysicsDomainExceeded):
        ref("V", Q(1))                                                # 0.53 A: never extrapolated


def test_other_profiles_round_the_same_value() -> None:
    fx = FixedPoint(64, 32)
    for R in GRID[:40]:
        v = L.enclose("V", R, 400)
        got = fx.to_exact(L.evaluate("V", R, fx))
        assert abs(got - v.lo) <= Q(1, 2 ** 33) + (v.hi - v.lo)
    with pytest.raises(VMHalt):                                        # 1.80 hartree does not fit FX(8,7) (max 127/128)
        L.evaluate("V", L.R_MIN_BOHR, FixedPoint(8, 7))


# --- fault injection --------------------------------------------------------------------------------

def _float_V(R: Q, retardation=True) -> int:
    """Fortran-like binary64 evaluation (every operation rounded) -- a plausible fast implementation."""
    r = float(R)

    def damp(n, x):
        return 1 - math.exp(-x) * sum(x ** i / math.factorial(i) for i in range(n + 1))
    v = 0.0
    for short, (eta, C, kadd), comp in ((L.BO_SHORT, L.BO_LONG, "BO"), (L.REL_SHORT, L.REL_LONG, "REL"),
                                        (L.QED_SHORT, L.QED_LONG, "QED")):
        for alpha, coefs in short.values():
            v += math.exp(-float(alpha) * r) * sum(float(c) * r ** i for i, c in coefs.items())
        kmin = min(C)
        for k, c in C.items():
            f = damp(2 * k + kadd, float(eta) * r)
            if retardation and k == kmin and comp == "BO":
                num = 1 + sum(float(a) * r ** (m + 1) for m, a in enumerate(L.RET_A))
                den = 1 + sum(float(b) * r ** (m + 1) for m, b in enumerate(L.RET_B))
                f = num / den + f - 1
            elif retardation and k == kmin and comp == "REL":
                f = f - 1
            v -= float(c) * f / r ** (2 * k)
    return bits(v)


@needs_data
def test_float_evaluation_is_not_the_reference(audit) -> None:
    """A Fortran-like double evaluation differs from the correctly rounded value somewhere."""
    from audit.independent_physics.ar2_lang2024 import judge_b64
    wrong = sum(judge_b64(audit, "V", R, _float_V(R)) is not None for R in GRID)
    assert wrong > 0


@needs_data
def test_injected_model_defects_are_caught(audit, monkeypatch) -> None:
    from audit.independent_physics.ar2_lang2024 import dVdR_numeric, judge_b64
    # 1. one digit of C6 changed
    eta, C, kadd = L.BO_LONG
    monkeypatch.setattr(L, "BO_LONG", (eta, {**C, 3: Q("64.2295223")}, kadd))
    monkeypatch.setitem(L.COMPONENTS, "BO", (L.BO_SHORT, L.BO_LONG))
    assert any(judge_b64(audit, "V", R, ref("V", R)) is not None for R in GRID)
    monkeypatch.undo()
    # 2. BO damped with f_{2k} instead of f_{2k+1}
    monkeypatch.setitem(L.COMPONENTS, "BO", (L.BO_SHORT, (eta, C, 0)))
    assert any(judge_b64(audit, "V", R, ref("V", R)) is not None for R in GRID)
    monkeypatch.undo()
    # 3. derivative missing the -2k D / R^{2k+1} term
    orig = L._component

    def no_power_term(name, R, M, retarded, deriv):
        if not deriv:
            return orig(name, R, M, retarded, deriv)
        e, (eta_, C_, kadd_) = COMP_SAVE[name]
        out = orig(name, R, M, retarded, deriv)
        for k, c in C_.items():                   # add back what the full derivative subtracts
            f, _ = L._damp(2 * k + kadd_, eta_ * R, M)
            out = out - c * f * (Q(2 * k) / R ** (2 * k + 1))
        return out
    COMP_SAVE = dict(L.COMPONENTS)
    monkeypatch.setattr(L, "_component", no_power_term)
    assert any(not in_rounding_interval(dVdR_numeric(audit, R, 80, False), ref("F", R, False)) for R in GRID)
    monkeypatch.undo()
    # 4. domain check that also rejects exactly 1.2 A
    monkeypatch.setattr(L, "check_domain", lambda R: (_ for _ in ()).throw(L.PhysicsDomainExceeded())
                        if R <= L.R_MIN_BOHR else None)
    with pytest.raises(L.PhysicsDomainExceeded):
        ref("V", L.R_MIN_BOHR)                    # the boundary test would fail on this defect
