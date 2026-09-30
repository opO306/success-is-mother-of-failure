"""C1-B1 Energy Bound v0 (a_reference/c1b1_energy_bound.py) and its use in the outgoing energy chain
(a_reference/c1b1_outgoing_energy.py). The inbound energy mode is tested in test_c1b1_inbound_outer.py.

(1) radial_derivatives is c1b1_outer_bound.derivatives without the R >= 20 guard: same syntax tree, same values on
R >= 20, and it contains high-precision point values below 20; (2) the energy and momentum ranges contain the real
executor states (a consistency check, never the proof); (3) the barrier lemma certifies [5.32, 5.35] for E~ <= 10 De and
refuses too-wide cells, too-thin barriers and too-high energy; a real bouncing trajectory stays outside; (4) the outgoing
energy chain: record re-check, the executor inside the first shell's claims, a low-energy state the v1 chain cannot
certify, and the documented limit at 1e-8 De; (5) fault injection.
"""
import ast
import inspect
import math
import sys
import types
from fractions import Fraction as Q
from pathlib import Path

import pytest

import a_reference.c1b1_energy_bound as EB
import a_reference.c1b1_outer_bootstrap as O
import a_reference.c1b1_outer_bound as B
import a_reference.c1b1_outgoing_energy as OE
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

POS, MOM = FixedPoint(96, 48), FixedPoint(96, 80)
DE = C.DE_CONTRACT


def _run(q, P, validated_only=False):
    return C.new_run(POS, B.H, tuple(-x / 2 for x in q), tuple(-x for x in P), tuple(x / 2 for x in q), P,
                     momentum_profile=MOM, validated_only=validated_only)


def _state(e, b, R0, sign):
    """Relative state at R0 with impact parameter b, E = e De; sign -1 inbound, +1 outbound (same as the survey)."""
    V = float(C.potential_high(Q(R0) ** 2))
    p = math.sqrt(2 * float(B.MU) * (float(e) * float(DE) - V))
    return _run((Q(math.sqrt(R0 * R0 - b * b)), Q(b), Q(0)), (Q(sign * p), Q(0), Q(0)))


def _rel(atoms):
    q = C.relative(POS, *atoms)
    pi, pj = (C.exact(MOM, a.p) for a in atoms)
    return q, tuple((y - x) / 2 for x, y in zip(pi, pj))


def _dot(a, b):
    return sum((x * y for x, y in zip(a, b)), Q(0))


# --- (1) the derivative enclosure below 20 ------------------------------------------------------------------------

def _body(fn):
    tree = ast.parse(inspect.getsource(fn).lstrip())
    f = tree.body[0]
    body = [s for s in f.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
    body = [s for s in body if not isinstance(s, ast.If)]                  # the scope guard, the only difference

    class Strip(ast.NodeTransformer):
        def visit_Attribute(self, node):
            self.generic_visit(node)
            if isinstance(node.value, ast.Name) and node.value.id == "B":
                return ast.copy_location(ast.Name(node.attr, ast.Load()), node)
            return node
    return [ast.dump(Strip().visit(s)) for s in body]


def test_radial_derivatives_is_the_outer_bound_formula_without_its_guard():
    assert _body(EB.radial_derivatives.__wrapped__) == _body(B.derivatives)
    for a, b in ((Q(20), Q(25)), (Q(100), Q(125)), (Q(5000), Q(6250))):
        assert EB.radial_derivatives(a, b) == B.derivatives(a, b)


@pytest.mark.parametrize("R", [Q(54, 10), Q(6), Q(71, 10), Q(10), Q(15)])
def test_below_20_the_enclosure_contains_the_high_precision_values(R):
    d = EB.radial_derivatives(R, R)
    assert d[0].lo <= C.potential_high(R * R) <= d[0].hi
    assert d[1].lo <= -C.force_high(R * R) <= d[1].hi


# --- (2) energy and momentum ranges against the executor (consistency, not proof) ---------------------------------

def test_the_energy_and_the_shell_momentum_range_contain_every_executor_state():
    run = _run((Q(28), Q(5), Q(0)), (Q(-12), Q(0), Q(0)))
    q, p = _rel(run.atoms)
    E = EB.energy_of_state(q, p)
    domain = O._covered_shell(Q(20), Q(29))
    dE = B.step_budget(domain, Q(13))["energy_hartree"]["total"]
    for n in range(1, 600):
        C.step(run)
        q, p = _rel(run.atoms)
        lo, hi = EB.momentum_range(E.widen(n * dE), domain.radial[0], domain.force)
        assert lo * lo <= _dot(p, p) <= hi * hi, n
        own = EB.energy_of_state(q, p)
        assert E.lo - n * dE <= own.hi and own.lo <= E.hi + n * dE


def test_a_forbidden_cell_has_no_momentum_range():
    V = EB.radial_derivatives(Q(532, 100), Q(533, 100))[0]
    assert EB.momentum_range(EB.EnergyRange(10 * DE, 10 * DE), V, Q(0)) is None
    assert EB.momentum_range(EB.EnergyRange(30 * DE, 30 * DE), V, Q(0)) is not None


# --- (3) the energy barrier ---------------------------------------------------------------------------------------

def test_the_barrier_532_535_is_certified_for_10_De():
    rec = EB.certify_energy_barrier(10 * DE, Q(532, 100), Q(535, 100), Q(20), 3)
    assert rec["V_lower_min"] > Q(1268, 100) * DE and rec["max_stored_step"] < Q(3, 100)
    assert rec["premises_not_proved_here"]


@pytest.mark.parametrize("E,c,d,cap,cells,reason", [
    (10, Q(530, 100), Q(540, 100), 20, 1, "not energetically forbidden"),      # one wide cell: enclosure too wide
    (10, Q(534, 100), Q(535, 100), 20, 1, "thicker than one stored step"),     # 0.01 < one step at |P_h| <= 20
    (13, Q(532, 100), Q(535, 100), 20, 3, "not energetically forbidden"),      # above the barrier's lower bound
])
def test_the_barrier_refusals(E, c, d, cap, cells, reason):
    with pytest.raises(O.NotCertified, match=reason):
        EB.certify_energy_barrier(E * DE, c, d, Q(cap), cells)


def test_a_real_head_on_bounce_below_10_De_never_stores_a_state_inside_the_barrier():
    """Consistency only: E ~ 9.9 De head-on from R = 6.5 inward; every stored R stays above d = 5.35."""
    V = C.potential_high(Q(65, 10) ** 2)
    p = Q(math.sqrt(2 * float(B.MU) * float(Q(99, 10) * DE - V)))
    run = _run((Q(65, 10), Q(0), Q(0)), (-p, Q(0), Q(0)), validated_only=True)
    rs = []
    for _ in range(400):
        C.step(run)
        q, _ = _rel(run.atoms)
        rs.append(_dot(q, q))
    assert min(rs) < Q(6) ** 2 and min(rs) > Q(535, 100) ** 2


# --- (4) the outgoing energy chain --------------------------------------------------------------------------------

def _check_outgoing(cert):
    cap = cert["p_cap"]
    for s in cert["shells"]:
        n, k, count, loss = s["induction_budget"], s["half_kick_cap"], s["max_steps"], s["w_loss_per_step"]
        assert count <= n and s["w_floor"] - loss > 0
        assert s["g_min"] == 2 * O.ALPHA * (s["w_floor"] - s["guard_b"] * k) - 2 * s["guard_b"] * O.D > 0
        lo = s["entry_enclosure"]["radius_lower"]
        assert count == O.residence_steps(s["b"] ** 2 - lo ** 2, s["g_min"])
        domain = O._covered_shell(s["a"], s["guard_b"])
        pe = EB.momentum_range(EB.EnergyRange(*s["energy_entry"]).widen(n * s["energy_step_budget"]),
                               domain.radial[0], domain.force)
        assert pe == s["energy_momentum_range"]
        assert min(s["entry_enclosure"]["p_norm"][1] + 2 * n * k, pe[1] + k) <= cap
    for s, t in zip(cert["shells"], cert["shells"][1:]):
        assert t["a"] == s["b"] and t["entry_enclosure"]["q_dot_p_lower"] == s["exit_enclosure"]["q_dot_p_lower"]
        assert EB.EnergyRange(*t["energy_entry"]) == EB.EnergyRange(*s["energy_entry"]).widen(
            s["max_steps"] * s["energy_step_budget"])


@pytest.fixture(scope="module")
def fast_outgoing():
    run = _state("10", 0, 25, +1)
    return run, OE.certify_outgoing_outer_energy(run, Q(191, 10))


def test_outgoing_energy_record_rechecks(fast_outgoing):
    _check_outgoing(fast_outgoing[1])
    assert fast_outgoing[1]["momentum_bounds"] == "energy_and_kick"


def test_outgoing_energy_executor_stays_inside_the_first_shell_claims(fast_outgoing):
    run0, cert = fast_outgoing
    s = cert["shells"][0]
    run = _run(*_rel(run0.atoms))
    q, p = _rel(run.atoms)
    steps = 0
    while _dot(q, q) < s["b"] ** 2:
        C.step(run)
        steps += 1
        q1, p1 = _rel(run.atoms)
        assert _dot(q1, q1) - _dot(q, q) >= s["g_min"]
        assert _dot(q1, p1) >= s["w_floor"] - s["w_loss_per_step"]
        pe = s["energy_momentum_range"]
        assert pe[0] ** 2 <= _dot(p1, p1) <= pe[1] ** 2
        q, p = q1, p1
    assert steps <= s["max_steps"]


def test_the_energy_chain_certifies_a_low_energy_state_the_v1_chain_cannot():
    run = _state("1e-4", 7, 25, +1)
    cap = B.sqrt_up(_dot(*[_rel(run.atoms)[1]] * 2) + 2 * B.MU * abs(C.potential_high(Q(400)))) * (1 + Q(1, 1024))
    cert = OE.certify_outgoing_outer_energy(run, cap)
    _check_outgoing(cert)
    import a_reference.c1b1_outer_chain as OC
    with pytest.raises(O.NotCertified):
        OC.certify_outgoing_outer(run, cap)


def test_the_documented_limit_1e_8_De_outgoing_from_25_is_not_certified():
    """~1e10 steps to R_J: the summed one-step energy budget reaches the total energy (~4.5e-12 hartree)."""
    run = _state("1e-8", 7, 25, +1)
    cap = B.sqrt_up(_dot(*[_rel(run.atoms)[1]] * 2) + 2 * B.MU * abs(C.potential_high(Q(400)))) * (1 + Q(1, 16))
    with pytest.raises(O.NotCertified):
        OE.certify_outgoing_outer_energy(run, cap)


# --- (5) fault injection -------------------------------------------------------------------------------------------

def _mutant(module, old, new):
    src = Path(module.__file__).read_text(encoding="utf-8")
    assert src.count(old) == 1, old
    mod = types.ModuleType("mutant_" + module.__name__.rsplit(".", 1)[-1])
    sys.modules[mod.__name__] = mod                                      # dataclasses look their module up
    exec(compile(src.replace(old, new), "mutant.py", "exec"), mod.__dict__)
    return mod


def test_fault_injection_a_momentum_floor_from_the_wrong_potential_end_is_caught():
    mod = _mutant(EB, "    lo2 = 2 * B.MU * (energy.lo - V.hi)\n", "    lo2 = 2 * B.MU * (energy.lo - V.lo)\n")
    run = _run((Q(28), Q(5), Q(0)), (Q(-12), Q(0), Q(0)))
    E = mod.energy_of_state(*_rel(run.atoms))
    domain = O._covered_shell(Q(20), Q(29))
    lo, _ = mod.momentum_range(E, domain.radial[0], domain.force)
    assert lo * lo > _dot(*[_rel(run.atoms)[1]] * 2)                     # the real state is below the claimed floor


def test_fault_injection_a_barrier_without_the_thickness_check_is_caught():
    mod = _mutant(EB, "    if not d - c > step:\n        raise O.NotCertified(\"barrier is not thicker than one stored step\")\n", "")
    mod.certify_energy_barrier(10 * DE, Q(5345, 1000), Q(535, 100), Q(20), 1)   # accepts a barrier one step can jump
    with pytest.raises(O.NotCertified):
        EB.certify_energy_barrier(10 * DE, Q(5345, 1000), Q(535, 100), Q(20), 1)


def test_fault_injection_an_outgoing_floor_taken_at_the_far_end_is_caught_by_the_executor(fast_outgoing):
    """Mutant: the angular-momentum floor sqrt(R^2 p^2 - L^2) evaluated at the shell's FAR end b instead of a. The
    real q.P near the entry is below that. (A sign flip of the loss is no test here: the loss is 0 at 10 De.)"""
    mod = _mutant(OE, "        x = a * a * p_state * p_state - (L_hi + n * dL) ** 2\n",
                  "        x = b * b * p_state * p_state - (L_hi + n * dL) ** 2\n")
    run0, _ = fast_outgoing
    cert = mod.certify_outgoing_outer_energy(_run(*_rel(run0.atoms)), Q(191, 10))
    s = cert["shells"][0]
    run = _run(*_rel(run0.atoms))
    worst = None
    for _ in range(s["max_steps"]):
        C.step(run)
        q, p = _rel(run.atoms)
        worst = _dot(q, p) if worst is None else min(worst, _dot(q, p))
        if _dot(q, q) >= s["b"] ** 2:
            break
    assert worst < s["w_floor"] - s["w_loss_per_step"]


def test_the_modules_never_run_a_trajectory_or_read_d_valid():
    for m in (EB, OE):
        src = Path(m.__file__).read_text(encoding="utf-8")
        assert "C.step(" not in src and "c1b1_domain_contract" not in src and ".validation" not in src
