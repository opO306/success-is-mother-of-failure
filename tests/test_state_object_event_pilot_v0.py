"""STATE_OBJECT_EVENT_PILOT_V0: unit and fault-injection tests (PART A and PART B kept separate)."""

from __future__ import annotations

import ast
import random
from fractions import Fraction as Q
from pathlib import Path

import pytest

from a_numeric import FixedPoint
from a_reference import c1b1_two_atom as C
from experiments.state_object_event_pilot_v0 import object_port as P
from experiments.state_object_event_pilot_v0 import pair_state as S
from experiments.state_object_event_pilot_v0 import world_retention as W

PKG = Path(W.__file__).resolve().parent
PART_A = ("world_retention.py", "object_port.py", "pair_state.py")
PART_B = ("event_lineage.py", "derivative_certificate.py")


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(a.name for a in node.names)
    return names


def test_parts_do_not_import_each_other():
    for f in PART_A:
        names = _imports(PKG / f)
        assert not any(n.split(".")[-1] in ("event_lineage", "derivative_certificate") for n in names), f
        assert not any(n.startswith("exact_expression_gate") for n in names), f
    for f in PART_B:
        p = PKG / f
        if p.exists():
            names = _imports(p)
            assert not any(n.split(".")[-1] in ("world_retention", "object_port", "pair_state") for n in names), f


# ---------------------------------------------------------------- PART A -------------------------------------------

@pytest.mark.parametrize("case", W.ORIGINS)
def test_trusted_origins_rebuild_bit_identical(case):
    import json
    run = W.new_case(case)
    doc = json.loads((W.ROOT / f"docs/active/c1b1_trusted_test_origins_v1/{case}.json").read_text(encoding="utf-8"))
    a, b = run.atoms
    assert [str(v) for v in list(a.r) + list(a.p) + list(b.r) + list(b.p)] == doc["initial_raw"]


def test_a2_sym_is_symmetric_after_rounding():
    a, b = W.new_case("A2_sym").atoms
    assert a.r == tuple(-x for x in b.r) and a.p == tuple(-x for x in b.p)


@pytest.mark.parametrize("case", W.CASES)
def test_observer_history_does_not_change_physics(case):
    r1 = W.run_loop(W.new_case(case), C.step, None, max_steps=150)
    obs = W.Observer()
    r2 = W.run_loop(W.new_case(case), C.step, obs, max_steps=150)
    assert r1 == r2
    assert len(obs.history) == r2["completed_steps"]


def test_observer_receives_only_immutable_snapshot():
    run = W.new_case("A2_sym")
    snap = W.snapshot(run)

    def flat(x):
        if isinstance(x, tuple):
            for y in x:
                yield from flat(y)
        else:
            yield x
    assert all(isinstance(v, (int, str, type(None))) for v in flat(snap))


def test_fault_injection_observer_that_writes_back_is_detected():
    """If an observer could reach the Run, a write-back changes the stream identity: the comparison sees it."""
    clean = W.run_loop(W.new_case("A2_sym"), C.step, None, max_steps=20)

    def evil_step(run):
        C.step(run)
        if run.t_steps == 5:                       # an observer with Run access nudging one raw
            a, b = run.atoms
            run.atoms = (C.Atom(a.species, (a.r[0] + 1,) + a.r[1:], a.p), b)
    bad = W.run_loop(W.new_case("A2_sym"), evil_step, None, max_steps=20)
    assert bad["stream_sha256"] != clean["stream_sha256"]


@pytest.mark.parametrize("case", W.CASES)
def test_port_bit_identical_to_canonical(case):
    ref = W.run_loop(W.new_case(case), C.step, None, max_steps=200)
    w = P.PortRun.from_run(W.new_case(case))
    got = W.run_loop(w, P.step, None, max_steps=200)
    assert got == ref
    assert w.law.checks == 2 * w.t_steps


def test_port_event_is_not_retained():
    w = P.PortRun.from_run(W.new_case("A2_sym"))
    for _ in range(3):
        P.step(w)
    assert not any(isinstance(v, P.InteractionEvent) for v in vars(w).values())
    assert isinstance(w.J_cache, tuple)


def test_fault_injection_port_breaks_newton_is_caught():
    w = P.PortRun.from_run(W.new_case("A2_sym"))
    a, b = w.atoms
    ev = w.law.interact(a, b)
    forged = P.InteractionEvent(tuple(x + 1 for x in ev.impulse_i), ev.impulse_j, ev.obligations)
    with pytest.raises(P.EventInvariantViolation):
        w.law.apply(forged, a, b)


def test_half_even_rounding_is_odd_symmetric():
    pos = FixedPoint(96, 48)
    rnd = random.Random(7)
    vals = [Q(k, 2) * Q(1, 1 << 48) for k in range(-9, 10)]          # exact ties
    vals += [Q(rnd.randrange(-10**30, 10**30), rnd.randrange(1, 10**25)) for _ in range(500)]
    for x in vals:
        assert pos.from_exact(-x) == -pos.from_exact(x)


def test_pair_lossless_lockstep():
    ref = W.new_case("A2_sym")
    w = S.PairRun.from_run(W.new_case("A2_sym"))
    for _ in range(400):
        C.step(ref)
        S.step(w)
        a, b = w.atoms
        assert (a.r, a.p, b.r, b.p) == (ref.atoms[0].r, ref.atoms[0].p, ref.atoms[1].r, ref.atoms[1].p)
        assert w.J_cache == ref.J_cache and w.t_steps == ref.t_steps


def test_pair_refuses_asymmetric_state():
    w = S.PairRun.from_run(W.new_case("e1_b10"))           # S_r = 0 but p not antisymmetric? check either way
    w.S_r = (w.S_r[0] + 2,) + w.S_r[1:]
    with pytest.raises(S.PairStateRefused):
        S.step(w)
    assert w.refused_at == w.t_steps


def _collision():
    pos, mom = W.profiles()
    return C.new_run(pos, Q(40), (Q(-23, 20), 0, 0), (400, 0, 0), (Q(23, 20), 0, 0), (-400, 0, 0),
                     momentum_profile=mom, validated_only=False)


def test_refusal_identical_in_every_model():
    ref = W.run_loop(_collision(), C.step, None, max_steps=50)
    assert ref["status"] == "PhysicsDomainExceeded"
    assert W.run_loop(P.PortRun.from_run(_collision()), P.step, None, max_steps=50) == ref
    assert W.run_loop(S.PairRun.from_run(_collision()), S.step, None, max_steps=50) == ref


def test_deep_size_counts_history_growth():
    obs = W.Observer()
    W.run_loop(W.new_case("A2_sym"), C.step, obs, max_steps=50)
    small = W.deep_size(obs.history[:10])
    big = W.deep_size(obs.history)
    assert big > 3 * small


# ---------------------------------------------------------------- PART B -------------------------------------------
# Every PART B test name contains "lineage" or "certificate": the campaign's soundness gate runs exactly these.

import gzip  # noqa: E402
import json as _json  # noqa: E402

from mpmath.libmp import from_int, from_rational, fzero, round_nearest  # noqa: E402

from exact_expression_gate_v1 import common as K  # noqa: E402
from experiments.state_object_event_pilot_v0 import derivative_certificate as D  # noqa: E402
from experiments.state_object_event_pilot_v0 import event_lineage as EL  # noqa: E402

CERT = EL.DEFAULT_CERT


def _f(x):
    x = Q(x)
    return from_rational(x.numerator, x.denominator, 96, round_nearest)


def _contains(form, eps, truth):
    """Independent oracle: is the exact value `truth` inside the form for this assignment of eps values?"""
    lin = EL.rq(form.c) + sum((EL.rq(v) * Q(eps[t]) for t, v in form.k.items()), Q(0))
    return abs(Q(truth) - lin) <= EL.rq(form.r)


def _value(form, eps, rho=0):
    return EL.rq(form.c) + sum((EL.rq(v) * Q(eps[t]) for t, v in form.k.items()), Q(0)) + Q(rho)


def test_lineage_same_tag_plus_minus_cancels_exactly():
    A = EL.Arith(96)
    x = EL.Form(_f(1), {7: _f(Q(3, 10))})
    y = EL.Form(_f(2), {7: _f(Q(3, 10))})
    z = EL.add(A, x, y, -1)
    assert 7 not in z.k


def test_lineage_total_momentum_carries_no_event_tag():
    L = EL.Lineage(96, EL.Table(CERT))
    for _ in range(5):
        L.step()
    for k in range(3):
        tot = EL.add(L.A, L.p[0][k], L.p[1][k])
        assert not tot.k                          # +J and -J share every tag: they cancel exactly


def test_lineage_tag_reuse_is_detected():
    tags = EL.Tags()
    tags.new()
    tags.next = 0                                 # fault injection: an allocator that hands out an old id
    with pytest.raises(EL.TagReuse):
        tags.new()
    A = EL.Arith(96)                              # what reuse would do: two independent errors falsely cancel
    x, y = EL.Form(fzero, {0: _f(1)}), EL.Form(fzero, {0: _f(1)})
    claimed = EL.add(A, x, y, -1)
    truth = _value(x, {0: 1}) - _value(y, {0: -1})            # independent errors: eps_x = 1, eps_y = -1
    assert not claimed.k and not _contains(claimed, {}, truth)


def test_lineage_forged_zero_nonlinear_remainder_is_detected():
    A = EL.Arith(96)
    x = EL.Form(fzero, {1: _f(1)})
    honest = EL.mul(A, x, x)
    forged = EL.Form(honest.c, dict(honest.k), fzero)
    for e in (Q(-1), Q(-1, 3), Q(0), Q(1, 2), Q(1)):
        assert _contains(honest, {1: e}, e * e)
    assert not all(_contains(forged, {1: e}, e * e) for e in (Q(-1), Q(1)))


class _InwardArith(EL.Arith):
    def err(self, s):
        return fzero


def test_lineage_inward_rounding_is_detected():
    honest, inward = EL.Arith(8), _InwardArith(8)
    x = EL.Form(from_int(1))
    y = EL.Form(from_rational(1, 1 << 20, 96, round_nearest))
    truth = 1 + Q(1, 1 << 20)
    assert _contains(EL.add(honest, x, y), {}, truth)
    assert not _contains(EL.add(inward, x, y), {}, truth)


def test_lineage_domain_below_at_above_r_min():
    r = K.R_MIN2
    tiny = Q(1, 10 ** 30)
    assert EL.domain(r - 2 * tiny, r - tiny) == K.VIOLATED
    assert EL.domain(r, r) == K.PROVEN
    assert EL.domain(r, r + tiny) == K.PROVEN
    assert EL.domain(r + tiny, r + 2 * tiny) == K.PROVEN
    assert EL.domain(r - tiny, r + tiny) == K.UNPROVEN
    lo, hi = EL.form_range(EL.Arith(96), EL.const_form(EL.Arith(96), r))   # r_min^2 is not a binary number
    assert lo <= r <= hi and EL.domain(lo, hi) != K.VIOLATED


def _fake_table(tmp_path, gps):
    cells = [{"m": m, "V1": ["0", "0"], "V2": ["0", "0"], "Gp": [str(gps.get(m, (0, 0))[0]), str(gps.get(m, (0, 0))[1])]}
             for m in range(D.M_LO, D.M_HI + 1)]
    path = tmp_path / "cert.json.gz"
    with gzip.open(path, "wb") as f:
        f.write(_json.dumps({"cells": cells}).encode())
    return D.Table(path)


def test_certificate_lookup_at_cell_boundary_uses_hull(tmp_path):
    t = _fake_table(tmp_path, {7269: (Q(-5), Q(-4)), 7270: (Q(-3), Q(-1))})
    edge = Q(7270, 1024) ** 2
    assert D.Table.cell_range(edge, edge)[0] == 7270
    lo, hi, cells = t.gprime_hull(Q(14539, 2048) ** 2, Q(14541, 2048) ** 2)      # R from 7269.5/1024 to 7270.5/1024
    assert cells == (7269, 7270) and (lo, hi) == (Q(-5), Q(-1))
    top = Q(7680, 1024) ** 2                    # R = 7.5 exactly: the lower-end rule picks cell 7680 -> refused (conservative)
    assert D.Table.cell_range(top, top) == (7680, 7680)
    with pytest.raises(D.EventDerivativeDomainUnsupported):
        t.gprime_hull(top, top)


def test_certificate_outside_range_fails_closed(tmp_path):
    t = _fake_table(tmp_path, {})
    with pytest.raises(D.EventDerivativeDomainUnsupported):
        t.gprime_hull(Q(68, 10) ** 2, Q(69, 10) ** 2)
    with pytest.raises(D.EventDerivativeDomainUnsupported):
        t.gprime_hull(Q(75, 10) ** 2, Q(76, 10) ** 2)


def test_lineage_reading_does_not_feed_back():
    def snap(L):
        qs, ps = L.components()
        return [(x.c, sorted(x.k.items()), x.r) for x in qs + ps]
    table = EL.Table(CERT)
    L1, L2 = EL.Lineage(96, table), EL.Lineage(96, table)
    for _ in range(8):
        L1.step()
        L2.step()
        before = snap(L2)
        EL.measure(*L2.ranges())                  # observe and decide every step
        assert snap(L2) == before
    assert snap(L1) == snap(L2)


def _reference_20():
    from mpmath import iv
    import exact_expression_gate_v0.lang_iv as LI
    iv.prec = 512
    q = [[LI.c(x) for x in r] for r in EL.Q0]
    p = [[LI.c(x) for x in r] for r in EL.P0]
    h, cdt = LI.c(Q(20)), LI.c(K.CDT)

    def forces(q):
        d = [q[1][k] - q[0][k] for k in range(3)]
        g = LI.G_of_R2(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
        t = [h * g * d[k] for k in range(3)]
        return [[-x for x in t], t]
    F = forces(q)
    for _ in range(20):
        p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(2)]
        q = [[q[a][k] + p[a][k] * cdt for k in range(3)] for a in range(2)]
        F = forces(q)
        p = [[p[a][k] + F[a][k] for k in range(3)] for a in range(2)]
    return [K.bounds(v) for r in q for v in r] + [K.bounds(v) for r in p for v in r]


def _candidate_20(shift=None):
    real = EL.interact

    def shifted(A, tags, table, qi, qj, step, h=Q(20)):
        ev = real(A, tags, table, qi, qj, step, h)
        if shift is not None:                      # fault injection: impulse center moved, claimed tags unchanged
            ev.J[0].c = from_rational(*(lambda v: (v.numerator, v.denominator))(EL.rq(ev.J[0].c) * (1 + shift)), 96,
                                      round_nearest)
        return ev
    EL.interact = shifted
    try:
        L = EL.Lineage(96, EL.Table(CERT))
        for _ in range(20):
            L.step()
        qr, pr = L.ranges()
    finally:
        EL.interact = real
    return qr + pr


def _meets(rng, ref):
    return all(lo <= rhi and rlo <= hi for (lo, hi), (rlo, rhi) in zip(rng, ref))


def test_lineage_short_run_contains_high_precision_reference():
    """Candidate at 96 bits vs an independent 512-bit interval replay (own loop here, lang_iv as shared TCB).
    Necessary check only: conservative rounding bounds can hide small defects (see the fault-injection test)."""
    ref = _reference_20()
    assert _meets(_candidate_20(), ref)
    assert not _meets(_candidate_20(shift=Q(1, 10 ** 12)), ref)    # an enclosure that really misses the truth

def test_checker_imports_no_executor_module():
    names = _imports(PKG / "checker.py")
    banned = ("world_retention", "object_port", "pair_state", "event_lineage", "derivative_certificate", "campaign",
              "campaign_b")
    assert not any(n.split(".")[-1] in banned for n in names)