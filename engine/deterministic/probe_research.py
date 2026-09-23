"""G11c: B learns what its own probe's actions do -- explore, propose, test, refine.

    1. Explore. For every action (and direction), one program repeating it.
       Declared observation-only before running: these runs fit claims, they
       never score them.
    2. Propose. Every change B saw becomes an unconditional effect claim
       (`probe_induction.propose`).
    3. Test. Programs alternating two different actions, run one at a time.
       Before each, every claim B currently holds is sealed (`SealedClaim`):
       the whole rule is committed before the result exists.
    4. React. A claim a step contradicts is refuted on the spot (surprise:
       `anomaly_recorded`), and every claim is re-derived from all steps seen
       so far: new changes become new claims, refuted ones get conditions --
       none, then one, then ALL of two -- or are marked unexplained (a gap in
       the language). A claim that changed counts only tests run *after* the
       change.
    5. Order by curiosity, then validate everything. While claims are still
       changing, B runs next the program whose actions it knows least about:
       an action with no claim at all first (it may do something B has never
       seen, in a state B has never tried), then actions whose claims have
       passed fewest tests since they last changed. Once a full round changes
       nothing, every remaining program in the pool runs anyway (validation)
       -- measured on the first build: stopping at "a quiet round" left
       "release" never observed doing anything, and let a grasp claim keep a
       coincidental condition (the wrong neighbour's mineral, equal to the
       right one's in all data so far) marked supported after one lucky test.
    6. Severe tests (G11d, `probe_planning`). Measured in the wall world:
       a coincidental condition survived the whole pool, because no pool
       program ever reached the state that would refute it. So every claim
       that has failed somewhere gets experiments B designs itself from its
       own claims (`probe_planning`): one for sufficiency (the reachable
       state nearest a failure where the claim still predicts success) and
       one for each condition's necessity (that condition false, the rest
       true, nearest a success). Measured: sufficiency alone swapped one
       coincidence for another ("east cell has no mineral"). Then the
       final claim set is sealed.

Grammar v3 scope applies: this is about the probe's own actions in a world
whose own dynamics are still; B is told nothing about what any symbol means.

B-facing: imports B-side modules and the executor *protocol* only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .blind_probe import BlindProbeDescriptor, BlindProbeProgram, BlindProbeRun
from .blind_protocol import EVENT_OBSERVATION_ONLY_DECLARED, seal_final_discovery
from .execution import AExecutor
from .causal_experiment import PredictionSeal
from .probe_grammar import EffectClaim, Geometry, SealedClaim, Transition, claim_fits
from .probe_induction import atoms_for, propose, refine, subjects_for
from .probe_planning import design_severe_test, reachable
from .research_journal import ResearchJournal
from .sealed_execution import execute_through_a, seal_predictions

FORMAT = "probe-research-v1"
DEFAULT_ROUND = 24
DEFAULT_SEVERE_BUDGET = 200


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ClaimResult:
    claim: EffectClaim
    status: str                      # "supported" | "untested"
    fresh_tests: int

    def canonical(self) -> dict[str, object]:
        return {"claim": self.claim.canonical(), "claim_id": self.claim.claim_id, "fresh_tests": self.fresh_tests,
                "statement": self.claim.statement(), "status": self.status}


@dataclass(frozen=True)
class ProbeClaimSet:
    """The final answer, in the shape `seal_final_discovery` needs (a digest)."""
    claims: tuple[ClaimResult, ...]
    unexplained: tuple[tuple[str, str | None, str], ...]

    @property
    def digest(self) -> str:
        return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"claims": [c.canonical() for c in self.claims], "format": FORMAT,
                "unexplained": [list(u) for u in self.unexplained]}


@dataclass(frozen=True)
class ProbeResearchOutcome:
    alias_world_id: str
    final: ProbeClaimSet
    exploration_arm_ids: tuple[str, ...]
    test_arm_ids: tuple[str, ...]
    refinements: tuple[tuple[str, str], ...]        # (claim statement after, "one"/"two")
    format: str = FORMAT

    def canonical(self) -> dict[str, object]:
        return {"alias_world_id": self.alias_world_id, "exploration_arm_ids": list(self.exploration_arm_ids),
                "final": self.final.canonical(), "format": self.format,
                "refinements": [list(r) for r in self.refinements], "test_arm_ids": list(self.test_arm_ids)}


def _transitions(program: BlindProbeProgram, run: BlindProbeRun) -> list[Transition]:
    return [Transition(program.program_id, i, a, d, run.checkpoints[i], run.checkpoints[i + 1])
            for i, (a, d) in enumerate(program.steps)]


def run_probe_research(descriptor: BlindProbeDescriptor, executor: AExecutor, journal: ResearchJournal,
                       round_size: int = DEFAULT_ROUND, program_length: int | None = None,
                       severe_budget: int = DEFAULT_SEVERE_BUDGET) -> ProbeResearchOutcome:
    geometry = Geometry(descriptor.width, descriptor.height, descriptor.wraps)
    length = min(descriptor.max_program_length, program_length or descriptor.max_program_length)
    options = [(a, d) for a, takes in sorted(descriptor.actions) for d in (sorted(descriptor.directions) if takes else [None])]
    subjects = subjects_for(descriptor.channels)
    atoms = atoms_for(subjects)

    seen: list[Transition] = []
    claims: dict[tuple[str, str | None, str], EffectClaim] = {}
    fresh: dict[tuple[str, str | None, str], int] = {}
    unexplained: set[tuple[str, str | None, str]] = set()
    refinements: list[tuple[str, str]] = []

    def rederive(new_steps: list[Transition]) -> bool:
        """Every claim already fits all earlier steps (this runs after each
        batch), so only the new steps can break one or show a new change."""
        changed = False
        for key, claim in sorted(claims.items(), key=lambda kv: kv[1].claim_id):
            if all(claim_fits(claim, t, geometry) for t in new_steps):
                continue
            better, how = refine(claim, seen, atoms, geometry)
            if better is None:
                journal.append("probe_claim_unexplained", claim.claim_id, {"claim": claim.canonical()})
                unexplained.add(key)
                del claims[key]
            else:
                journal.append("probe_claim_refined", better.claim_id,
                               {"from": claim.claim_id, "how": how, "claim": better.canonical()})
                refinements.append((better.statement(), how))
                claims[key] = better
            fresh[key] = 0
            changed = True
        for claim in propose(new_steps, subjects, geometry, set(claims) | unexplained):
            key = (claim.action, claim.direction, claim.subject)
            better, how = refine(claim, seen, atoms, geometry)
            if better is None:
                journal.append("probe_claim_unexplained", claim.claim_id, {"claim": claim.canonical()})
                unexplained.add(key)
                continue
            journal.append("probe_claim_proposed", better.claim_id, {"claim": better.canonical(), "how": how})
            claims[key], fresh[key] = better, 0
            changed = True
        return changed

    # 1. Explore -- observation only.
    exploration, explored = [], []
    initial = None
    for option in options:
        program = BlindProbeProgram(descriptor.alias_world_id, tuple([option] * length))
        journal.append(EVENT_OBSERVATION_ONLY_DECLARED, program.program_id, {"reason": "explore_actions",
                                                                             "horizon": program.ticks})
        result = execute_through_a(journal, executor, program.program_id, program)
        exploration.append(program.program_id)
        if result.status == "success":
            initial = initial or result.run.checkpoints[0]
            journal.append("observation_recorded", program.program_id, {"run": result.run.canonical()})
            explored.extend(_transitions(program, result.run))
    seen.extend(explored)
    rederive(explored)

    # 2-4. Test, one sealed program at a time; react to surprise.
    pool = [BlindProbeProgram(descriptor.alias_world_id, tuple((o1 if i % 2 == 0 else o2) for i in range(length)))
            for o1 in options for o2 in options if o1 != o2]
    tested, quiet = [], 0
    remaining = list(pool)

    def curiosity(program: BlindProbeProgram) -> tuple:
        used = set(program.steps)
        unknown = sum(1 for o in used if not any((o[0], o[1]) == (k[0], k[1]) for k in claims))
        least = min([fresh[k] for k in claims if (k[0], k[1]) in used] or [0])
        return (-unknown, least)

    def run_sealed(program: BlindProbeProgram) -> bool:
        """Seal every current claim, run, compare, react. True if claims changed."""
        active = dict(claims)
        if active:
            seal_predictions(journal, PredictionSeal(f"SEAL-{program.program_id}", program.program_id,
                                                     journal.next_sequence,
                                                     {c.claim_id: (SealedClaim(c),) for c in active.values()}))
        else:
            journal.append(EVENT_OBSERVATION_ONLY_DECLARED, program.program_id, {"reason": "no_claims_yet",
                                                                                 "horizon": program.ticks})
        result = execute_through_a(journal, executor, program.program_id, program)
        tested.append(program.program_id)
        if result.status != "success":
            return False
        journal.append("observation_recorded", program.program_id, {"run": result.run.canonical()})
        steps = _transitions(program, result.run)
        if active:
            held = {c.claim_id: all(claim_fits(c, t, geometry) for t in steps) for c in active.values()}
            journal.append("result_compared", program.program_id, {"held": held})
            used = {(t.action, t.direction) for t in steps}
            for key, claim in active.items():
                if not held[claim.claim_id]:
                    journal.append("anomaly_recorded", claim.claim_id,
                                   {"arm_id": program.program_id, "kind": "claim_contradicted"})
                elif (claim.action, claim.direction) in used and claims.get(key) == claim:
                    fresh[key] += 1
        seen.extend(steps)
        return rederive(steps)

    while remaining:
        if quiet < round_size:            # discovery: most curious first
            program = min(remaining, key=lambda p: (curiosity(p), remaining.index(p)))
        else:                             # validation: everything left, in order
            program = remaining[0]
        remaining.remove(program)
        quiet = 0 if run_sealed(program) else quiet + 1

    # 6. Severe tests (G11d): every claim that has failed somewhere gets
    # experiments B designs itself -- sufficiency, then each condition's
    # necessity. A claim refined by a result is a new claim and gets its own.
    if initial is not None:
        survived: set[tuple] = set()
        models: dict[frozenset, list] = {}
        run_ids = set(tested)
        for _ in range(severe_budget):
            pending = [(c, kind) for c in sorted(claims.values(), key=lambda c: c.claim_id) if c.conditions
                       for kind in (None,) + c.conditions if (c.claim_id, kind) not in survived]
            if not pending:
                break
            claim, dropped = pending[0]
            model_key = frozenset(c.claim_id for c in claims.values())
            if model_key not in models:
                models.clear()
                models[model_key] = reachable(list(claims.values()), initial, options, subjects, geometry)
            plan = design_severe_test(claim, models[model_key], seen, subjects, geometry, length, dropped)
            program = None if plan is None else BlindProbeProgram(descriptor.alias_world_id, plan.steps)
            if program is None or program.program_id in run_ids:
                survived.add((claim.claim_id, dropped))   # nothing new to try: keep what the pool showed
                continue
            journal.append("probe_test_designed", program.program_id,
                           {"claim_id": claim.claim_id, "kind": "sufficiency" if dropped is None else "necessity",
                            "condition": None if dropped is None else dropped.text(),
                            "planned_distance": plan.distance, "steps": [list(s) for s in plan.steps]})
            run_ids.add(program.program_id)
            run_sealed(program)
            if claim in claims.values():
                survived.add((claim.claim_id, dropped))

    results = tuple(ClaimResult(c, "supported" if fresh[k] >= 1 else "untested", fresh[k])
                    for k, c in sorted(claims.items(), key=lambda kv: kv[1].claim_id))
    final = ProbeClaimSet(results, tuple(sorted(unexplained, key=lambda u: (u[0], u[1] or "", u[2]))))
    seal_final_discovery(journal, descriptor.alias_world_id, final,
                         tuple(r.claim.claim_id for r in results if r.status != "supported"))
    return ProbeResearchOutcome(descriptor.alias_world_id, final, tuple(exploration), tuple(tested),
                                tuple(refinements))
