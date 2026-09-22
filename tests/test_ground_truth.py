"""Pins down the independent ground-truth audit's own behavior.

Two things must be true for `audit/ground_truth` to be trustworthy:

1. It never imports anything from B0.3 upward (the whole point is to build
   an answer key B0.7 is graded against without B0.7's code shaping the
   answer).
2. It actually distinguishes a valid world from an invalid one -- a report
   that always says VALID would be worthless as an answer key.
"""
from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from audit.ground_truth import audit_world1_mediator, audit_world2_direct, audit_world3_conditional
from audit.ground_truth.report import GroundTruthReport
from audit.ground_truth.world2_direct import DirectState, step as direct_step
from audit.ground_truth.world3_conditional import ConditionalState, step as conditional_step

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_DIR = ROOT / "audit" / "ground_truth"

# Anything from B0.3 upward -- the modules a circular "grade B by B" audit would reach for.
FORBIDDEN_MODULE_PREFIXES = (
    "engine.deterministic.mechanism_candidate",
    "engine.deterministic.mechanism_test",
    "engine.deterministic.mechanism_tester",
    "engine.deterministic.causal_path_builder",
    "engine.deterministic.causal_edge",
    "engine.deterministic.causal_edge_validator",
    "engine.deterministic.causal_timeline",
    "engine.deterministic.causal_graph_model",
    "engine.deterministic.causal_hypothesis",
    "engine.deterministic.missing_link_hypothesis",
    "engine.deterministic.missing_link_investigator",
    "engine.deterministic.research_journal",
    "engine.deterministic.trace_model",
    "engine.deterministic.adapter_comparison",
    "engine.deterministic.hypothesis_set",
    "engine.deterministic.counterfactual",
    "engine.deterministic.residual_pattern",
    "engine.deterministic.theory_revision",
    "engine.deterministic.experiment_proposal",
)


def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", sorted(GROUND_TRUTH_DIR.glob("*.py")))
def test_no_ground_truth_module_imports_b_code(path: Path) -> None:
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    violations = [name for name in imported
                 if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_MODULE_PREFIXES)]
    assert violations == [], f"{path.name} imports B0.3+ module(s): {violations}"


def test_world1_mediator_seals_valid_with_all_three_interventions_passing() -> None:
    report = audit_world1_mediator()
    assert report.verdict == "VALID"
    names = {c.name for c in report.checks}
    assert {"A_changes_B_heat_toggles_final_bond_state",
            "B_changes_C_bond_state_changes_final_kinetic_energy",
            "blocking_B_severs_A_to_C_effect"} <= names
    assert all(c.passed for c in report.checks)


def test_world2_direct_seals_valid_and_is_exhaustive() -> None:
    report = audit_world2_direct()
    assert report.verdict == "VALID"
    assert report.exhaustive is True
    assert report.exhaustive_cases_checked == 2


def test_world3_conditional_seals_valid_and_is_exhaustive_over_four_cases() -> None:
    report = audit_world3_conditional()
    assert report.verdict == "VALID"
    assert report.exhaustive is True
    assert report.exhaustive_cases_checked == 4


def test_world2_direct_step_matches_truth_table() -> None:
    assert direct_step(DirectState(False, False)).outcome_active is False
    assert direct_step(DirectState(True, False)).outcome_active is True


def test_world3_conditional_step_matches_truth_table() -> None:
    assert conditional_step(ConditionalState(False, False, False)).outcome_active is False
    assert conditional_step(ConditionalState(True, False, False)).outcome_active is False
    assert conditional_step(ConditionalState(False, True, False)).outcome_active is False
    assert conditional_step(ConditionalState(True, True, False)).outcome_active is True


# ---------------------------------------------------------------------------
# The audit must actually be able to fail -- an always-VALID checker is not
# an independent answer key, it is theater.
# ---------------------------------------------------------------------------

def test_report_verdict_is_invalid_world_when_a_check_fails() -> None:
    report = GroundTruthReport("GT-broken", "deadbeef", (("a", "c"),), (), exhaustive=True)
    report.add("case-1", True, expected=True, observed=True)
    report.add("case-2", False, expected=True, observed=False)
    assert report.verdict == "INVALID_WORLD"


def test_report_verdict_is_ambiguous_when_marked_so_even_with_passing_checks() -> None:
    report = GroundTruthReport("GT-x", "deadbeef", (), ())
    report.add("case-1", True, expected=True, observed=True)
    report.mark_ambiguous("precondition", "blocking construction did not hold")
    assert report.verdict == "AMBIGUOUS"


def test_report_verdict_is_audit_error_when_marked_so() -> None:
    report = GroundTruthReport("GT-x", "deadbeef", (), ())
    report.mark_audit_error("unexpected exception")
    assert report.verdict == "AUDIT_ERROR"


def test_report_with_no_checks_is_ambiguous_not_silently_valid() -> None:
    report = GroundTruthReport("GT-empty", "deadbeef", (), ())
    assert report.verdict == "AMBIGUOUS"


def test_world2_detects_a_broken_direct_relation() -> None:
    """A world where C never actually copies A must not seal VALID."""
    def broken_step(state: DirectState) -> DirectState:
        return DirectState(source_active=state.source_active, outcome_active=False)

    report = GroundTruthReport("GT-2-broken", "deadbeef", (("source_active", "outcome_active"),), (), exhaustive=True)
    for source_active in (False, True):
        result = broken_step(DirectState(source_active, False))
        report.add("case", result.outcome_active == source_active, source_active, result.outcome_active)
    assert report.verdict == "INVALID_WORLD"


def test_world3_detects_a_gate_that_never_blocks() -> None:
    """A world where D=false still lets A move C must not seal VALID."""
    def broken_step(state: ConditionalState) -> ConditionalState:
        return replace(state, outcome_active=state.source_active)  # ignores gate_enabled entirely

    c_at_a0_d0 = broken_step(ConditionalState(False, False, False)).outcome_active
    c_at_a1_d0 = broken_step(ConditionalState(True, False, False)).outcome_active
    report = GroundTruthReport("GT-3-broken", "deadbeef", (("source_active", "outcome_active"),), (), exhaustive=True)
    report.add("D_false_blocks_A_effect_on_C", c_at_a0_d0 == c_at_a1_d0, "identical", (c_at_a0_d0, c_at_a1_d0))
    assert report.verdict == "INVALID_WORLD"


def test_digest_is_stable_across_recomputation() -> None:
    first = audit_world2_direct()
    second = audit_world2_direct()
    assert first.digest == second.digest


def test_digest_excludes_itself_no_recursive_field() -> None:
    report = audit_world2_direct()
    assert "ground_truth_digest" not in report.canonical()
    assert "ground_truth_digest" in report.sealed()
