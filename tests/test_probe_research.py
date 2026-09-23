"""G11: B learns what its own probe's actions do (grammar v3).

Sections:
  1. grammar v3: sentence form, wrap-aware deltas, condition limits, frozen digest
  2. end-to-end: B's final claims, translated back through the evaluator's
     manifest, equal the probe's real behaviour -- 36 effects, all conditions
  3. how it got there: two conditions only after one failed; tests after changes
  4. what the language cannot say is marked unexplained, not forced -- and
     B designs the experiments that refute a coincidence (G11d)
  5. protocol, blindness, determinism across symbol shuffles
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.deterministic.blind_probe import BlindProbeCheckpoint
from engine.deterministic.blind_probe_evaluator import BlindProbeExecutor, make_probe_session
from engine.deterministic.blind_protocol import audit_protocol
from engine.deterministic.probe_grammar import (
    GRAMMAR_DIGEST, AtomicCondition, EffectClaim, Geometry, cell_subject, observed_delta,
)
from engine.deterministic.probe_planning import predict
from engine.deterministic.probe_research import run_probe_research
from engine.deterministic.probe_world import ProbeSpec, ProbeWorldSpec
from engine.deterministic.research_journal import ResearchJournal, read_journal
from tests.test_deterministic_blind_hypothesis import _closure
from tests.test_probe import _env

OFFSET = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


def _world(blocked=()):
    """Still world (no flows): every observed change is the probe's own."""
    minerals = [(3, 0, 0, 2), (1, 0, 0, 2), (2, 1, 0, 2), (2, 3, 0, 2)]    # one pile on each side
    return ProbeWorldSpec("PW-G11", "R-G11", _env(minerals, water_rate=0, blocked=blocked), ProbeSpec(2, 0, 5),
                          ("mineral", "heat"), 12)


def _research(tmp_path: Path, seed: int = 0, spec=None, name="j.jsonl"):
    spec = spec or _world()
    descriptor, manifest = make_probe_session(spec, seed)
    path = tmp_path / name
    journal = ResearchJournal.create(path)
    outcome = run_probe_research(descriptor, BlindProbeExecutor(spec, manifest), journal)
    journal.close()
    return outcome, manifest, path


def _real(manifest, claim: EffectClaim) -> tuple:
    action = {v: k for k, v in manifest.action_symbol.items()}
    direction = {v: k for k, v in manifest.direction_symbol.items()}
    channel = {v: k for k, v in manifest.channel_symbol.items()}

    def subject(s: str) -> str:
        if s.startswith("rel:"):
            _, offset, ch = s.split(":")
            return f"rel:{offset}:{channel[ch]}"
        return s
    return (action[claim.action], direction.get(claim.direction), subject(claim.subject), claim.delta,
            tuple(sorted((subject(c.subject), c.op, c.value) for c in claim.conditions)))


def _truth() -> set[tuple]:
    """What the probe really does (probe_world.py), in grammar v3 terms."""
    expected = set()
    for d, (dx, dy) in OFFSET.items():
        cell = f"rel:{dx:+d},{dy:+d}"
        energy = (("self.energy", ">=", 1),)
        expected |= {("MOVE", d, "self.x" if dx else "self.y", dx or dy, energy),
                     ("MOVE", d, "self.energy", -1, energy), ("MOVE", d, f"{cell}:heat", 1, energy),
                     ("HEAT", d, "self.energy", -1, energy), ("HEAT", d, f"{cell}:heat", 1, energy)}
        grasp = tuple(sorted(((f"{cell}:mineral", ">=", 1), ("self.holding", "=", 0))))
        expected |= {("GRASP", d, "self.holding", 1, grasp), ("GRASP", d, f"{cell}:mineral", -1, grasp)}
        release = (("self.holding", ">=", 1),)
        expected |= {("RELEASE", d, "self.holding", -1, release), ("RELEASE", d, f"{cell}:mineral", 1, release)}
    return expected


# ---------------------------------------------------------------------------
# 1. Grammar v3.
# ---------------------------------------------------------------------------

def test_grammar_v3_is_frozen() -> None:
    assert GRAMMAR_DIGEST == "7aff4cd75b1bf9675c818343dc507a2abfc78d888b962069cf9397c2ea48c155"


def test_position_change_is_measured_on_the_published_wrapping_grid() -> None:
    before = BlindProbeCheckpoint(0, (5, 0, 3, 0), ())
    after = BlindProbeCheckpoint(1, (0, 0, 2, 0), ())
    assert observed_delta("self.x", before, after, Geometry(6, 4, True)) == 1      # never -5


@pytest.mark.parametrize("kwargs", [
    dict(action="A", direction=None, subject="self.x", delta=0),                    # a claim names a change
    dict(action="A", direction=None, subject="self.speed", delta=1),                # unknown subject
    dict(action="A", direction=None, subject="rel:+2,0:CH", delta=1),               # beyond one step
    dict(action="A", direction=None, subject="self.x", delta=1, conditions=(
        AtomicCondition("self.x", ">=", 1), AtomicCondition("self.y", ">=", 1), AtomicCondition("self.energy", "=", 0))),
])
def test_claims_outside_grammar_v3_are_refused(kwargs) -> None:
    with pytest.raises(ValueError):
        EffectClaim(**kwargs)


def test_atomic_conditions_are_only_at_least_one_or_zero() -> None:
    with pytest.raises(ValueError):
        AtomicCondition("self.energy", ">=", 3)


# ---------------------------------------------------------------------------
# 2. End-to-end.
# ---------------------------------------------------------------------------

def test_b_recovers_exactly_what_its_probe_does(tmp_path) -> None:
    outcome, manifest, _path = _research(tmp_path)
    learned = {_real(manifest, r.claim) for r in outcome.final.claims}
    assert learned == _truth()
    assert all(r.status == "supported" for r in outcome.final.claims)
    assert outcome.final.unexplained == ()


@pytest.mark.parametrize("seed", [1, 2])
def test_the_result_does_not_depend_on_how_symbols_were_shuffled(tmp_path, seed) -> None:
    outcome, manifest, _path = _research(tmp_path, seed=seed)
    assert {_real(manifest, r.claim) for r in outcome.final.claims} == _truth()


# ---------------------------------------------------------------------------
# 3. How it got there.
# ---------------------------------------------------------------------------

def test_two_conditions_appear_only_for_grasp_and_only_by_refinement(tmp_path) -> None:
    outcome, manifest, path = _research(tmp_path)
    two = [r for r in outcome.final.claims if len(r.claim.conditions) == 2]
    assert {_real(manifest, r.claim)[0] for r in two} == {"GRASP"}
    assert all(len(r.claim.conditions) <= 1 for r in outcome.final.claims if _real(manifest, r.claim)[0] != "GRASP")
    proposed_with_two = [e for e in read_journal(path) if e.event_type == "probe_claim_proposed"
                         and e.payload["how"] == "two"]
    refined_to_two = [e for e in read_journal(path) if e.event_type == "probe_claim_refined"
                      and e.payload["how"] == "two"]
    assert refined_to_two            # B raised the complexity itself after single conditions failed
    assert not any(len(e.payload["claim"]["conditions"]) == 2 and e.payload["how"] != "two"
                   for e in proposed_with_two)


def test_every_final_claim_passed_a_test_run_after_it_last_changed(tmp_path) -> None:
    outcome, _manifest, path = _research(tmp_path)
    entries = read_journal(path)
    for result in outcome.final.claims:
        cid = result.claim.claim_id
        last_change = max(e.sequence for e in entries if e.record_id == cid
                          and e.event_type in ("probe_claim_proposed", "probe_claim_refined"))
        later = [e for e in entries if e.event_type == "result_compared" and e.sequence > last_change
                 and cid in e.payload["held"]]
        assert later and all(e.payload["held"][cid] for e in later)


def test_validation_caught_a_coincidental_condition(tmp_path) -> None:
    """Measured: before validation ran everything, a grasp claim carried the
    wrong neighbour's mineral as its condition (equal to the right one's in
    all data so far). The refinement history shows it being replaced."""
    outcome, manifest, _path = _research(tmp_path)
    grasp_conditions = [s for s, how in outcome.refinements if " when " in s and "holding = 0" in s]
    assert len(grasp_conditions) > len({s.split(":")[0] for s in grasp_conditions})   # some grasp refined twice+


# ---------------------------------------------------------------------------
# 4. What the language cannot say.
# ---------------------------------------------------------------------------

def _wall(tmp_path):
    return _research(tmp_path, spec=_world(blocked=[((2, 0), (3, 0))]))


def test_a_wall_the_language_cannot_name_is_marked_unexplained(tmp_path) -> None:
    """A wall east of the start cell stops MOVE E there only. No observable
    in grammar v3 says "a wall is east of me", so B must not keep a
    condition that happens to fit -- it marks the effect unexplained.
    Measured: the wall also blocks GRASP E and HEAT E across it, and those
    end unexplained too."""
    outcome, manifest, _path = _wall(tmp_path)
    action = {v: k for k, v in manifest.action_symbol.items()}
    direction = {v: k for k, v in manifest.direction_symbol.items()}
    real_unexplained = {(action[a], direction.get(d)) for a, d, _s in outcome.final.unexplained}
    assert real_unexplained == {("MOVE", "E"), ("GRASP", "E"), ("HEAT", "E")}


def test_no_wrong_claim_is_left_supported_in_the_wall_world(tmp_path) -> None:
    """Before G11d B left "moves east when the cell underfoot is warm" marked
    supported with 16 passed tests: a coincidence no pool program could
    refute. Every claim B still holds must now be true."""
    outcome, manifest, _path = _wall(tmp_path)
    assert all(_real(manifest, r.claim) in _truth() for r in outcome.final.claims)


def test_b_designed_the_refuting_experiments_itself(tmp_path) -> None:
    """The refutations came from programs B planned from its own claims:
    both sufficiency and necessity tests, and at least one contradicted a
    claim it was designed against."""
    _outcome, _manifest, path = _wall(tmp_path)
    entries = read_journal(path)
    designed = [e for e in entries if e.event_type == "probe_test_designed"]
    assert {e.payload["kind"] for e in designed} == {"sufficiency", "necessity"}
    contradicted = {(e.payload["arm_id"], e.record_id) for e in entries if e.event_type == "anomaly_recorded"}
    assert any((e.record_id, e.payload["claim_id"]) in contradicted for e in designed)


def test_designed_tests_are_sealed_before_they_run(tmp_path) -> None:
    _outcome, _manifest, path = _wall(tmp_path)
    entries = read_journal(path)
    for e in (e for e in entries if e.event_type == "probe_test_designed"):
        sealed = [x.sequence for x in entries if x.event_type == "prediction_sealed" and x.record_id == "SEAL-" + e.record_id]
        executed = [x.sequence for x in entries if x.event_type == "execution_completed" and x.record_id == e.record_id]
        assert sealed and executed and max(sealed) < min(executed)


def test_bs_model_predicts_a_step_from_its_own_claims() -> None:
    before = BlindProbeCheckpoint(0, (3, 0, 2, 0), ())
    claims = [EffectClaim("A", "D", "self.x", 1, (AtomicCondition("self.energy", ">=", 1),)),
              EffectClaim("A", "D", "rel:+1,+0:C", 1)]
    after = predict(claims, before, "A", "D", Geometry(4, 4, True))
    assert after.probe == (0, 0, 2, 0) and after.cells == ((0, 0, "C", 1),)    # wrapped


# ---------------------------------------------------------------------------
# 5. Protocol, blindness.
# ---------------------------------------------------------------------------

def test_journal_passes_the_protocol_audit(tmp_path) -> None:
    _outcome, _manifest, path = _research(tmp_path)
    assert audit_protocol(path).valid


def test_journal_names_no_real_action_direction_channel_or_world(tmp_path) -> None:
    _outcome, _manifest, path = _research(tmp_path)
    text = path.read_text(encoding="utf-8")
    for name in ('"MOVE"', '"GRASP"', '"RELEASE"', '"HEAT"', '"WAIT"', '"N"', '"E"', '"S"', '"W"',
                 ":mineral", ":heat", '"mineral"', '"heat"', "PW-G11", "R-G11"):
        assert name not in text


def test_b_side_modules_cannot_reach_a_or_the_translator() -> None:
    for module in ("probe_grammar", "probe_induction", "probe_planning", "probe_research"):
        closure = _closure(module)
        assert not closure & {"probe_world", "environment_kernel", "environment_spec", "blind_probe_evaluator",
                              "blind_evaluator", "synthetic_runtime"}, module
