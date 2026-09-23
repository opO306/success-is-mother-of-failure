"""Seal-then-execute: the two journal steps every blind B loop shares.

Moved out of `research_loop.py` (which re-exports both): that module is the
physical-world research loop and imports the particle-world adapter, so the
blind loops (`blind_research_loop`, `probe_research`) that needed only these
two functions were pulling A's particle kernel into their import closure.
Found while freezing grammar v3 (G11 follow-up).
"""
from __future__ import annotations

from .causal_experiment import PredictionSeal
from .execution import AExecutor, ExecutionResult
from .research_journal import ResearchJournal
from .research_world import ResearchWorldSpec


def seal_predictions(journal: ResearchJournal, seal: PredictionSeal) -> PredictionSeal:
    """Journal predictions before execution. `seal.sealed_at_seq` must match this append's sequence.

    Enforcing that match here is what makes the seal-before-execution ordering
    a checkable fact rather than a convention callers might violate.
    """
    if seal.sealed_at_seq != journal.next_sequence:
        raise ValueError(
            f"seal claims sequence {seal.sealed_at_seq} but the journal's next "
            f"sequence is {journal.next_sequence}; seal immediately before appending")
    journal.append("prediction_sealed", seal.seal_id, seal.canonical())
    return seal


def execute_through_a(journal: ResearchJournal, executor: AExecutor,
                      arm_id: str, submitted_spec: ResearchWorldSpec) -> ExecutionResult:
    """Run `submitted_spec` through `executor` and journal the outcome, success or failure."""
    result = executor.execute(submitted_spec)
    journal.append("execution_completed", arm_id, result.canonical())
    return result
