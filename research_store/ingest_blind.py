"""Evaluator side: store one G7.3c blind research run, split by tier.

    b_visible    "blind_research_run"  B's full journal (hypothesis sets,
                                       sealed predictions, observed runs,
                                       comparisons, rejections, final seal),
                                       its outcome, and the G7.2 protocol
                                       audit of that journal. Alias-only.
    evaluator    "blind_run_binding"   which real world/revision/seed that
                                       alias world was, the real spec, and
                                       the alias<->real mapping; references
                                       the b_visible record's payload.
    ground_truth (nothing yet)         scoring B's answer against the truth
                                       is G7.4 and will land here.

A run whose journal fails the protocol audit is still stored -- failures are
data -- but tagged `protocol_valid=false` so no reader mistakes it for a
clean run.
"""
from __future__ import annotations

from pathlib import Path

from engine.deterministic.blind_evaluator import BlindTranslationManifest
from engine.deterministic.blind_protocol import audit_protocol
from engine.deterministic.research_journal import read_journal
from engine.deterministic.synthetic_spec import SyntheticWorldSpec

from ._core import EVALUATOR, StoreRecord
from .b_visible import BVisibleWriter
from .evaluator import EvaluatorStore

SCHEMA_VERSION = 1

# Benchmark-level identifiers that must never reach b_visible either,
# whichever world a run came from.
_GLOBAL_SECRETS = ("WORLD-S01", "WORLD-S02", "WORLD-S03", "R-7F93C2", "R-A18D40", "R-51E8B7",
                   "GT-2", "GT-3", "GT-M1", "RULE_S01", "RULE_S02", "RULE_S03")


def secrets_of(real_spec: SyntheticWorldSpec, manifest: BlindTranslationManifest) -> tuple[str, ...]:
    """Every string whose presence in b_visible data would reveal the real world."""
    names = set(real_spec.variables) | set(manifest.variable_alias)
    quoted = tuple(f'"{name}"' for name in sorted(names)) + tuple(f" {name} " for name in sorted(names))
    return tuple(sorted({real_spec.world_id, real_spec.world_revision, real_spec.digest,
                         manifest.real_world_id, manifest.real_world_revision,
                         *quoted, *_GLOBAL_SECRETS}))


def store_blind_research_run(root: Path, *, real_spec: SyntheticWorldSpec, seed: int,
                             manifest: BlindTranslationManifest, outcome, journal_path: Path,
                             provenance: dict[str, object]) -> tuple[StoreRecord, StoreRecord]:
    """Returns (b_visible record, evaluator record)."""
    secrets = secrets_of(real_spec, manifest)
    audit = audit_protocol(journal_path)
    journal = [entry.canonical() for entry in read_journal(journal_path)]

    b_writer = BVisibleWriter(root)
    b_payload = b_writer.put({"journal": journal, "outcome": outcome.canonical(),
                              "final_hypothesis_set": outcome.final_hypothesis_set.canonical(),
                              "protocol_audit": audit.canonical()}, forbidden_values=secrets)
    b_tags = {"alias_world_id": outcome.alias_world_id, "termination": outcome.termination,
              "protocol_valid": str(audit.valid).lower(),
              "validated_fully": str(outcome.validated_fully).lower(),
              "verdicts": ",".join(sorted(q.verdict for q in outcome.questions))}
    b_record = b_writer.record("blind_research_run", SCHEMA_VERSION, provenance, b_tags, b_payload,
                               forbidden_values=secrets)

    evaluator = EvaluatorStore(root)
    e_payload = evaluator.put(EVALUATOR, {
        "real_world_id": real_spec.world_id, "real_world_revision": real_spec.world_revision,
        "real_spec": real_spec.canonical(), "seed": seed,
        "alias_world_id": manifest.alias_world_id,
        "variable_alias": dict(manifest.variable_alias), "control_alias": dict(manifest.control_alias),
        "observable_alias": dict(manifest.observable_alias),
        "b_visible_payload": b_payload.canonical(), "b_visible_record_digest": b_record.record_digest,
    })
    e_tags = {"real_world_id": real_spec.world_id, "real_world_revision": real_spec.world_revision,
              "seed": str(seed), "ticks": str(real_spec.ticks), "alias_world_id": manifest.alias_world_id}
    e_record = evaluator.record(EVALUATOR, "blind_run_binding", SCHEMA_VERSION, provenance, e_tags, e_payload,
                                refs=(b_payload,))
    return b_record, e_record
