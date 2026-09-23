"""causal v5 reference executor (docs/current/A_MICRO_V5_REFERENCE_EXECUTOR_PLAN_V1.md).

Sections:
  1. exact numbers: one constructor, no floats, one canonical form
  2. the spec refuses what the plan refuses
  3. hand-computed physics: contact times, merges, U' = ΣU + ΣK − K'
  4. halts are results: corner, non-binding (no port / no rule / below threshold), contested
  5. instants: three-way merge at once, causal rounds, never deferring an existing event
  6. invariances: relabelling, input order, observation interval, Galilean, meter
  7. structural guards: no floats in the physics modules, conservation over a run
"""
from __future__ import annotations

import ast
import random
from fractions import Fraction
from pathlib import Path

import pytest

from engine.deterministic.v5_meter import DenominatorMeter
from engine.deterministic.v5_number import deser, q, ser
from engine.deterministic.v5_reference import run_v5
from engine.deterministic.v5_spec import FORMAT, RunRequest, WorldSpecV5
from engine.deterministic.v5_state import initial_state

ROOT = Path(__file__).resolve().parents[1]
UNITS = {"mass": {"name": "u", "si": "1"}, "length": {"name": "pm", "si": "1/1000000000000"},
         "time": {"name": "fs", "si": "1/1000000000000000"}}
ALL_PORTS = ["E", "N", "S", "W"]


def world(elements, structures, *, rules=None, materials=None) -> WorldSpecV5:
    """elements: (label, kind, x, y); structures: dict(members, momentum, internal_energy, bonds)."""
    return WorldSpecV5.from_mapping({
        "format": FORMAT, "world_id": "test", "units": UNITS,
        "materials": materials or [{"kind": 0, "mass": "1", "contact_half_width": "1/2", "ports": ALL_PORTS},
                                   {"kind": 1, "mass": "2", "contact_half_width": "1/2", "ports": ALL_PORTS}],
        "bond_rules": rules if rules is not None else [
            {"rule_id": "ew", "a": {"kind": 0, "port": "E"}, "b": {"kind": 0, "port": "W"}, "threshold": "0"},
            {"rule_id": "ns", "a": {"kind": 0, "port": "N"}, "b": {"kind": 0, "port": "S"}, "threshold": "0"}],
        "elements": [{"label": l, "kind": k, "position": [str(x), str(y)]} for l, k, x, y in elements],
        "structures": [{"members": s["members"], "momentum": [str(c) for c in s.get("momentum", (0, 0))],
                        "internal_energy": str(s.get("internal_energy", 0)), "bonds": s.get("bonds", [])}
                       for s in structures]})


def free(label, momentum=(0, 0)):
    return {"members": [label], "momentum": momentum}


def run(spec, end=40, interval=1, meter=None):
    return run_v5(spec, RunRequest(end, interval), meter)


# ---------------------------------------------------------------------------
# 1. Exact numbers.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [0.5, True, "0.5", "1e3", None])
def test_only_exact_numbers_enter(bad) -> None:
    with pytest.raises(TypeError):
        q(bad)


def test_one_physical_value_has_one_serialised_form() -> None:
    assert ser(q("2/4")) == ser(q("1/2")) == [1, 2]
    assert ser(q(0)) == [0, 1] and ser(q("-3/6")) == [-1, 2]
    with pytest.raises(ValueError):
        deser([2, 4])


def test_a_float_anywhere_in_a_spec_is_refused() -> None:
    raw = world([("a", 0, 0, 0)], [free("a")]).canonical()
    with pytest.raises(TypeError):
        WorldSpecV5.from_mapping({**_as_mapping(raw), "materials": [{"kind": 0, "mass": 1.0,
                                                                        "contact_half_width": "1/2", "ports": []}]})


def _as_mapping(canonical):
    return {"format": FORMAT, "world_id": "t", "units": UNITS, "bond_rules": [],
            "elements": [{"label": "a", "kind": 0, "position": ["0", "0"]}],
            "structures": [{"members": ["a"]}]}


# ---------------------------------------------------------------------------
# 2. Spec validation.
# ---------------------------------------------------------------------------

def test_units_are_required() -> None:
    raw = _as_mapping(None)
    raw.pop("units")
    raw["materials"] = [{"kind": 0, "mass": "1", "contact_half_width": "1/2", "ports": []}]
    with pytest.raises(ValueError, match="units"):
        WorldSpecV5.from_mapping(raw)


def test_overlapping_bodies_are_refused() -> None:
    with pytest.raises(ValueError, match="overlap"):
        initial_state(world([("a", 0, 0, 0), ("b", 0, "1/2", 0)], [free("a"), free("b")]))


def test_a_bond_must_be_a_flush_face_contact() -> None:
    spec = world([("a", 0, 0, 0), ("b", 0, 2, 0)], [{"members": ["a", "b"], "bonds": [["a", "E", "b", "W"]]}])
    with pytest.raises(ValueError, match="flush"):
        initial_state(spec)


def test_two_rules_for_one_face_pair_are_refused() -> None:
    rule = {"rule_id": "x", "a": {"kind": 0, "port": "E"}, "b": {"kind": 0, "port": "W"}, "threshold": "0"}
    with pytest.raises(ValueError, match="at most one rule"):
        world([("a", 0, 0, 0)], [free("a")], rules=[rule, {**rule, "rule_id": "y", "threshold": "1"}])


def test_the_run_request_is_not_part_of_the_world() -> None:
    spec = world([("a", 0, 0, 0)], [free("a", (1, 0))])
    assert run(spec, interval=1).spec_digest == run(spec, interval=Fraction(1, 3)).spec_digest


# ---------------------------------------------------------------------------
# 3. Hand-computed physics.
# ---------------------------------------------------------------------------

def _chain():
    return world([("a", 0, 0, 0), ("b", 0, 4, 0), ("c", 0, 10, 0)],
                 [free("a", (1, 0)), free("b", (-1, 0)), free("c", ("-1/3", 0))])


def test_head_on_contact_time_and_merge_are_exact() -> None:
    result = run(_chain(), end=20)
    first, second = result.events
    assert first.time == Fraction(3, 2) and first.kinetic_energy_absorbed == 1 and first.post.internal_energy == 1
    assert second.time == Fraction(39, 2) and second.kinetic_energy_absorbed == Fraction(1, 27)
    assert second.post.internal_energy == Fraction(28, 27)          # U' = ΣU + ΣK − K': the earlier 1 carried over


def test_a_bond_moves_nothing() -> None:
    event = run(_chain(), end=20).events[0]
    pre = dict(p for snap in event.pre for p in snap.positions)
    assert dict(event.post.positions) == pre


@pytest.mark.parametrize("gap", [4, 5, Fraction(9, 2)])
def test_odd_even_or_fractional_distance_all_meet(gap) -> None:
    """Parity no longer decides chemistry: continuous paths always touch."""
    result = run(world([("a", 0, 0, 0), ("b", 0, gap, 0)], [free("a", (1, 0)), free("b", (-1, 0))]))
    assert len(result.events) == 1 and result.events[0].time == (Fraction(gap) - 1) / 2


def test_crossing_paths_are_caught_not_swapped() -> None:
    """Fast bodies one width apart: v4 would swap them; v5 catches the touch."""
    result = run(world([("a", 0, 0, 0), ("b", 0, "3/2", 0)], [free("a", (5, 0)), free("b", (-5, 0))]))
    assert result.events and result.events[0].time == Fraction(1, 20)


def test_grow_carries_existing_internal_energy() -> None:
    spec = world([("a", 0, 0, 0), ("b", 0, 1, 0), ("c", 0, 5, 0)],
                 [{"members": ["a", "b"], "bonds": [["a", "E", "b", "W"]], "internal_energy": 5},
                  free("c", (-2, 0))])
    event = run(spec).events[0]
    # K_c = 2, K' = 4/6 = 2/3, absorbed 4/3; U' = 5 + 4/3
    assert event.kinetic_energy_absorbed == Fraction(4, 3) and event.post.internal_energy == Fraction(19, 3)


# ---------------------------------------------------------------------------
# 4. Halts are results.
# ---------------------------------------------------------------------------

def test_corner_contact_halts_with_a_record() -> None:
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 3)], [free("a", (1, 1)), free("b", (-1, -1))]))
    assert result.outcome == "halted" and result.unresolved[0].kind == "corner_contact"
    assert result.final_state.time == 1 and result.events == ()


@pytest.mark.parametrize("rules, reason", [
    ([], "no_rule"),
    ([{"rule_id": "ew", "a": {"kind": 0, "port": "E"}, "b": {"kind": 0, "port": "W"}, "threshold": "100"}],
     "below_threshold"),
])
def test_a_contact_that_cannot_bond_halts(rules, reason) -> None:
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 0)], [free("a", (1, 0)), free("b", (-1, 0))], rules=rules))
    assert result.outcome == "halted"
    (u,) = result.unresolved
    assert u.kind == "non_binding_collision_unresolved" and u.reason == reason


def test_a_face_without_a_port_halts() -> None:
    materials = [{"kind": 0, "mass": "1", "contact_half_width": "1/2", "ports": ["N", "S"]}]
    rules = [{"rule_id": "ns", "a": {"kind": 0, "port": "N"}, "b": {"kind": 0, "port": "S"}, "threshold": "0"}]
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 0)], [free("a", (1, 0)), free("b", (-1, 0))],
                       materials=materials, rules=rules))
    assert result.unresolved[0].reason == "no_port"


def test_two_contacts_claiming_one_port_halt_as_contested() -> None:
    spec = world([("x", 0, 0, 0), ("a", 0, 5, "-1/2"), ("b", 0, 5, "1/2")],
                 [free("x"), free("a", (-1, 0)), free("b", (-1, 0))])
    result = run(spec)
    assert result.outcome == "halted"
    assert {u.kind for u in result.unresolved} == {"contested_contact"}
    # every contender is recorded -- none is quietly kept as the winner
    assert {label for u in result.unresolved for label, _ in u.participants} == {"x", "a", "b"}


def test_a_halt_applies_nothing_at_that_instant() -> None:
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 0)], [free("a", (1, 0)), free("b", (-1, 0))], rules=[]))
    assert len(result.final_state.structures) == 2 and result.final_state.time == 1


# ---------------------------------------------------------------------------
# 5. Instants.
# ---------------------------------------------------------------------------

def test_three_bodies_meeting_at_once_merge_once() -> None:
    spec = world([("w", 0, -4, 0), ("m", 0, 0, 0), ("e", 0, 4, 0)],
                 [free("w", (1, 0)), free("m"), free("e", (-1, 0))])
    (event,) = run(spec).events
    assert event.round == 0 and len(event.bonds) == 2 and len(event.pre) == 3
    assert event.post.members == frozenset({"w", "m", "e"}) and event.post.momentum == (0, 0)


def test_same_time_existing_event_cannot_be_deferred_to_next_round() -> None:
    """A-B and B-C are both real events at t: both belong to round 0, in one merge."""
    spec = world([("a", 0, -3, 0), ("b", 0, 0, 0), ("c", 0, 3, 0)],
                 [free("a", (1, 0)), free("b"), free("c", (-1, 0))])
    events = run(spec).events
    assert [e.round for e in events] == [0] and len(events[0].bonds) == 2


def test_a_causal_round_follows_a_velocity_change_at_the_same_instant() -> None:
    """c rests flush against b (not an event). a hits b; the merged ab now moves
    into c -- a new event at the same instant, caused by round 0."""
    spec = world([("a", 0, -3, 0), ("b", 0, 0, 0), ("c", 0, 1, 0)],
                 [free("a", (2, 0)), free("b"), free("c")])
    events = run(spec).events
    assert [(e.time, e.round) for e in events] == [(1, 0), (1, 1)]
    assert events[1].post.members == frozenset({"a", "b", "c"})


def test_resting_flush_contact_is_not_an_event_but_pressing_is() -> None:
    resting = world([("a", 0, 0, 0), ("b", 0, 1, 0)], [free("a", (0, 1)), free("b", (0, 1))])
    assert run(resting).events == ()
    pressing = world([("a", 0, 0, 0), ("b", 0, 1, 0)], [free("a", (1, 0)), free("b")])
    (event,) = run(pressing).events
    assert event.time == 0                                           # P4: already touching and pressing in


# ---------------------------------------------------------------------------
# 6. Invariances.
# ---------------------------------------------------------------------------

def _mixed():
    return world([("a", 0, 0, 0), ("b", 0, 4, 0), ("c", 0, 10, 0), ("d", 0, 0, 6), ("e", 0, 0, 12),
                  ("h", 1, 20, 20)],
                 [free("a", (1, 0)), free("b", (-1, 0)), free("c", ("-1/3", 0)), free("d", (0, 1)),
                  free("e", (0, "-1/2")), free("h", ("1/7", "1/5"))])


MAPPINGS = [{"a": "z9", "b": "b", "c": "a", "d": "q", "e": "00", "h": "m"},
            {"a": "e", "b": "d", "c": "c", "d": "b", "e": "a", "h": "h"}]


@pytest.mark.parametrize("mapping", MAPPINGS)
def test_relabelling_preserves_physical_outcome(mapping) -> None:
    spec = _mixed()
    assert run(spec.relabeled(mapping)).physics() == run(spec).relabeled(mapping).physics()


def test_input_order_does_not_matter() -> None:
    spec = _mixed()
    shuffled = WorldSpecV5(spec.world_id, spec.units, tuple(reversed(spec.materials)),
                           tuple(reversed(spec.bond_rules)), tuple(random.Random(3).sample(spec.elements, 6)),
                           tuple(reversed(spec.structures)))
    assert shuffled.digest == spec.digest
    assert run(shuffled).physics() == run(spec).physics()


def test_observation_interval_is_not_physics() -> None:
    results = {k: run(_mixed(), end=30, interval=k) for k in (Fraction(1), Fraction(1, 2), Fraction(1, 3))}
    physics = {k: r.physics() for k, r in results.items()}
    assert physics[Fraction(1)] == physics[Fraction(1, 2)] == physics[Fraction(1, 3)]
    by_time = {k: {o.time: o.canonical() for o in r.observations} for k, r in results.items()}
    for t in range(0, 31):
        assert by_time[Fraction(1)][t] == by_time[Fraction(1, 2)][t] == by_time[Fraction(1, 3)][t]


def test_galilean_boost_changes_no_event() -> None:
    """E6: add the same velocity u to everything (no fixed boundary in v5-v1)."""
    spec = _mixed()
    u = (Fraction(3, 2), Fraction(-2, 5))
    boosted = WorldSpecV5(spec.world_id, spec.units, spec.materials, spec.bond_rules, spec.elements,
                          tuple(type(s)(s.members, s.bonds,
                                        (s.momentum[0] + u[0] * _mass(spec, s), s.momentum[1] + u[1] * _mass(spec, s)),
                                        s.internal_energy) for s in spec.structures))
    plain, moved = run(spec), run(boosted)
    assert [(e.time, e.round, e.bonds, e.post.internal_energy, e.kinetic_energy_absorbed) for e in plain.events] == \
           [(e.time, e.round, e.bonds, e.post.internal_energy, e.kinetic_energy_absorbed) for e in moved.events]
    shift = {e.label: e.position for e in plain.final_state.elements}
    for element in moved.final_state.elements:
        x, y = shift[element.label]
        assert element.position == (x + u[0] * 40, y + u[1] * 40)


def _mass(spec, s):
    kinds = {e.label: e.kind for e in spec.elements}
    return sum((spec.material(kinds[m]).mass for m in s.members), Fraction(0))


@pytest.mark.parametrize("tangential, bonds", [(0, False), (4, True)])
def test_threshold_is_total_relative_energy_not_normal_impact(tangential, bonds) -> None:
    """E5: slow approach along x, fast sliding along y. Relative KE with mu = 1/2:
    (1/4)(1 + t^2). Threshold 2: t=0 -> 1/4 (halt), t=4 -> 17/4 (bond)."""
    rules = [{"rule_id": "ew", "a": {"kind": 0, "port": "E"}, "b": {"kind": 0, "port": "W"}, "threshold": "2"}]
    # contact after 1 time unit (gap 2 - 1 = 1 closed at speed 1); start b so dy = 0 then
    spec = world([("a", 0, 0, 0), ("b", 0, 2, -tangential)], [free("a"), free("b", (-1, tangential))], rules=rules)
    result = run(spec)
    assert (result.outcome == "completed" and len(result.events) == 1) is bonds


def test_threshold_ignores_how_fast_the_pair_travels_together() -> None:
    """E5/E6: a pair flying east at speed 9-10 but closing at only 1 has relative KE
    1/4 -- below a threshold of 1 -- even though their total KE is 90.5."""
    rules = [{"rule_id": "ew", "a": {"kind": 0, "port": "E"}, "b": {"kind": 0, "port": "W"}, "threshold": "1"}]
    result = run(world([("a", 0, 0, 0), ("b", 0, 3, 0)], [free("a", (10, 0)), free("b", (9, 0))], rules=rules))
    assert result.outcome == "halted" and result.unresolved[0].reason == "below_threshold"


def test_the_meter_changes_nothing() -> None:
    plain = run(_mixed())
    metered = run(_mixed(), meter=DenominatorMeter())
    assert metered.physics() == plain.physics() and metered.meter_summary["events"] == len(plain.events)


# ---------------------------------------------------------------------------
# 7. Structural guards.
# ---------------------------------------------------------------------------

PHYSICS_MODULES = ["v5_number", "v5_spec", "v5_state", "v5_reference"]


@pytest.mark.parametrize("module", PHYSICS_MODULES)
def test_no_float_can_enter_the_physics(module) -> None:
    tree = ast.parse((ROOT / "engine" / "deterministic" / f"{module}.py").read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            offenders.append(f"float literal line {node.lineno}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "float":
            offenders.append(f"float() line {node.lineno}")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if any(n in ("math", "cmath", "numpy", "time", "random") for n in names):
                offenders.append(f"imports {names} line {node.lineno}")
    assert offenders == [], offenders


def test_every_physical_value_in_a_result_is_exact() -> None:
    result = run(_mixed())

    def walk(value):
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
    walk(result.canonical())
    for state in (result.final_state, *result.observations):
        for element in state.elements:
            assert all(type(c) is Fraction for c in element.position)


def test_momentum_and_energy_are_conserved_over_a_run() -> None:
    spec = _mixed()
    result = run(spec)
    assert initial_state(spec).totals(spec) == result.final_state.totals(spec)
