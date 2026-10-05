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
