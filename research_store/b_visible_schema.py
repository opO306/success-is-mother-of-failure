"""Allowlist for every string written to the b_visible tier.

The literal leak scan (`b_visible._scan`) rejects strings known to be secret.
This module is the second, stronger wall: it rejects every string that is
not *known to be allowed*. A b_visible value may contain, as a dict key or a
string value, only:

  * an id of a known alias-only shape (ALIAS-XXXXXXXX, BCAND-..., BH-...,
    SEAL-BCAND-..., BPLAN-..., FDS-n, hex digests, a git commit),
  * a hypothesis statement built only from alias ids and the fixed words of
    the G7.3b vocabulary ("->", "AND", "OR", "NOT", "no controllable
    variable affects"),
  * an applicability condition of a fixed shape (alias_world:<alias>,
    baseline:true|false, time:one_tick_per_edge),
  * a comma-joined list of verdict words,
  * an exception class name (the executor reports only the class, never
    the message -- see `blind_synthetic_executor`),
  * a word from `VOCABULARY` below, enumerated by hand.

Why enumerate the vocabulary instead of allowing "any snake_case word": the
real variable names of the benchmark worlds (x1, x2, x3) are themselves
snake_case words. A pattern loose enough to admit every field name would
admit them too. Enumerating means a new field name fails loudly until
someone adds it here on purpose -- a b_visible schema change becomes a
decision someone wrote down, not a side effect.

What this cannot catch, stated plainly: information carried by *non-string*
structure -- counts, ordering, booleans, integer values. Those are allowed
by design (B's observations are booleans; its counts are its own), and a
leak through them would have to be designed in upstream, not typed in by
accident. This guards the accident.

Pure: imports no engine module, no other tier.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_ALIAS = r"ALIAS-[0-9A-F]{8}"

_ID_PATTERNS = tuple(re.compile(p) for p in (
    rf"^{_ALIAS}$",
    r"^BCAND-[0-9a-f]{16}$", r"^BPLAN-[0-9a-f]{16}$", r"^BH-[0-9a-f]{16}$",
    r"^SEAL-(BCAND|BTOOL)-[0-9a-f]{16}$", r"^BTOOL-[0-9a-f]{16}$", r"^BTOOLDEF-[0-9a-f]{16}$", r"^FDS-\d+$", r"^BOBS-[0-9a-f]{16}$",
    r"^[0-9a-f]{64}$",            # sha256 digests
    r"^[0-9a-f]{40}$",            # git commit
    rf"^alias_world:{_ALIAS}$", r"^baseline:(true|false)$", r"^time:one_tick_per_edge$",
    r"^initial:observed$", r"^origin:noticed$",
    r"^[A-Z][A-Za-z]*(Error|Exception)$",   # exception class name only
))

_STATEMENT = re.compile(
    rf"^(no controllable variable affects {_ALIAS}"
    rf"|(NOT )?{_ALIAS}( (AND|OR) {_ALIAS})? -> {_ALIAS}"
    rf"|{_ALIAS} -> {_ALIAS} after \d+ ticks"
    rf"|{_ALIAS} -> {_ALIAS} -> {_ALIAS})$")

VERDICT_WORDS = frozenset({"SOLVED", "INSEPARABLE", "NO_SURVIVOR", "OPEN"})

VOCABULARY = frozenset({
    # record / provenance / tags
    "alias_world_id", "commit", "dirty", "producer", "semantics", "protocol_valid", "termination",
    "validated_fully", "verdicts", "true", "false", "unknown", "run_blind_benchmark.py",
    "blind_research_run", "provenance", "tags",
    # stored payload
    "journal", "outcome", "final_hypothesis_set", "protocol_audit", "valid", "violation_codes",
    # journal entries
    "event_type", "format", "payload", "previous_digest", "record_digest", "record_id", "sequence",
    "hypothesis_set_created", "experiment_candidate_ranked", "prediction_sealed", "execution_completed",
    "observation_recorded", "result_compared", "hypothesis_status_changed", "final_discovery_sealed",
    "b0-research-journal-v1",
    # selection record
    "phase", "discovery", "validation", "horizon", "expected_split_pairs", "expected_split_pairs_by_question",
    # hypotheses and predictions
    "hypothesis_set", "target_observable_id", "hypotheses", "hypothesis_id", "statement",
    "applicability_conditions", "predictions", "evidence", "status", "parent_hypothesis_ids",
    "child_hypothesis_ids", "subject_digest", "message_type", "causal_hypothesis_set", "causal-hypothesis-v1",
    "control_values", "prediction", "kind", "interventional", "interventional-prediction-v1",
    "observable_id", "expected_value", "tick", "observable_value",
    "untested", "supported", "underspecified", "contradicted_in_domain",
    # seals, execution, observation
    "seal_id", "arm_id", "sealed_at_seq", "predictions_by_hypothesis", "causal-experiment-v1",
    "error_kind", "error_message", "executed_spec_digest", "run_digest", "success", "failed",
    "causal-execution-result-v1", "execution failed (details withheld -- blind boundary)",
    "run", "checkpoints", "observables", "blind-execution-v1", "held", "rejected",
    # final seal
    "alias_world_id", "executed_arm_ids", "experiment_count", "final_hypothesis_set_digest",
    "journal_terminal_digest", "unresolved_hypothesis_ids", "blind-protocol-v1",
    # outcome
    "questions", "verdict", "surviving_hypothesis_ids", "rejected_hypothesis_ids", "inseparable_pairs",
    "executed_candidate_ids", "discovery_experiment_count", "plan_size", "final_seal",
    "blind-research-loop-v1", "COMPLETE", "LIMIT_REACHED", "HARNESS_FAILURE",
    # evidence links (G7.4+)
    "evidence_id", "relation", "source_digest", "description", "supports", "refutes",
    "prediction_held", "prediction_failed",
    # B's own limitation assessment (G7.4+, blind_limitations.py)
    "limitation", "limitation_assessed", "diagnosis", "pairs", "hypothesis_ids", "separable_at_horizon",
    "checked_up_to_horizon", "blind-limitations-v1", "observation_horizon", "not_diagnosable", "mixed",
    "vocabulary_exhausted", "budget_exhausted", "none",
    # G8: look first, surprise, notice
    "observation_only_declared", "reason", "initial_values", "observation_arm_ids", "anomaly_recorded",
    "all_hypotheses_refuted", "hypothesis_noticed", "derived_from", "hypothesis", "trigger_arm",
    "proposed_hypothesis_ids", "proposal_untested", "blind-research-loop-v2", "lag",
    "OBSERVATION_ONLY_SCORED", "OBSERVATION_DECLARED_AFTER_EXECUTION",
    # G9: tools composed from primitive presses
    "tool_designed", "tool_reused", "tool_search_failed", "tool", "pattern", "control_id",
    "risky_for_proposals", "severity_against_refuted", "tool_arm_ids", "tools_used", "tool_id", "reused",
    "no_informative_press_pattern", "blind-tool-v1", "blind-research-loop-v3",
    # protocol audit violation codes (blind_protocol.VIOLATION_CODES)
    "EXECUTION_WITHOUT_PRIOR_SEAL", "SEAL_AFTER_EXECUTION", "DUPLICATE_ARM_EXECUTION",
    "FINAL_SEAL_MISSING", "FINAL_SEAL_NOT_TERMINAL", "FINAL_SEAL_SEQUENCE_MISMATCH",
    "FINAL_SEAL_JOURNAL_DIGEST_MISMATCH", "FINAL_HYPOTHESIS_DIGEST_MISMATCH", "EXECUTED_ARM_SET_MISMATCH",
}) | VERDICT_WORDS


class SchemaViolation(ValueError):
    """A string bound for b_visible is not on the allowlist."""


@dataclass(frozen=True)
class StringPolicy:
    """Which strings may appear in a b_visible value. `semantics` lists the
    exact research-semantics labels allowed in provenance."""
    semantics: frozenset[str]
    vocabulary: frozenset[str] = VOCABULARY

    def allows(self, text: str) -> bool:
        if text in self.vocabulary or text in self.semantics:
            return True
        if any(p.match(text) for p in _ID_PATTERNS) or _STATEMENT.match(text):
            return True
        parts = text.split(",")
        return len(parts) > 1 and all(part in VERDICT_WORDS for part in parts)

    def check(self, value: Any) -> None:
        """Raise `SchemaViolation` on the first disallowed string -- keys
        included. The offending string is *not* echoed in the message: if
        it is a leak, the error text must not carry it onward."""
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                for key, sub in item.items():
                    if not isinstance(key, str) or not self.allows(key):
                        raise SchemaViolation("disallowed key in b_visible value")
                    stack.append(sub)
            elif isinstance(item, (list, tuple)):
                stack.extend(item)
            elif isinstance(item, str):
                if not self.allows(item):
                    raise SchemaViolation(f"disallowed string of length {len(item)} in b_visible value")
            elif item is None or isinstance(item, (bool, int)):
                continue
            else:
                raise SchemaViolation(f"disallowed value type {type(item).__name__} in b_visible value")
