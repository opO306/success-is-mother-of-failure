"""G9: B composes its own experiment tools from primitive presses.

Sections:
  1. the primitive in A: a scheduled press/release, world rule untouched
  2. the primitive on B's side: schedules in blind specs and in B's own simulation
  3. tool design: new, informative, most severe against the closest rival
  4. tools in the loop: sealed like any experiment; failures recorded; reuse
  5. boundaries
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_execution import BlindCandidateSpec
from engine.deterministic.blind_hypothesis import DELAYED, DIRECT, BlindCausalClaim, predict_target
from engine.deterministic.blind_protocol import audit_protocol
from engine.deterministic.blind_research_loop import INSEPARABLE, SOLVED, run_blind_research
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.blind_tools import Tool
from engine.deterministic.research_journal import ResearchJournal, read_journal
from engine.deterministic.synthetic_kernel import RULE_S03, run_synthetic_world
from engine.deterministic.synthetic_spec import SyntheticScheduledClamp, SyntheticWorldSpec
from tests.test_deterministic_blind_hypothesis import FORBIDDEN_MODULES, _closure

V = ("x1", "x2", "x3")


def _spec(controls=("x1",), observables=("x1", "x3"), ticks=2, initial=None) -> SyntheticWorldSpec:
    initial = initial or {}
    return SyntheticWorldSpec(world_id="WORLD-S03", world_revision="R-51E8B7", variables=V,
                              initial_values=tuple((v, initial.get(v, False)) for v in V), clamps=(),
                              public_controls=controls, public_observables=observables, ticks=ticks)


def _run(tmp_path: Path, spec: SyntheticWorldSpec, seed: int = 0, name: str = "j.jsonl", **kwargs):
    world, manifest = make_blind_session(spec, seed)
    path = tmp_path / name
    journal = ResearchJournal.create(path)
    outcome = run_blind_research(world, control_descriptors(spec, seed), observable_descriptors(spec, seed),
                                 SyntheticBlindAExecutor(spec, manifest), journal, **kwargs)
    journal.close()
    real = {alias: n for n, alias in manifest.variable_alias.items()}
    statements = {h.hypothesis_id: " ".join(real.get(t, t) for t in h.statement.split())
                  for h in outcome.final_hypothesis_set.hypotheses}
    return outcome, read_journal(path), path, manifest, statements


# ---------------------------------------------------------------------------
# 1. The primitive in A.
# ---------------------------------------------------------------------------

def test_a_press_at_one_tick_reaches_x3_two_ticks_later_in_the_real_world() -> None:
    pulse = replace(_spec(), schedule=(SyntheticScheduledClamp(0, "x1", "ON"), SyntheticScheduledClamp(1, "x1", "OFF"),
                                        SyntheticScheduledClamp(2, "x1", "OFF")))
    values = [dict(c.values) for c in run_synthetic_world(pulse, RULE_S03).checkpoints]
    assert [(v["x1"], v["x3"]) for v in values] == [(True, False), (False, False), (False, True)]


def test_a_world_without_a_schedule_keeps_its_exact_digest() -> None:
    assert "schedule" not in _spec().canonical()


@pytest.mark.parametrize("schedule", [
    (SyntheticScheduledClamp(0, "x2", "ON"),),                                  # not a public control
    (SyntheticScheduledClamp(9, "x1", "ON"),),                                  # past the run
    (SyntheticScheduledClamp(0, "x1", "ON"), SyntheticScheduledClamp(0, "x1", "OFF")),  # same tick twice
])
def test_invalid_schedules_are_refused(schedule) -> None:
    with pytest.raises(ValueError):
        replace(_spec(), schedule=schedule)


# ---------------------------------------------------------------------------
# 2. The primitive on B's side.
# ---------------------------------------------------------------------------

def test_blind_spec_without_schedule_keeps_its_digest() -> None:
    spec = BlindCandidateSpec("ALIAS-W", "BCAND-1", (("ALIAS-C", 1),), 1)
    assert "schedule" not in spec.canonical()


def test_b_simulates_a_press_the_way_a_runs_it() -> None:
    delayed = BlindCausalClaim(DELAYED, "T", ("A",), lag=2)
    direct = BlindCausalClaim(DIRECT, "T", ("A",))
    pulse = {0: {"A": True}, 1: {"A": False}, 2: {"A": False}}
    assert predict_target(delayed, {}, 2, schedule=pulse) is True    # A was on two ticks ago
    assert predict_target(direct, {}, 2, schedule=pulse) is False    # A was off one tick ago


def test_executor_runs_b_s_schedule_on_the_real_control(tmp_path) -> None:
    spec = _spec()
    world, manifest = make_blind_session(spec, 0)
    control = manifest.control_alias["x1"]
    blind = BlindCandidateSpec(world.alias_world_id, "BTOOL-0000000000000001", (), 2,
                               schedule=((0, control, 1), (1, control, 0), (2, control, 0)))
    run = SyntheticBlindAExecutor(spec, manifest).execute(blind).run
    x3 = manifest.observable_alias["x3"]
    assert [c.value_of(x3) for c in run.checkpoints] == [False, False, True]


# ---------------------------------------------------------------------------
# 3. Tool design.
# ---------------------------------------------------------------------------

def test_steady_holds_are_not_tools() -> None:
    with pytest.raises(ValueError):
        Tool((1, 1, 1), 2)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_b_invents_the_single_press_test_on_its_own(tmp_path, seed) -> None:
    """Given only "hold a control at 1/0 at tick t", B composes "press at
    tick 0, release after" -- the test that separates its idea ("after 2
    ticks") from its closest refuted rival ("after 1 tick"). Nobody named
    this pattern to B."""
    outcome, entries, path, _m, statements = _run(tmp_path, _spec(), seed=seed)
    [used] = outcome.tools_used
    assert used["tool"]["pattern"] == [1, 0, 0] and not used["reused"]
    [question] = outcome.questions
    assert question.verdict == SOLVED
    assert [statements[h] for h in question.surviving_hypothesis_ids] == ["x1 -> x3 after 2 ticks"]
    designed = [e for e in entries if e.event_type == "tool_designed"]
    assert len(designed) == 1 and designed[0].payload["risky_for_proposals"] == 1
    assert audit_protocol(path).valid


def test_severity_follows_the_closest_rival_not_a_head_count() -> None:
    """Hand-computed on the hidden-mediator question: holding x1 through tick
    1 and pressing it only at tick 0 tie on a plain count of disagreeing
    refuted claims; ranking rivals by closeness breaks the tie the right way."""
    from engine.deterministic.blind_hypothesis import INVERTED, NO_EFFECT
    from engine.deterministic.blind_tools import _score
    claims = {"idea": BlindCausalClaim(DELAYED, "T", ("A",), lag=2),
              "direct": BlindCausalClaim(DIRECT, "T", ("A",)),
              "null": BlindCausalClaim(NO_EFFECT, "T"),
              "inverted": BlindCausalClaim(INVERTED, "T", ("A",))}
    hold, press = Tool((1, 1, 0), 2), Tool((1, 0, 0), 2)
    flat = {"idea": ["direct", "inverted", "null"]}
    assert sum(_score(hold, "A", (), ("idea",), claims, "T", {}, False, flat)[2]) == \
        sum(_score(press, "A", (), ("idea",), claims, "T", {}, False, flat)[2])
    ranked = {"idea": ["direct", "null", "inverted"]}   # closest rivals first
    assert _score(press, "A", (), ("idea",), claims, "T", {}, False, ranked) > \
        _score(hold, "A", (), ("idea",), claims, "T", {}, False, ranked)


# ---------------------------------------------------------------------------
# 4. Tools in the loop.
# ---------------------------------------------------------------------------

def test_tool_experiment_is_sealed_before_it_runs(tmp_path) -> None:
    outcome, entries, path, *_ = _run(tmp_path, _spec())
    [arm] = outcome.tool_arm_ids
    index = next(i for i, e in enumerate(entries) if e.event_type == "execution_completed" and e.record_id == arm)
    assert entries[index - 1].event_type == "prediction_sealed" and entries[index - 1].payload["arm_id"] == arm
    assert audit_protocol(path).valid
    assert outcome.final_seal.experiment_count == (len(outcome.executed_candidate_ids) + len(outcome.observation_arm_ids)
                                                   + len(outcome.tool_arm_ids))


def test_a_tie_no_press_can_break_is_recorded_as_a_failed_search(tmp_path) -> None:
    """S03 with one tick: chain vs. its last edge. No press pattern within one
    tick separates them; B tries, fails, and says so -- the tie stands."""
    outcome, entries, *_ = _run(tmp_path, _spec(controls=("x1", "x2"), observables=V, ticks=1))
    failed = [e for e in entries if e.event_type == "tool_search_failed"]
    assert failed and failed[0].payload["reason"] == "no_informative_press_pattern"
    assert INSEPARABLE in {q.verdict for q in outcome.questions}
    assert outcome.tool_arm_ids == ()


def test_a_tool_from_an_earlier_run_is_reused_instead_of_searching_again(tmp_path) -> None:
    first, *_ = _run(tmp_path, _spec(), seed=0, name="a.jsonl")
    toolbox = tuple(Tool.from_canonical(u["tool"]) for u in first.tools_used)
    second, entries, *_ = _run(tmp_path, _spec(), seed=1, name="b.jsonl", toolbox=toolbox)
    assert [u["reused"] for u in second.tools_used] == [True]
    assert any(e.event_type == "tool_reused" for e in entries)
    assert not any(e.event_type == "tool_designed" for e in entries)


def test_toolbox_is_read_from_b_s_own_memory_in_the_store(tmp_path) -> None:
    from research_store.b_visible import BVisibleReader
    from research_store.ingest_blind import store_blind_research_run
    from research_store.provenance import BLIND_RESEARCH_SEMANTICS
    spec = _spec()
    world, manifest = make_blind_session(spec, 0)
    path = tmp_path / "j.jsonl"
    journal = ResearchJournal.create(path)
    outcome = run_blind_research(world, control_descriptors(spec, 0), observable_descriptors(spec, 0),
                                 SyntheticBlindAExecutor(spec, manifest), journal)
    journal.close()
    prov = {"commit": "0" * 40, "dirty": False, "producer": "run_blind_benchmark.py",
            "semantics": BLIND_RESEARCH_SEMANTICS}
    store_blind_research_run(tmp_path / "store", real_spec=spec, seed=0, manifest=manifest, outcome=outcome,
                             journal_path=path, provenance=prov)
    assert BVisibleReader(tmp_path / "store").toolbox(semantics=BLIND_RESEARCH_SEMANTICS) == \
        [outcome.tools_used[0]["tool"]]


def test_no_tools_when_nothing_needs_one(tmp_path) -> None:
    outcome, entries, *_ = _run(tmp_path, _spec(controls=("x1", "x2"), observables=V, ticks=2))
    assert outcome.tool_arm_ids == () and not any(e.event_type.startswith("tool") for e in entries)


# ---------------------------------------------------------------------------
# 5. Boundaries.
# ---------------------------------------------------------------------------

def test_tool_module_cannot_reach_evaluator_or_answer_modules() -> None:
    closure = _closure("blind_tools")
    assert not closure & FORBIDDEN_MODULES and "ground_truth" not in closure
    assert "blind_tools" in _closure("blind_research_loop")


def test_tool_journal_carries_no_real_identity(tmp_path) -> None:
    spec = _spec()
    _outcome, _entries, path, *_ = _run(tmp_path, spec)
    text = path.read_text(encoding="utf-8")
    for secret in ("WORLD-S03", "R-51E8B7", spec.digest, '"x1"', '"x2"', '"x3"'):
        assert secret not in text
