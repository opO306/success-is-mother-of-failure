"""B0.4 Deep Investigator: InvestigationTarget -> traces -> DivergenceChain -> mechanism candidates -> follow-ups.

Takes a "red dot on the map" B0.3 already found (a `BoundaryCandidate` pair,
an `IsolatedCaseCandidate`) and asks exactly one question: where did the two
runs first genuinely differ, and what sequence of differences led to the
known outcome difference? It answers that question and stops -- it proposes
mechanism candidates and follow-up experiments, but running an intervention,
building a full causal graph, or deciding which candidate is "true" is later
work (see docs/README's B1/B2 scope).

Reuses B0.1/B0.2/B0.3 unchanged: `RealCausalAExecutor` for the two runs
(via `trace_model.run_traced`, which drives the same public
`causal_kernel.KernelObserver` hook rather than any private phase function),
and the same journal/append-only discipline for recording what was found.
"""
from __future__ import annotations

from dataclasses import dataclass

from .causal_spec import CausalWorldSpec
from .divergence_analysis import DivergenceChain, InterventionRecord, compare_snapshot_sequences
from .investigation_target import InvestigationTarget
from .mechanism_candidate import (
    FollowupExperimentProposal,
    MechanismCandidateSet,
    propose_mechanism_candidates,
)
from .research_journal import ResearchJournal
from .trace_model import TraceSpec, run_traced


def seal_investigation_target(journal: ResearchJournal, target: InvestigationTarget) -> InvestigationTarget:
    """Journal an InvestigationTarget before any trace is collected -- what is being compared is fixed first."""
    journal.append("investigation_target_sealed", target.target_id, target.canonical())
    return target


def trace_and_compare(
    journal: ResearchJournal, target: InvestigationTarget, trace_spec: TraceSpec,
    baseline_spec: CausalWorldSpec, contrast_spec: CausalWorldSpec,
    interventions: tuple[InterventionRecord, ...] = (),
) -> DivergenceChain:
    """Run both specs through the real causal kernel via `trace_model.run_traced` and compare the traces.

    `baseline_spec`/`contrast_spec` must match `target.baseline_spec_digest`/
    `target.contrast_spec_digest` -- the sealed target, not whatever specs a
    caller happens to pass, decides what this investigation is about.
    """
    if baseline_spec.digest != target.baseline_spec_digest:
        raise ValueError("baseline_spec does not match the sealed investigation target")
    if contrast_spec.digest != target.contrast_spec_digest:
        raise ValueError("contrast_spec does not match the sealed investigation target")
    baseline_trace = run_traced(baseline_spec, trace_spec)
    contrast_trace = run_traced(contrast_spec, trace_spec)
    chain = compare_snapshot_sequences(
        target.baseline_spec_digest, target.contrast_spec_digest, baseline_trace, contrast_trace, interventions,
    )
    journal.append("divergence_chain_recorded", target.target_id, {
        "chain": chain.canonical(), "target_id": target.target_id,
    })
    return chain


def propose_and_record_mechanisms(
    journal: ResearchJournal, target: InvestigationTarget, chain: DivergenceChain, source_role: str,
) -> MechanismCandidateSet:
    """Draft mechanism candidates from `chain`'s events and journal them, one candidate per touched role.

    Raises if `chain` has no events: an investigation with no observed
    difference has nothing for a mechanism candidate to explain.
    """
    if not chain.events:
        raise ValueError("cannot propose mechanism candidates from a divergence chain with no events")
    candidate_set = propose_mechanism_candidates(target.target_id, chain.events, source_role)
    journal.append("mechanism_candidates_proposed", target.target_id, candidate_set.canonical())
    return candidate_set


def propose_followup_experiment(journal: ResearchJournal, proposal: FollowupExperimentProposal) -> FollowupExperimentProposal:
    """Journal a proposed (not executed) intervention to discriminate one mechanism candidate.

    B0.4 stops here: no `AExecutor` call, no world fork, no result. Running
    this proposal is later work, out of this module's scope by design.
    """
    journal.append("followup_experiment_proposed", proposal.proposal_id, proposal.canonical())
    return proposal


@dataclass(frozen=True)
class DeepInvestigationOutcome:
    target: InvestigationTarget
    chain: DivergenceChain
    mechanism_candidates: MechanismCandidateSet
    followup_proposals: tuple[FollowupExperimentProposal, ...]

    def canonical(self) -> dict[str, object]:
        return {"chain": self.chain.canonical(), "followup_proposals": [x.canonical() for x in self.followup_proposals],
                "mechanism_candidates": self.mechanism_candidates.canonical(), "target": self.target.canonical()}


def investigate(
    journal: ResearchJournal, target: InvestigationTarget, trace_spec: TraceSpec,
    baseline_spec: CausalWorldSpec, contrast_spec: CausalWorldSpec, source_role: str,
    interventions: tuple[InterventionRecord, ...] = (),
) -> DeepInvestigationOutcome:
    """Run the full B0.4 pipeline: seal target -> trace both specs -> compare -> propose mechanisms.

    Does not itself draft `FollowupExperimentProposal`s -- those depend on
    which mechanism candidate a caller wants to discriminate next, so
    `followup_proposals` is empty here; use `propose_followup_experiment`
    separately once a candidate is chosen for follow-up.
    """
    seal_investigation_target(journal, target)
    chain = trace_and_compare(journal, target, trace_spec, baseline_spec, contrast_spec, interventions)
    candidates = propose_and_record_mechanisms(journal, target, chain, source_role)
    return DeepInvestigationOutcome(target, chain, candidates, ())
