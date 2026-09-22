"""GT-3: A affects C only when gate D is enabled -- C := A AND D.

Free-standing, like World 2 (see package docstring and `world2_direct.py`
for why this does not reuse `causal_kernel`). D is a gating condition, not a
mediator: the intended structure is

        D
        |
        v
    A ----> C   (only when D is true)

not `A -> D -> C`. The audit below checks exactly that distinction: holding
D fixed at each value and varying A, rather than treating D as a node A
passes through.

Only three booleans are involved, so every reachable (source_active,
gate_enabled) pair is run -- 4 cases, exhaustively, not sampled.
"""
from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass

from .report import GroundTruthReport

FORMAT = "ground-truth-conditional-world-v1"


@dataclass(frozen=True)
class ConditionalState:
    source_active: bool
    gate_enabled: bool
    outcome_active: bool

    def canonical(self) -> dict[str, object]:
        return {"format": FORMAT, "gate_enabled": self.gate_enabled,
                "outcome_active": self.outcome_active, "source_active": self.source_active}


def step(state: ConditionalState) -> ConditionalState:
    """The entire A3 rule: C is A AND D. Nothing else is read or written."""
    return ConditionalState(source_active=state.source_active, gate_enabled=state.gate_enabled,
                            outcome_active=state.source_active and state.gate_enabled)


def _world_digest() -> str:
    return hashlib.sha256(inspect.getsource(step).encode("utf-8")).hexdigest()


_EXPECTED_TABLE = {
    (False, False): False,
    (True, False): False,
    (False, True): False,
    (True, True): True,
}


def audit_world3_conditional() -> GroundTruthReport:
    report = GroundTruthReport(
        world_id="GT-3-conditional-A-to-C-gated-by-D",
        world_spec_digest=_world_digest(),
        expected_edges=(("source_active", "outcome_active"),),  # conditional on gate_enabled, not routed through it
        forbidden_edges=(("source_active", "gate_enabled"), ("gate_enabled", "source_active")),
        exhaustive=True,
    )

    try:
        cases_checked = 0
        for (source_active, gate_enabled), expected in _EXPECTED_TABLE.items():
            initial = ConditionalState(source_active=source_active, gate_enabled=gate_enabled, outcome_active=False)
            result = step(initial)
            cases_checked += 1
            report.add(f"truth_table_A={int(source_active)}_D={int(gate_enabled)}",
                       result.outcome_active == expected,
                       expected=expected, observed=result.outcome_active,
                       detail="one of the 4 exhaustive (source_active, gate_enabled) combinations")
        report.exhaustive_cases_checked = cases_checked

        # The gate-defining check: with D held fixed at false, varying A must
        # never move C.
        c_at_a0_d0 = step(ConditionalState(False, False, False)).outcome_active
        c_at_a1_d0 = step(ConditionalState(True, False, False)).outcome_active
        report.add("D_false_blocks_A_effect_on_C", c_at_a0_d0 == c_at_a1_d0,
                   expected="outcome_active identical for A=0 and A=1 when gate_enabled=False",
                   observed={"C_at_A0_D0": c_at_a0_d0, "C_at_A1_D0": c_at_a1_d0})

        # With D held fixed at true, varying A must move C.
        c_at_a0_d1 = step(ConditionalState(False, True, False)).outcome_active
        c_at_a1_d1 = step(ConditionalState(True, True, False)).outcome_active
        report.add("D_true_lets_A_affect_C", c_at_a0_d1 != c_at_a1_d1,
                   expected="outcome_active differs between A=0 and A=1 when gate_enabled=True",
                   observed={"C_at_A0_D1": c_at_a0_d1, "C_at_A1_D1": c_at_a1_d1})

        # D is a gate, not a mediator A passes through: A must never change D.
        d_before = True
        after_a_change = step(ConditionalState(source_active=not d_before, gate_enabled=d_before, outcome_active=False))
        report.add("A_never_changes_D", after_a_change.gate_enabled == d_before,
                   expected=d_before, observed=after_a_change.gate_enabled,
                   detail="rules out A -> D -> C being mistaken for the intended A -[if D]-> C")

        source_text = inspect.getsource(step)
        reads_both_inputs = "state.source_active" in source_text and "state.gate_enabled" in source_text
        report.add("step_function_reads_both_source_and_gate", reads_both_inputs,
                   expected="step()'s body references both source_active and gate_enabled",
                   observed={"source": source_text.strip()})
    except Exception as error:  # noqa: BLE001
        report.mark_audit_error(f"{type(error).__name__}: {error}")

    return report
