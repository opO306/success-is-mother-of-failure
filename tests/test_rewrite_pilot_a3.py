"""REWRITE_PILOT_A3: smallest counterexamples for every rewrite rule, the R0 interpreter control, domain duties, the
generator bounds, the R6 predicate catalogue entry, and checker independence. Cheap; runs before any campaign."""

from __future__ import annotations

import ast
import sys
from fractions import Fraction as Q
from pathlib import Path

import pytest
from mpmath import iv
from mpmath.libmp import to_rational

from experiments.precision_pilot_a2t import evaluator_adapter as A2E
from experiments.rewrite_pilot_a3 import adapter as AD
from experiments.rewrite_pilot_a3 import rules as RU
from experiments.rewrite_pilot_a3 import rwforce as RW
from experiments.rewrite_pilot_a3 import symbolic as SY

PKG = Path(RU.__file__).resolve().parent


@pytest.fixture(scope="module")
def probe():
    A2E.prepare("algebra")
    return A2E._PROBE


def bnd(x):
    return Q(*to_rational(x._mpi_[0])), Q(*to_rational(x._mpi_[1]))


def G1024(R2):
    import exact_expression_gate_v0.lang_iv as LI
    old = iv.prec
    iv.prec = 1024
    try:
        return bnd(LI.G_of_R2(LI.c(R2)))
    finally:
        iv.prec = old


def test_generator_bounds():
    cs = RU.candidates()
    assert len(cs) == 23 and () in cs and all(len(c) <= RU.MAX_RULES for c in cs)
    assert not any("R3" in c and "R1" not in c for c in cs)
    with pytest.raises(ValueError):
        RU.build_plan(None, ("R3",))
    assert RU.parse_ev(RU.ev_id(("R1", "R4"))) == ("R1", "R4")
    with pytest.raises(ValueError):
        RU.parse_ev("rw:R4+R1")                         # non-canonical order refused


@pytest.mark.parametrize("prec", [64, 128, 512])
def test_r0_is_bit_identical_to_algebra(probe, prec):
    import exact_expression_gate_v0.lang_iv as LI
    iv.prec = prec
    fa = probe.Force(probe.Backend("mp", prec), True)
    f = RW.RwForce(RU.build_plan(probe.PROGRAM, ()))
    for x in [LI.c(Q(r) ** 2) for r in ("3.5", "7.1", "29")] + [iv.mpf([LI.c(Q(49)).a, LI.c(Q(50)).b])]:
        assert f(x)._mpi_ == fa(x)._mpi_


def test_zero_fold_drops_exact_zero_only(probe):
    groups, tail, num, den, dn, k, c = probe.PROGRAM
    tiny = Q(1, 10 ** 400)
    tail2 = dict(tail)
    tail2[-8] = tiny                                    # an even slot that is exactly 0 in the real tail
    plan = RU.build_plan((groups, tail2, num, den, dn, k, c), ("R1",))
    assert plan["tail"][-8] == tiny and -10 not in plan["tail"]
    assert RU.build_plan(probe.PROGRAM, ("R1",))["ops"] < RU.build_plan(probe.PROGRAM, ())["ops"]


def test_domain_duty_kept_even_when_every_inverse_term_is_folded(probe):
    from exact_expression_gate_v1 import common as K
    groups, tail, num, den, dn, k, c = probe.PROGRAM
    zero_inv = ([(a, {d: (v if d >= 0 else Q(0)) for d, v in P.items()}) for a, P in groups],
                {d: Q(0) for d in tail}, num, den, dn, k, c)
    plan = RU.build_plan(zero_inv, ("R1",))
    assert not plan["tail"] and all(d >= 0 for P in plan["blocks"] for d in P)    # 0 * f(x) folded away ...
    iv.prec = 128
    for rules in RU.candidates():
        f = RW.RwForce(RU.build_plan(probe.PROGRAM, rules))
        for x in (iv.mpf([0, 1]), iv.mpf(["-1e-30", "1"])):
            with pytest.raises(K.DomainStop):
                f(x)
    with pytest.raises(K.DomainStop):                   # ... but R > 0 is still demanded
        RW.RwForce(plan)(iv.mpf([0, 1]))


def test_den_premise_and_runtime_guard(probe):
    from exact_expression_gate_v1 import common as K
    groups, tail, num, den, dn, k, c = probe.PROGRAM
    bad = dict(den)
    bad[3] = -abs(bad[3])                               # one negative RET_B: den may vanish for some R > 0
    with pytest.raises(ValueError):
        RU.build_plan((groups, tail, num, bad, dn, k, c), ("R2",))
    plan = RU.build_plan(probe.PROGRAM, ("R2",))
    plan["den"] = {0: Q(1), 1: Q(-1)}                   # den = 1 - R crosses 0 inside the input
    iv.prec = 128
    import exact_expression_gate_v0.lang_iv as LI
    with pytest.raises(K.DomainStop):
        RW.RwForce(plan)(iv.mpf([LI.c(Q(1, 4)).a, LI.c(Q(4)).b]))


def test_symbolic_identity_is_not_domain_identity():
    import sympy as s
    x = s.symbols("x")
    assert s.cancel((x ** 2 - 1) / (x - 1)) == x + 1    # a CAS calls these equal ...
    assert ((x ** 2 - 1) / (x - 1)).subs(x, 1) is s.nan  # ... but the original is undefined at x = 1
    # hence S2 (domain duties) is a separate gate from S3 (identity)


def test_r6_predicate_counterexamples():
    assert RU.sqrt_lt(Q(1), Q(1), Q(-2), Q(-2)) is False   # naive x < y^2 says 1 < 4 True: wrong for y < 0
    assert RU.sqrt_lt(Q(4), Q(4), Q(2), Q(2)) is False     # exact tie sqrt(4) = 2: '<' is false, x < y^2 is 4 < 4 false
    assert RU.sqrt_lt(Q(3), Q(5), Q(2), Q(2)) is None      # x straddles y^2 = 4: refuse rather than guess
    assert RU.sqrt_lt(Q(4), Q(4), Q(3), Q(3)) is True
    assert RU.sqrt_lt(Q(9), Q(9), Q(3), Q(3)) is False     # sqrt(9) < 3 is false; 9 < 9 false: strictness kept
    assert RU.sqrt_lt(Q(1), Q(2), Q(-1), Q(1)) is None     # y crossing 0: refuse
    assert RU.sqrt_lt(Q(-1), Q(1), Q(5), Q(5)) is None     # sqrt domain
    import random
    rnd = random.Random(1)
    for _ in range(400):                                    # agreement with exact truth on proven cases
        x, y = Q(rnd.randint(0, 50), rnd.randint(1, 5)), Q(rnd.randint(-10, 10), rnd.randint(1, 5))
        r = RU.sqrt_lt(x, x, y, y)
        truth = (y > 0 and x < y * y)
        assert r is None or r == truth


@pytest.mark.parametrize("rules", RU.candidates(), ids=RU.ev_id)
def test_every_candidate_contains_truth_at_hard_inputs(probe, rules):
    import exact_expression_gate_v0.lang_iv as LI
    rmin = probe.L.R_MIN_BOHR
    rstar = Q(7113, 1000)                               # close to the force sign change (potential minimum)
    plan = RU.build_plan(probe.PROGRAM, rules)
    assert SY.s3a(plan, probe.PROGRAM)["canonical_equal"]
    for prec in (64, 192):
        iv.prec = prec
        f = RW.RwForce(plan)
        for a, b in ((rmin * rmin, Q(900)), ((rstar - Q(1, 10 ** 6)) ** 2, (rstar + Q(1, 10 ** 6)) ** 2),
                     (rmin * rmin, (rmin * Q(1001, 1000)) ** 2)):
            lo, hi = bnd(f(iv.mpf([LI.c(a).a, LI.c(b).b])))
            for r2 in (a, b, (a + b) / 2):
                t0, t1 = G1024(r2)
                assert lo <= t0 and t1 <= hi, (prec, a, b)


def test_adapter_rw_pass_swaps_and_restores():
    AD.prepare("rw:R1+R2")
    from exact_expression_gate_v1 import stream
    LI = sys.modules["exact_expression_gate_v0.lang_iv"]
    r = AD.run_pass("rw:R1+R2", "A2_bound", 128, 5)
    a = A2E.run_pass("algebra", "A2_bound", 128, 5)
    assert stream.LI is LI and r["force_swap_restored"] and r["effective_p"] == 128
    assert r["cells"] == a["cells"] and r["evaluator"] == "rw:R1+R2"
    for (x0, x1), (y0, y1) in zip(r["endpoints_scaled"], a["endpoints_scaled"]):
        assert Q(x0) <= Q(y1) and Q(y0) <= Q(x1)


def test_checker_imports_no_executor_module():
    tree = ast.parse((PKG / "checker.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    banned = ("rules", "rwforce", "symbolic", "adapter", "runner", "campaign", "policies", "evaluator_adapter",
              "harness", "probe")
    assert not any(n.split(".")[-1] in banned for n in names), names
