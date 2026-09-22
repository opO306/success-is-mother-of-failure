"""B0.6 orchestrator: read B0.4/B0.5 journal evidence, propose CausalEdges, validate, register, build paths.

Two entry points, one gate:

- `build_from_evidence` is the default, automatic path (per the confirmed
  design decision): given a `causal_timeline.AtomicChangeGroup` sequence (the
  real, deduplicated, observation-order timeline built from a trace -- never
  a `MechanismCandidate.path` walked directly, since that path repeats a
  (role, field) once per observation it was sampled at and cannot serve as a
  causal sequence on its own) and the set of roles a `MechanismCandidate`
  with `SUPPORTS` evidence actually concerns, it proposes one edge candidate
  per pair of consecutive *distinct* groups that touch a supported role.
- `evaluate_requested_relation` lets a caller name two specific nodes to
  examine -- it does not create an edge, only escalates the pair to
  `validate_relation`.

Both call `causal_edge_validator.validate_relation` before anything is
registered; neither can bypass it. Every registered edge/path is journaled
append-only and rebuildable by replay, exactly like B0.1-B0.5.

`MechanismCandidate`s from B0.4 are used only as *evidence locators* here --
which roles were implicated, and with what `MechanismEvidence` -- never as a
pre-built path to walk.
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from .causal_edge import CausalEdge, CausalPath, MissingLink, derive_edge_status, path_status
from .causal_edge_validator import validate_relation
from .causal_graph_model import AtomicPhaseEvent, CausalCondition, CausalNode, PathEvidenceBundle
from .causal_timeline import AtomicChangeGroup
from .mechanism_candidate import MechanismCandidateSet
from .mechanism_test import MechanismEvidence
from .research_domain import ResearchDomain
from .research_journal import ResearchJournal, read_journal


def register_atomic_phase_event(journal: ResearchJournal, event: AtomicPhaseEvent) -> AtomicPhaseEvent:
    journal.append("atomic_event_recorded", event.event_id, event.canonical())
    return event


def propose_causal_edge(
    journal: ResearchJournal,
    source: CausalNode, target: CausalNode,
    source_domain: ResearchDomain, target_domain: ResearchDomain,
    same_atomic_event: bool,
    observation_evidence_ids: tuple[str, ...], intervention_evidence_ids: tuple[str, ...],
    contradiction_evidence_ids: tuple[str, ...] = (),
    condition=None,
    independent_supporting_domain_count: int = 1,
) -> CausalEdge | None:
    """Validate one source -> target relation and, if legal, register it with a derived status.

    Returns `None` (and journals nothing but the rejection) when
    `validate_relation` rejects the pair -- an edge is never force-created.
    """
    has_evidence = bool(observation_evidence_ids) or bool(intervention_evidence_ids)
    rejection = validate_relation(source, target, source_domain, target_domain, same_atomic_event, has_evidence)
    if rejection is not None:
        journal.append("causal_edge_rejected", f"{source.node_id}-{target.node_id}", {
            "reason": rejection.reason, "source_node_id": source.node_id, "target_node_id": target.node_id,
        })
        return None

    evidence = PathEvidenceBundle(observation_evidence_ids, intervention_evidence_ids, contradiction_evidence_ids)
    status = derive_edge_status(bool(observation_evidence_ids), bool(intervention_evidence_ids),
                                bool(contradiction_evidence_ids), independent_supporting_domain_count)
    edge_id = f"EDGE-{source.node_id}-{target.node_id}"
    edge = CausalEdge(edge_id, source.node_id, target.node_id, condition, evidence, status)
    journal.append("causal_edge_proposed", edge.edge_id, edge.canonical())
    return edge


def strengthen_edge_with_contradiction(
    journal: ResearchJournal, edge: CausalEdge, contradiction_evidence_id: str,
    independent_supporting_domain_count: int = 1,
) -> CausalEdge:
    """Add a contradicting evidence id to an existing edge. Never deletes prior support (docs/README section 12)."""
    new_evidence = replace(edge.evidence,
                           contradiction_evidence_ids=tuple(sorted(set(edge.evidence.contradiction_evidence_ids)
                                                                  | {contradiction_evidence_id})))
    new_status = derive_edge_status(bool(new_evidence.observation_evidence_ids),
                                    bool(new_evidence.intervention_evidence_ids),
                                    bool(new_evidence.contradiction_evidence_ids),
                                    independent_supporting_domain_count)
    updated = replace(edge, evidence=new_evidence, status=new_status)
    journal.append("causal_edge_updated", updated.edge_id, updated.canonical())
    return updated


def register_missing_link(journal: ResearchJournal, link: MissingLink) -> MissingLink:
    journal.append("missing_link_recorded", f"{link.source_node_id}-{link.target_node_id}", link.canonical())
    return link


def register_causal_path(journal: ResearchJournal, path: CausalPath) -> CausalPath:
    journal.append("causal_path_created", path.path_id, path.canonical())
    return path


def _node_for_change(role: str, field: str, domain_id: str) -> CausalNode:
    return CausalNode("state", role, field, domain_id)


def build_from_evidence(
    journal: ResearchJournal, path_id: str, timeline: tuple[AtomicChangeGroup, ...],
    candidate_set: MechanismCandidateSet, evidence: tuple[MechanismEvidence, ...],
    domain: ResearchDomain,
) -> CausalPath | None:
    """Automatically propose and register edges/atomic events/a path from a real cross-role timeline.

    `timeline` must already be a deduplicated, `observation_seq`-ordered
    sequence of `AtomicChangeGroup`s (`causal_timeline.build_cross_role_timeline`
    applied to `causal_timeline.extract_state_changes` -- never a raw trace
    and never any `MechanismCandidate.path`). Only (role, field) pairs
    belonging to a role some `SUPPORTS`-evidenced mechanism candidate
    concerns are used to build edges; roles only implicated by a
    `CONTRADICTS`/`INCONCLUSIVE` candidate contribute nothing (a rejected
    mechanism is not silently reused for a different one).

    Changes within one `AtomicChangeGroup` never become an edge with each
    other -- they are recorded as siblings of one `AtomicPhaseEvent`
    (docs/README sections 4/16/17: a shared instant is not a sequence).
    Only pairs of *distinct* groups may become an edge, in the timeline's
    observed order.

    Returns `None` if no candidate in `candidate_set` has supporting
    evidence, or if the supported roles never appear in `timeline` -- an
    inconclusive or unrelated investigation legitimately produces no path.
    """
    supported_ids = {item.mechanism_candidate_id for item in evidence if item.relation == "SUPPORTS"}
    # A candidate's `source_role` names the investigation's starting point,
    # not what this particular candidate is about -- `propose_mechanism_candidates`
    # builds one candidate per role its `path` steps actually touch, so that
    # role set (every step's `.role`, always uniform within one candidate) is
    # what determines which timeline changes this SUPPORTS verdict covers.
    supported_roles = {step.role for c in candidate_set.candidates if c.candidate_id in supported_ids
                       for step in c.path}
    if not supported_roles:
        return None

    relevant_groups = [group for group in timeline
                      if any(c.role in supported_roles for c in group.changes)]
    if len(relevant_groups) < 2:
        return None

    supporting_evidence = tuple(sorted(supported_ids))
    edges: list[CausalEdge] = []
    missing_links: list[MissingLink] = []

    for earlier, later in zip(relevant_groups, relevant_groups[1:]):
        event = AtomicPhaseEvent(earlier.observation_seq, earlier.tick, earlier.phase,
                                 tuple(sorted({_node_for_change(c.role, c.field, domain.domain_id).node_id
                                              for c in earlier.changes})))
        register_atomic_phase_event(journal, event)

        for left_change in earlier.changes:
            if left_change.role not in supported_roles:
                continue
            left_node = _node_for_change(left_change.role, left_change.field, domain.domain_id)
            for right_change in later.changes:
                if right_change.role not in supported_roles:
                    continue
                right_node = _node_for_change(right_change.role, right_change.field, domain.domain_id)
                edge = propose_causal_edge(
                    journal, left_node, right_node, domain, domain, False,
                    (f"seq-{earlier.observation_seq}-{later.observation_seq}",), supporting_evidence,
                )
                if edge is not None:
                    edges.append(edge)
                else:
                    missing_links.append(MissingLink(
                        left_node.node_id, right_node.node_id,
                        "relation failed validation; see causal_edge_rejected in journal"))

    # The final group's changes get one AtomicPhaseEvent too, for completeness.
    last = relevant_groups[-1]
    register_atomic_phase_event(journal, AtomicPhaseEvent(
        last.observation_seq, last.tick, last.phase,
        tuple(sorted({_node_for_change(c.role, c.field, domain.domain_id).node_id for c in last.changes})),
    ))

    if not edges and not missing_links:
        return None
    for link in missing_links:
        register_missing_link(journal, link)
    status = path_status(tuple(e.status for e in edges)) if edges else "UNRESOLVED"
    path = CausalPath(path_id, tuple(sorted({e.edge_id for e in edges})), tuple(missing_links), status)
    return register_causal_path(journal, path)


def evaluate_requested_relation(
    journal: ResearchJournal, source: CausalNode, target: CausalNode,
    source_domain: ResearchDomain, target_domain: ResearchDomain,
    same_atomic_event: bool,
    observation_evidence_ids: tuple[str, ...], intervention_evidence_ids: tuple[str, ...],
) -> CausalEdge | None:
    """A caller-requested relation to examine. Goes through the same `validate_relation` gate as automatic discovery.

    Naming a relation here never elevates it above what the evidence
    supports -- it only asks B0.6 to check it, exactly as
    `build_from_evidence` would for any candidate it discovered on its own.
    """
    return propose_causal_edge(journal, source, target, source_domain, target_domain, same_atomic_event,
                               observation_evidence_ids, intervention_evidence_ids)


def rebuild_causal_graph(path: Path) -> dict[str, object]:
    """Replay the journal into edges/paths/atomic events/missing links. Always rebuildable, never authoritative."""
    edges: dict[str, CausalEdge] = {}
    paths: dict[str, CausalPath] = {}
    atomic_events: dict[str, dict[str, object]] = {}
    missing_links: dict[tuple[str, str], MissingLink] = {}
    for entry in read_journal(path):
        if entry.event_type == "causal_edge_proposed" or entry.event_type == "causal_edge_updated":
            payload = entry.payload
            raw_condition = payload.get("condition")
            condition = (CausalCondition(raw_condition["condition_id"], raw_condition["expression"],
                                        tuple(raw_condition["axis_ids"])) if raw_condition is not None else None)
            bundle = PathEvidenceBundle(tuple(payload["evidence"]["observation_evidence_ids"]),
                                        tuple(payload["evidence"]["intervention_evidence_ids"]),
                                        tuple(payload["evidence"]["contradiction_evidence_ids"]))
            edges[payload["edge_id"]] = CausalEdge(payload["edge_id"], payload["source_node_id"],
                                                   payload["target_node_id"], condition, bundle, payload["status"])
        elif entry.event_type == "causal_path_created":
            payload = entry.payload
            links = tuple(MissingLink(x["source_node_id"], x["target_node_id"], x["reason"])
                         for x in payload["missing_links"])
            paths[payload["path_id"]] = CausalPath(payload["path_id"], tuple(payload["edge_ids"]), links,
                                                   payload["status"])
        elif entry.event_type == "atomic_event_recorded":
            payload = entry.payload
            atomic_events[entry.record_id] = payload
        elif entry.event_type == "missing_link_recorded":
            payload = entry.payload
            missing_links[(payload["source_node_id"], payload["target_node_id"])] = MissingLink(
                payload["source_node_id"], payload["target_node_id"], payload["reason"])
    return {"atomic_events": atomic_events, "edges": edges, "missing_links": missing_links, "paths": paths}
