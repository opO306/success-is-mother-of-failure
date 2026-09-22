"""GT-M1: the canonical mediator benchmark -- A -> B -> C with B independently controllable.

GT-1 (`gt1_physical_mediator_legacy.py`) shows the real A0 bond physics is
consistent with a mediator, but A0 gives no public control that flips the
bond independently of heat -- GT-1's "block B" intervention has to change
the whole world (particle placement) rather than just B, so it cannot
cleanly separate "B mediates" from "this other world has no route from A to
C at all". GT-M1 is a purpose-built synthetic world that fixes exactly this:
`mediator_active` (B) has its own public control, separate from `source_active`
(A), so the three mediator-defining interventions can be run in the strict
sense -- vary A alone, vary B alone, and vary A while B is pinned.

    state: (source_active: bool, mediator_active: bool, outcome_active: bool)
    step:  mediator_active := source_active   (unless mediator_active was
                                                forced by an intervention --
                                                see `step_with_mediator_override`)
           outcome_active   := mediator_active

Two step functions are defined:

  `step` is the world's own one-tick rule, used to confirm A really does
  drive B under ordinary (non-intervened) evolution -- intervention 1.

  `step_with_mediator_override` lets a caller pin `mediator_active` to a
  chosen value for this tick regardless of `source_active` -- the public
  control B0.7's public-control discipline says a mediator benchmark needs.
  It is what makes interventions 2 and 3 possible in the strict sense GT-1
  could not achieve: intervention 2 varies B alone (A held fixed) to show B
  changes C, and intervention 3 pins B while varying A to show blocking B
  severs A's effect on C, in the *same* world rather than a different one.

This is exhaustive: only 4 (source_active, mediator_active) combinations
exist for the override check, and only 2 for the ordinary-evolution check.

B is never exposed this module or its ground-truth answer (see
`ground_truth/__init__.py`) -- this is the answer key, not the world B
would be handed to research. An A-compatible, B-researchable version of
this same world (with `mediator_active` as a real, engine-level public
control) is planned to ride the same `ResearchWorldAdapter` path GT-2/GT-3
need; see CURRENT_STATE.md for status. Until that lands, GT-M1 exists only
at the ground-truth level: it seals the *intended* structure so the future
executable world has an answer to be checked against from day one.
"""
from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass

from .report import GroundTruthReport

FORMAT = "ground-truth-mediator-world-v1"


@dataclass(frozen=True)
class MediatorState:
    source_active: bool
    mediator_active: bool
    outcome_active: bool

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "mediator_active": self.mediator_active,
                "outcome_active": self.outcome_active, "source_active": self.source_active}


def step(state: MediatorState) -> MediatorState:
    """Ordinary evolution, no intervention: B follows A, C follows B."""
    mediator_active = state.source_active
    return MediatorState(source_active=state.source_active, mediator_active=mediator_active,
                         outcome_active=mediator_active)


def step_with_mediator_override(state: MediatorState, forced_mediator: bool) -> MediatorState:
    """The public control on B: pin mediator_active to `forced_mediator` this tick.

    source_active is still read and carried forward (it is not deleted by
    the intervention), but it does not determine mediator_active while this
    override is in effect -- only outcome_active continues to follow
    whatever mediator_active ends up being.
    """
    return MediatorState(source_active=state.source_active, mediator_active=forced_mediator,
                         outcome_active=forced_mediator)


def _world_digest() -> str:
    raw = inspect.getsource(step) + inspect.getsource(step_with_mediator_override)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def audit_world_m1_mediator() -> GroundTruthReport:
    report = GroundTruthReport(
        world_id="GT-M1-mediator-canonical-A-to-B-to-C",
        world_spec_digest=_world_digest(),
        expected_edges=(("source_active", "mediator_active"), ("mediator_active", "outcome_active")),
        forbidden_edges=(("source_active", "outcome_active"),),
        exhaustive=True,
    )

    try:
        cases_checked = 0

        # --- intervention 1: A changes B, under ordinary (non-intervened) evolution ---
        for source_active in (False, True):
            result = step(MediatorState(source_active, False, False))
            cases_checked += 1
            report.add(f"A_changes_B_ordinary_evolution_source={source_active}",
                       result.mediator_active == source_active,
                       expected=source_active, observed=result.mediator_active,
                       detail="one of 2 exhaustive cases: mediator_active follows source_active "
                              "when nothing overrides it")

        # --- intervention 2: B changes C, A held fixed, B varied via the override control ---
        c_with_b_false = step_with_mediator_override(MediatorState(True, False, False), forced_mediator=False)
        c_with_b_true = step_with_mediator_override(MediatorState(True, False, False), forced_mediator=True)
        cases_checked += 2
        report.add("B_changes_C_with_A_held_fixed",
                   c_with_b_false.outcome_active != c_with_b_true.outcome_active,
                   expected="outcome_active differs when mediator_active is forced False vs True, "
                            "with source_active identical (True) in both",
                   observed={"outcome_with_B_false": c_with_b_false.outcome_active,
                             "outcome_with_B_true": c_with_b_true.outcome_active})

        # --- intervention 3, the defining check: pin B, vary A, C must not move ---
        for forced_mediator in (False, True):
            outcome_a0 = step_with_mediator_override(MediatorState(False, False, False), forced_mediator).outcome_active
            outcome_a1 = step_with_mediator_override(MediatorState(True, False, False), forced_mediator).outcome_active
            cases_checked += 2
            report.add(f"blocking_B_at_{forced_mediator}_severs_A_effect_on_C",
                       outcome_a0 == outcome_a1,
                       expected="outcome_active identical across source_active=False/True "
                                f"when mediator_active is pinned at {forced_mediator}",
                       observed={"outcome_source_False": outcome_a0, "outcome_source_True": outcome_a1},
                       detail="the strict mediator check GT-1 could only approximate: here B is "
                              "pinned in the SAME world via a real control, not by constructing a "
                              "different initial placement")

        report.exhaustive_cases_checked = cases_checked

        source_text = inspect.getsource(step_with_mediator_override)
        override_ignores_source_for_mediator = "forced_mediator" in source_text and \
            "mediator_active=state.source_active" not in source_text
        report.add("override_control_reads_forced_value_not_source",
                   override_ignores_source_for_mediator,
                   expected="step_with_mediator_override sets mediator_active from forced_mediator, "
                            "not from state.source_active",
                   observed={"source": source_text.strip()},
                   detail="static confirmation the override is a genuine independent control on B, "
                          "not source_active relabelled")
    except Exception as error:  # noqa: BLE001
        report.mark_audit_error(f"{type(error).__name__}: {error}")

    return report
