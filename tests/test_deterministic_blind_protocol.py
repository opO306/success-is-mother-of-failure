"""G7.2: Protocol Integrity -- predictions are sealed before a result is
seen, and the final answer is sealed before any evaluator appears.

Journals here are built by hand, directly through `ResearchJournal.append`,
rather than by running `research_loop.seal_predictions`/`execute_through_a`
against a real executor -- this file tests `blind_protocol.py`'s replay
auditor against journals with controlled, deliberately-ordered event
sequences, the same way `test_deterministic_research_journal.py` builds
journals by hand to test the hash chain itself. What matters here is
whether `audit_protocol` correctly reads a journal's *recorded* history,
not whether a full research loop run would naturally produce a valid one
(that composition happens starting G7.3).

Sections:
  1. seal-before-execution ordering (live enforcement via seal_predictions,
     plus replay audit both ways)
  2. duplicate-arm-execution detection
  3. FinalDiscoverySeal computation (sealed_at_seq/journal_terminal_digest/
     executed_arm_ids/experiment_count all read back from the journal, not
     caller-supplied)
  4. terminal invariant (nothing after final_discovery_sealed)
  5. final hypothesis digest audit
  6. data leakage (no real identity in FinalDiscoverySeal's canonical())
  7. dependency boundary (blind_protocol.py never imports blind_evaluator/
     ground_truth/synthetic_runtime)
  8. deliberate mutation of the auditor itself

What this file does NOT test, on purpose (see CURRENT_STATE.md's G7.2
scope note): autonomous discovery, ground-truth scoring, held-out
intervention, alias robustness, 9-session runs, or any PASS/
INFERENCE_FAILURE verdict. This Gate is protocol-order auditing only.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.deterministic.blind_protocol import (
    EVENT_FINAL_DISCOVERY_SEALED,
    VIOLATION_DUPLICATE_ARM_EXECUTION,
    VIOLATION_EXECUTED_ARM_SET_MISMATCH,
    VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL,
    VIOLATION_FINAL_HYPOTHESIS_DIGEST_MISMATCH,
    VIOLATION_FINAL_SEAL_JOURNAL_DIGEST_MISMATCH,
    VIOLATION_FINAL_SEAL_MISSING,
    VIOLATION_FINAL_SEAL_NOT_TERMINAL,
    VIOLATION_FINAL_SEAL_SEQUENCE_MISMATCH,
    VIOLATION_SEAL_AFTER_EXECUTION,
    FinalDiscoverySeal,
    audit_final_hypothesis_digest,
    audit_protocol,
    seal_final_discovery,
)
from engine.deterministic.causal_hypothesis import CausalHypothesis, CausalHypothesisSet
from engine.deterministic.causal_experiment import PredictionSeal
from engine.deterministic.research_journal import GENESIS_DIGEST, ResearchJournal, read_journal
from engine.deterministic.research_loop import seal_predictions
from engine.deterministic.research_observable_prediction import ObservablePrediction

ROOT = Path(__file__).resolve().parents[1]


def _hypothesis_set(subject_digest: str = "SUBJ-1") -> CausalHypothesisSet:
    hypothesis = CausalHypothesis(
        "H-1", "x1 determines x3", ("domain-1",),
        (ObservablePrediction(1, "x3", True),), (), "untested",
    )
    return CausalHypothesisSet(subject_digest, (hypothesis,))


def _seal(arm_id: str, sealed_at_seq: int) -> PredictionSeal:
    return PredictionSeal(f"SEAL-{arm_id}", arm_id, sealed_at_seq,
                          {"H-1": (ObservablePrediction(1, "x3", True),)})


def _execution_payload() -> dict[str, object]:
    return {"executed_spec_digest": "DEAD" * 16, "run": None, "status": "ok"}


# ---------------------------------------------------------------------------
# 1. Seal-before-execution ordering.
# ---------------------------------------------------------------------------

def test_normal_seal_then_execute_order_is_valid(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    seal_predictions(journal, _seal("ARM-1", journal.next_sequence))
    journal.append("execution_completed", "ARM-1", _execution_payload())
    journal.close()

    audit = audit_protocol(tmp_path / "journal.jsonl")
    assert VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL not in audit.violation_codes
    assert VIOLATION_SEAL_AFTER_EXECUTION not in audit.violation_codes


def test_execution_without_prior_seal_is_a_violation(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    journal.append("execution_completed", "ARM-1", _execution_payload())
    journal.close()

    audit = audit_protocol(tmp_path / "journal.jsonl")
    assert not audit.valid
    assert VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL in audit.violation_codes


def test_seal_after_execution_is_a_violation(tmp_path: Path) -> None:
    """Predicting after seeing the result: execution_completed appears
    first, then a prediction_sealed claiming the same arm_id -- the exact
    "grade the exam, then fill in the answer key" failure this Gate exists
    to catch."""
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    journal.append("execution_completed", "ARM-1", _execution_payload())
    journal.append("prediction_sealed", "SEAL-ARM-1", _seal("ARM-1", 5).canonical())
    journal.close()

    audit = audit_protocol(tmp_path / "journal.jsonl")
    assert not audit.valid
    assert VIOLATION_SEAL_AFTER_EXECUTION in audit.violation_codes
    # Also correctly flagged as execution-without-prior-seal, since at the
    # point execution_completed appears, no seal for ARM-1 exists yet.
    assert VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL in audit.violation_codes


def test_seal_predictions_rejects_wrong_sealed_at_seq(tmp_path: Path) -> None:
    """The existing enforcement this Gate reuses rather than duplicates --
    seal_predictions() itself refuses a seal whose sealed_at_seq does not
    match journal.next_sequence."""
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    with pytest.raises(ValueError, match="seal immediately before appending"):
        seal_predictions(journal, _seal("ARM-1", 99))


def test_prediction_sealed_matches_arm_by_payload_not_record_id(tmp_path: Path) -> None:
    """prediction_sealed's journal record_id is the seal_id, not the
    arm_id -- the auditor must read payload["arm_id"], never compare
    record_id to execution_completed's record_id directly."""
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    seal_predictions(journal, _seal("ARM-7", journal.next_sequence))
    logged_entry = read_journal(path)[-1]
    assert logged_entry.record_id == "SEAL-ARM-7"
    assert logged_entry.payload["arm_id"] == "ARM-7"
    journal.append("execution_completed", "ARM-7", _execution_payload())
    journal.close()

    audit = audit_protocol(tmp_path / "journal.jsonl")
    assert VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL not in audit.violation_codes


# ---------------------------------------------------------------------------
# 2. Duplicate-arm-execution detection.
# ---------------------------------------------------------------------------

def test_duplicate_arm_execution_is_a_violation(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    seal_predictions(journal, _seal("ARM-1", journal.next_sequence))
    journal.append("execution_completed", "ARM-1", _execution_payload())
    seal_predictions(journal, _seal("ARM-1-retry", journal.next_sequence))
    journal.append("execution_completed", "ARM-1", _execution_payload())
    journal.close()

    audit = audit_protocol(tmp_path / "journal.jsonl")
    assert not audit.valid
    assert VIOLATION_DUPLICATE_ARM_EXECUTION in audit.violation_codes


def test_retry_with_a_new_arm_id_is_not_a_duplicate(tmp_path: Path) -> None:
    journal = ResearchJournal.create(tmp_path / "journal.jsonl")
    seal_predictions(journal, _seal("ARM-1", journal.next_sequence))
    journal.append("execution_completed", "ARM-1", _execution_payload())
    seal_predictions(journal, _seal("ARM-2", journal.next_sequence))
    journal.append("execution_completed", "ARM-2", _execution_payload())
    journal.close()

    audit = audit_protocol(tmp_path / "journal.jsonl")
    assert VIOLATION_DUPLICATE_ARM_EXECUTION not in audit.violation_codes


# ---------------------------------------------------------------------------
# 3. FinalDiscoverySeal computation.
# ---------------------------------------------------------------------------

def _run_two_valid_experiments(journal: ResearchJournal) -> None:
    seal_predictions(journal, _seal("ARM-1", journal.next_sequence))
    journal.append("execution_completed", "ARM-1", _execution_payload())
    seal_predictions(journal, _seal("ARM-2", journal.next_sequence))
    journal.append("execution_completed", "ARM-2", _execution_payload())


def test_seal_final_discovery_computes_fields_from_the_journal(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)

    entries_before_seal = read_journal(path)
    expected_terminal_digest = entries_before_seal[-1].record_digest
    expected_next_seq = journal.next_sequence

    seal = seal_final_discovery(journal, "ALIAS-8FA19C", _hypothesis_set(), ())
    journal.close()

    assert seal.sealed_at_seq == expected_next_seq
    assert seal.journal_terminal_digest == expected_terminal_digest
    assert seal.executed_arm_ids == ("ARM-1", "ARM-2")
    assert seal.experiment_count == 2
    assert seal.final_hypothesis_set_digest == _hypothesis_set().digest
    assert seal.unresolved_hypothesis_ids == ()


def test_seal_final_discovery_on_empty_journal_uses_genesis_digest(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    seal = seal_final_discovery(journal, "ALIAS-EMPTY", _hypothesis_set(), ())
    journal.close()

    assert seal.journal_terminal_digest == GENESIS_DIGEST
    assert seal.executed_arm_ids == ()
    assert seal.experiment_count == 0


def test_seal_final_discovery_appends_final_discovery_sealed_event(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    journal.close()

    entries = read_journal(path)
    assert entries[-1].event_type == EVENT_FINAL_DISCOVERY_SEALED


def test_caller_cannot_claim_arm_ids_that_were_not_executed() -> None:
    """FinalDiscoverySeal itself does not validate executed_arm_ids against
    a journal -- only seal_final_discovery computes them authoritatively,
    and audit_protocol independently checks a stored seal against replay
    (see EXECUTED_ARM_SET_MISMATCH tests below). This test only confirms
    the dataclass's own structural invariants (sorted/unique/non-empty)."""
    with pytest.raises(ValueError, match="sorted and unique"):
        FinalDiscoverySeal(
            "FDS-1", "ALIAS-1", 3, "digest-h", "digest-j",
            executed_arm_ids=("ARM-2", "ARM-1"),  # not sorted
            experiment_count=2, unresolved_hypothesis_ids=(),
        )


def test_final_discovery_seal_rejects_experiment_count_mismatch() -> None:
    with pytest.raises(ValueError, match="experiment_count"):
        FinalDiscoverySeal(
            "FDS-1", "ALIAS-1", 3, "digest-h", "digest-j",
            executed_arm_ids=("ARM-1",), experiment_count=2, unresolved_hypothesis_ids=(),
        )


# ---------------------------------------------------------------------------
# 4. Terminal invariant.
# ---------------------------------------------------------------------------

def test_event_after_final_discovery_sealed_is_a_violation(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    # A hypothetical bug: B keeps updating its research state after
    # declaring itself finished.
    journal.append("hypothesis_status_changed", "H-1", {
        "hypothesis_id": "H-1", "new_status": "contradicted_in_domain",
        "previous_status": "active", "reason": "post-seal edit",
    })
    journal.close()

    audit = audit_protocol(path)
    assert not audit.valid
    assert VIOLATION_FINAL_SEAL_NOT_TERMINAL in audit.violation_codes


def test_execution_after_final_discovery_sealed_is_a_violation(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    seal_predictions(journal, _seal("ARM-3", journal.next_sequence))
    journal.append("execution_completed", "ARM-3", _execution_payload())
    journal.close()

    audit = audit_protocol(path)
    assert not audit.valid
    assert VIOLATION_FINAL_SEAL_NOT_TERMINAL in audit.violation_codes


def test_journal_with_no_final_seal_reports_missing(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    journal.close()

    audit = audit_protocol(path)
    assert not audit.valid
    assert VIOLATION_FINAL_SEAL_MISSING in audit.violation_codes


# ---------------------------------------------------------------------------
# 5. Final-seal self-consistency (sequence / journal digest / executed arms).
# ---------------------------------------------------------------------------

def test_tampered_final_seal_sequence_is_a_violation(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    journal.close()

    _tamper_last_entry_payload(path, {"sealed_at_seq": 999})
    audit = audit_protocol(path)
    assert not audit.valid
    assert VIOLATION_FINAL_SEAL_SEQUENCE_MISMATCH in audit.violation_codes


def test_tampered_final_seal_journal_digest_is_a_violation(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    journal.close()

    _tamper_last_entry_payload(path, {"journal_terminal_digest": "F" * 64})
    audit = audit_protocol(path)
    assert not audit.valid
    assert VIOLATION_FINAL_SEAL_JOURNAL_DIGEST_MISMATCH in audit.violation_codes


def test_tampered_executed_arm_ids_is_a_violation(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    journal.close()

    _tamper_last_entry_payload(path, {"executed_arm_ids": ["ARM-1", "ARM-99"]})
    audit = audit_protocol(path)
    assert not audit.valid
    assert VIOLATION_EXECUTED_ARM_SET_MISMATCH in audit.violation_codes


def _tamper_last_entry_payload(path: Path, updates: dict[str, object]) -> None:
    import json
    lines = path.read_text(encoding="utf-8").splitlines()
    raw = json.loads(lines[-1])
    raw["payload"].update(updates)
    lines[-1] = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 6. Final hypothesis digest audit.
# ---------------------------------------------------------------------------

def test_final_hypothesis_digest_matches_when_correct(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    journal.close()

    audit = audit_final_hypothesis_digest(path, _hypothesis_set())
    assert audit.valid


def test_final_hypothesis_digest_mismatch_is_a_violation(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal_final_discovery(journal, "ALIAS-1", _hypothesis_set(), ())
    journal.close()

    different_hypothesis_set = _hypothesis_set(subject_digest="SUBJ-DIFFERENT")
    audit = audit_final_hypothesis_digest(path, different_hypothesis_set)
    assert not audit.valid
    assert VIOLATION_FINAL_HYPOTHESIS_DIGEST_MISMATCH in audit.violation_codes


def test_final_hypothesis_digest_audit_reports_missing_seal(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    journal.close()

    audit = audit_final_hypothesis_digest(path, _hypothesis_set())
    assert not audit.valid
    assert VIOLATION_FINAL_SEAL_MISSING in audit.violation_codes


# ---------------------------------------------------------------------------
# 7. Data leakage.
# ---------------------------------------------------------------------------

SECRET_VALUES = (
    "WORLD-S01", "WORLD-S02", "WORLD-S03",
    "R-7F93C2", "R-A18D40", "R-51E8B7",
    "GT-2", "GT-3", "GT-M1",
)

FORBIDDEN_FIELD_NAMES = frozenset({
    "real_world_id", "real_world_revision", "ground_truth_id", "rule", "fingerprint", "source",
})


def _serialize(value: object) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_final_discovery_seal_canonical_has_no_secret_values(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = ResearchJournal.create(path)
    _run_two_valid_experiments(journal)
    seal = seal_final_discovery(journal, "ALIAS-8FA19C", _hypothesis_set(), ())
    journal.close()

    serialized = _serialize(seal.canonical())
    for secret in SECRET_VALUES:
        assert secret not in serialized


def test_final_discovery_seal_has_no_forbidden_field_names() -> None:
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(FinalDiscoverySeal)}
    leaked = field_names & FORBIDDEN_FIELD_NAMES
    assert not leaked, f"FinalDiscoverySeal structurally carries forbidden fields: {leaked}"


# ---------------------------------------------------------------------------
# 8. Dependency boundary.
# ---------------------------------------------------------------------------

def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


FORBIDDEN_MODULES = {
    "ground_truth", "engine.deterministic.synthetic_runtime", ".synthetic_runtime", "synthetic_runtime",
    "engine.deterministic.blind_evaluator", ".blind_evaluator", "blind_evaluator",
}


def test_blind_protocol_does_not_import_forbidden_modules() -> None:
    path = ROOT / "engine" / "deterministic" / "blind_protocol.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name in FORBIDDEN_MODULES or name.startswith("ground_truth.") for name in imported)


def test_blind_protocol_has_no_wildcard_imports() -> None:
    path = ROOT / "engine" / "deterministic" / "blind_protocol.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    has_star = any(isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
                  for node in ast.walk(tree))
    assert not has_star


# Section 9 (deliberate mutation of blind_protocol.py's own logic -- the
# seal-after-execution check, the terminal-invariant check, and the
# dependency-boundary import) is not permanent test code: it was done by
# hand against the working tree during this Gate's implementation session
# (temporarily disabling each check and confirming the relevant test above
# fails, then reverting), per RULES.md's checker-defect-injection
# requirement. See CURRENT_STATE.md's G7.2 entry for what was verified.
