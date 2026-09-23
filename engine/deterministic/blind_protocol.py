"""G7.2: Protocol Integrity -- B's predictions are sealed before it sees a
result, and its final answer is sealed before any evaluator appears.

This module adds no new inference. It reuses `PredictionSeal` and
`seal_predictions()` (`causal_experiment.py`/`research_loop.py`) exactly as
they already exist -- `seal_predictions` already refuses a seal whose
`sealed_at_seq` does not match `journal.next_sequence`, which is the
existing enforcement this Gate builds on rather than duplicates. What is
new here is (1) `FinalDiscoverySeal`, the B-side terminal answer a research
journal is sealed with, and (2) `audit_protocol`, a journal-replay checker
that proves -- from the recorded history, not from a caller's claim -- that
every execution had a prior seal and that nothing happened after the final
seal.

Required order, both enforced live (via `seal_predictions`'s existing
check) and auditable after the fact (via `audit_protocol`'s replay):

    blind descriptor -> hypotheses -> experiment candidate -> prediction
        -> PredictionSeal -> execute -> observe/compare -> update hypotheses
        -> ... -> FinalDiscoverySeal -> (only now) an evaluator may appear

This module is B/protocol-side, exactly like `blind_session.py`: it must
never import `blind_evaluator`, `ground_truth`, or `synthetic_runtime`
(`tests/test_deterministic_blind_protocol.py`'s dependency-boundary tests
enforce this by AST, both the qualified and bare relative-import forms --
see `blind_session.py`'s own docstring for why bare relative names matter
here). It knows about `BlindWorldDescriptor` (an alias-only world id),
`CausalHypothesisSet`, `PredictionSeal`, and `ResearchJournal` --
nothing about real world identity.

What this Gate deliberately does not do (see `CURRENT_STATE.md`'s G7.2
scope note): run autonomous discovery, score against ground truth, run a
held-out intervention, check alias 3-permutation robustness, run a
9-session certification, or produce a `PASS`/`INFERENCE_FAILURE` verdict.
`BlindProtocolAudit` reports structured violation codes only -- a later
Gate's evaluator composes those into an external verdict, not this one.

Accidents (`causal_experiment.detect_accident`: intended/submitted/executed
spec digests disagreeing) and protocol violations (seal/order/final-freeze
broken) are different failure kinds and must not be merged: an accident is
"the experiment wasn't prepared or executed as intended"; a protocol
violation is "the research procedure itself was broken" (predicted after
seeing the result, or the research state kept changing after B declared it
finished). Nothing in this module reports an accident, and nothing in
`causal_experiment.py`'s accident detection reports a protocol violation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .causal_hypothesis import CausalHypothesisSet
from .research_journal import GENESIS_DIGEST, JournalEntry, ResearchJournal, read_journal

FORMAT = "blind-protocol-v1"

EVENT_FINAL_DISCOVERY_SEALED = "final_discovery_sealed"
# G8: an arm declared, before it runs, to be observation-only -- executed
# without sealed predictions because it tests nothing; its result may set
# B's observed initial values but must never score a hypothesis.
EVENT_OBSERVATION_ONLY_DECLARED = "observation_only_declared"

VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL = "EXECUTION_WITHOUT_PRIOR_SEAL"
VIOLATION_SEAL_AFTER_EXECUTION = "SEAL_AFTER_EXECUTION"
VIOLATION_DUPLICATE_ARM_EXECUTION = "DUPLICATE_ARM_EXECUTION"
VIOLATION_FINAL_SEAL_MISSING = "FINAL_SEAL_MISSING"
VIOLATION_FINAL_SEAL_NOT_TERMINAL = "FINAL_SEAL_NOT_TERMINAL"
VIOLATION_FINAL_SEAL_SEQUENCE_MISMATCH = "FINAL_SEAL_SEQUENCE_MISMATCH"
VIOLATION_FINAL_SEAL_JOURNAL_DIGEST_MISMATCH = "FINAL_SEAL_JOURNAL_DIGEST_MISMATCH"
VIOLATION_FINAL_HYPOTHESIS_DIGEST_MISMATCH = "FINAL_HYPOTHESIS_DIGEST_MISMATCH"
VIOLATION_EXECUTED_ARM_SET_MISMATCH = "EXECUTED_ARM_SET_MISMATCH"
VIOLATION_OBSERVATION_ONLY_SCORED = "OBSERVATION_ONLY_SCORED"
VIOLATION_OBSERVATION_DECLARED_AFTER_EXECUTION = "OBSERVATION_DECLARED_AFTER_EXECUTION"

VIOLATION_CODES = frozenset({
    VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL, VIOLATION_SEAL_AFTER_EXECUTION,
    VIOLATION_DUPLICATE_ARM_EXECUTION, VIOLATION_FINAL_SEAL_MISSING,
    VIOLATION_FINAL_SEAL_NOT_TERMINAL, VIOLATION_FINAL_SEAL_SEQUENCE_MISMATCH,
    VIOLATION_FINAL_SEAL_JOURNAL_DIGEST_MISMATCH, VIOLATION_FINAL_HYPOTHESIS_DIGEST_MISMATCH,
    VIOLATION_EXECUTED_ARM_SET_MISMATCH, VIOLATION_OBSERVATION_ONLY_SCORED,
    VIOLATION_OBSERVATION_DECLARED_AFTER_EXECUTION,
})


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


def _texts_unique_sorted(values: tuple[str, ...], context: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{context} must be a tuple")
    for value in values:
        _text(value, context)
    if len(set(values)) != len(values):
        raise ValueError(f"{context} must not repeat")
    return tuple(sorted(values))


@dataclass(frozen=True)
class FinalDiscoverySeal:
    """B's terminal declaration for one blind research journal: which
    experiments it ran, what its final hypothesis set is, and which
    hypotheses remain unresolved -- sealed before any evaluator appears.

    Carries no real-world identity: `alias_world_id` is the only world
    reference, matching `BlindWorldDescriptor.alias_world_id`
    (`blind_session.py`). `real_world_id`/`real_world_revision`/
    `ground_truth_id`/`rule`/`fingerprint` must never be added here --
    see this module's docstring and
    `tests/test_deterministic_blind_protocol.py`'s leakage tests.

    Every field except `seal_id` is meant to be computed by
    `seal_final_discovery` from the journal and hypothesis set it is
    given, not assembled by hand by a caller -- see that function's
    docstring for why.
    """
    seal_id: str
    alias_world_id: str
    sealed_at_seq: int
    final_hypothesis_set_digest: str
    journal_terminal_digest: str
    executed_arm_ids: tuple[str, ...]
    experiment_count: int
    unresolved_hypothesis_ids: tuple[str, ...]
    format: str = FORMAT

    def __post_init__(self) -> None:
        _text(self.seal_id, "seal_id")
        _text(self.alias_world_id, "alias_world_id")
        _text(self.final_hypothesis_set_digest, "final_hypothesis_set_digest")
        _text(self.journal_terminal_digest, "journal_terminal_digest")
        if isinstance(self.sealed_at_seq, bool) or not isinstance(self.sealed_at_seq, int) or self.sealed_at_seq < 0:
            raise ValueError("sealed_at_seq must be a nonnegative integer")
        if tuple(sorted(self.executed_arm_ids)) != tuple(self.executed_arm_ids) or \
                len(set(self.executed_arm_ids)) != len(self.executed_arm_ids):
            raise ValueError("executed_arm_ids must be sorted and unique")
        for arm_id in self.executed_arm_ids:
            _text(arm_id, "executed_arm_ids entry")
        if self.experiment_count != len(self.executed_arm_ids):
            raise ValueError("experiment_count must equal len(executed_arm_ids)")
        if tuple(sorted(self.unresolved_hypothesis_ids)) != tuple(self.unresolved_hypothesis_ids) or \
                len(set(self.unresolved_hypothesis_ids)) != len(self.unresolved_hypothesis_ids):
            raise ValueError("unresolved_hypothesis_ids must be sorted and unique")
        for hypothesis_id in self.unresolved_hypothesis_ids:
            _text(hypothesis_id, "unresolved_hypothesis_ids entry")
        if self.format != FORMAT:
            raise ValueError("unsupported blind protocol format")

    def canonical(self) -> dict[str, object]:
        return {
            "alias_world_id": self.alias_world_id,
            "executed_arm_ids": list(self.executed_arm_ids),
            "experiment_count": self.experiment_count,
            "final_hypothesis_set_digest": self.final_hypothesis_set_digest,
            "format": self.format,
            "journal_terminal_digest": self.journal_terminal_digest,
            "seal_id": self.seal_id,
            "sealed_at_seq": self.sealed_at_seq,
            "unresolved_hypothesis_ids": list(self.unresolved_hypothesis_ids),
        }


def _executed_arm_ids(entries: tuple[JournalEntry, ...]) -> tuple[str, ...]:
    return tuple(sorted({entry.record_id for entry in entries if entry.event_type == "execution_completed"}))


def seal_final_discovery(
    journal: ResearchJournal, alias_world_id: str,
    final_hypothesis_set: CausalHypothesisSet, unresolved_hypothesis_ids: tuple[str, ...],
) -> FinalDiscoverySeal:
    """Compute and append the terminal seal for `journal`.

    Deliberately authoritative rather than a thin constructor call: a
    caller supplies only `alias_world_id`, the final hypothesis set, and
    which hypothesis ids remain unresolved. Every other field --
    `sealed_at_seq`, `journal_terminal_digest`, `executed_arm_ids`,
    `experiment_count` -- is read back from the journal itself, so a
    caller cannot claim an executed-arm set or a terminal digest the
    journal does not actually show. `unresolved_hypothesis_ids` is still
    caller-supplied because "which hypotheses remain open" is a judgment
    about the hypothesis set B is submitting, not something recoverable
    purely from `execution_completed`/`hypothesis_status_changed` events
    without also re-deriving `hypothesis_assessment` logic this Gate does
    not touch.
    """
    _text(alias_world_id, "alias_world_id")
    entries = read_journal(journal.path)
    executed_arm_ids = _executed_arm_ids(entries)
    sealed_at_seq = journal.next_sequence
    journal_terminal_digest = entries[-1].record_digest if entries else GENESIS_DIGEST

    seal = FinalDiscoverySeal(
        seal_id=f"FDS-{sealed_at_seq}",
        alias_world_id=alias_world_id,
        sealed_at_seq=sealed_at_seq,
        final_hypothesis_set_digest=final_hypothesis_set.digest,
        journal_terminal_digest=journal_terminal_digest,
        executed_arm_ids=executed_arm_ids,
        experiment_count=len(executed_arm_ids),
        unresolved_hypothesis_ids=_texts_unique_sorted(unresolved_hypothesis_ids, "unresolved_hypothesis_ids"),
    )
    journal.append(EVENT_FINAL_DISCOVERY_SEALED, seal.seal_id, seal.canonical())
    return seal


@dataclass(frozen=True)
class BlindProtocolAudit:
    """The result of replaying a journal to check protocol integrity.

    Structured violation codes only -- no PASS/FAIL verdict composition
    happens here. A later Gate's evaluator is responsible for turning
    these into an external verdict such as PROTOCOL_VIOLATION.
    """
    valid: bool
    violation_codes: tuple[str, ...]

    def canonical(self) -> dict[str, object]:
        return {"valid": self.valid, "violation_codes": list(self.violation_codes)}


def audit_protocol(path: Path) -> BlindProtocolAudit:
    """Replay a journal from genesis and check protocol integrity by the
    recorded history alone -- never by trusting a caller's claim that it
    sealed before executing.

    Checks, in the order violations are discovered during replay:
      - every `execution_completed` has a strictly-earlier `prediction_sealed`
        for the same `arm_id` -- or a strictly-earlier
        `observation_only_declared` for it (G8), in which case that arm must
        never be sealed or compared against any hypothesis (read from that entry's own payload, not its
        `record_id` -- `prediction_sealed`'s `record_id` is `seal_id`, not
        `arm_id`; see this function's own payload reads below)
      - no `arm_id` has more than one `execution_completed`
      - if a `final_discovery_sealed` entry exists, nothing follows it in
        the journal
      - the (last, if several -- though a valid journal has at most one
        by the terminal check above) `final_discovery_sealed` entry's
        recorded `sealed_at_seq`/`journal_terminal_digest`/
        `executed_arm_ids` match what replay independently computes
    A missing `final_discovery_sealed` entry is reported as
    `FINAL_SEAL_MISSING` -- a journal mid-research (no final seal yet) is
    not itself a violation to `seal_final_discovery`, but a caller asking
    this function "is this journal's protocol complete and closed" gets a
    `False`/`FINAL_SEAL_MISSING` answer until one exists.
    """
    entries = read_journal(path)
    violations: list[str] = []

    sealed_arm_seq: dict[str, int] = {}
    executed_arm_seq: dict[str, int] = {}
    observation_only: set[str] = set()
    final_seal_entry: JournalEntry | None = None
    final_seal_index: int | None = None

    for index, entry in enumerate(entries):
        if final_seal_entry is not None:
            violations.append(VIOLATION_FINAL_SEAL_NOT_TERMINAL)
            break
        if entry.event_type == EVENT_OBSERVATION_ONLY_DECLARED:
            arm_id = entry.record_id
            if arm_id in executed_arm_seq:
                violations.append(VIOLATION_OBSERVATION_DECLARED_AFTER_EXECUTION)
            if arm_id in sealed_arm_seq:
                violations.append(VIOLATION_OBSERVATION_ONLY_SCORED)
            observation_only.add(arm_id)
        elif entry.event_type == "result_compared" and entry.record_id in observation_only:
            violations.append(VIOLATION_OBSERVATION_ONLY_SCORED)
        elif entry.event_type == "prediction_sealed":
            arm_id = entry.payload.get("arm_id")
            if isinstance(arm_id, str):
                if arm_id in observation_only:
                    violations.append(VIOLATION_OBSERVATION_ONLY_SCORED)
                if arm_id in executed_arm_seq:
                    # A seal arriving after that arm's execution was already
                    # journaled -- "predicted after seeing the result".
                    violations.append(VIOLATION_SEAL_AFTER_EXECUTION)
                if arm_id not in sealed_arm_seq:
                    sealed_arm_seq[arm_id] = entry.sequence
        elif entry.event_type == "execution_completed":
            arm_id = entry.record_id
            if arm_id in executed_arm_seq:
                violations.append(VIOLATION_DUPLICATE_ARM_EXECUTION)
            executed_arm_seq[arm_id] = entry.sequence
            if arm_id not in sealed_arm_seq and arm_id not in observation_only:
                violations.append(VIOLATION_EXECUTION_WITHOUT_PRIOR_SEAL)
        elif entry.event_type == EVENT_FINAL_DISCOVERY_SEALED:
            final_seal_entry = entry
            final_seal_index = index

    if final_seal_entry is None:
        violations.append(VIOLATION_FINAL_SEAL_MISSING)
    else:
        prior_entries = entries[:final_seal_index]
        expected_sealed_at_seq = final_seal_entry.sequence
        expected_terminal_digest = prior_entries[-1].record_digest if prior_entries else GENESIS_DIGEST
        expected_executed_arm_ids = _executed_arm_ids(prior_entries)

        payload = final_seal_entry.payload
        if payload.get("sealed_at_seq") != expected_sealed_at_seq:
            violations.append(VIOLATION_FINAL_SEAL_SEQUENCE_MISMATCH)
        if payload.get("journal_terminal_digest") != expected_terminal_digest:
            violations.append(VIOLATION_FINAL_SEAL_JOURNAL_DIGEST_MISMATCH)
        if tuple(payload.get("executed_arm_ids", ())) != expected_executed_arm_ids:
            violations.append(VIOLATION_EXECUTED_ARM_SET_MISMATCH)

    return BlindProtocolAudit(valid=not violations, violation_codes=tuple(violations))


def audit_final_hypothesis_digest(path: Path, expected_final_hypothesis_set: CausalHypothesisSet) -> BlindProtocolAudit:
    """Separate from `audit_protocol` because it needs a hypothesis set to
    compare against, not just the journal -- checks that the journal's
    `final_discovery_sealed` entry's `final_hypothesis_set_digest` matches
    `expected_final_hypothesis_set.digest`."""
    entries = read_journal(path)
    final_seal_entries = [e for e in entries if e.event_type == EVENT_FINAL_DISCOVERY_SEALED]
    if not final_seal_entries:
        return BlindProtocolAudit(valid=False, violation_codes=(VIOLATION_FINAL_SEAL_MISSING,))
    payload = final_seal_entries[-1].payload
    if payload.get("final_hypothesis_set_digest") != expected_final_hypothesis_set.digest:
        return BlindProtocolAudit(valid=False, violation_codes=(VIOLATION_FINAL_HYPOTHESIS_DIGEST_MISMATCH,))
    return BlindProtocolAudit(valid=True, violation_codes=())
