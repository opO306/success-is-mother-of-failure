"""G8: B notices a regularity in what it has already seen, after being surprised.

Until G8, B's hypotheses were a closed menu built once, before any
experiment; a surprise ("every hypothesis I hold was just contradicted")
could only end a question as NO_SURVIVOR. Here a surprise instead triggers
B to look back over its own recorded observations, with no hypothesis in
hand, for one kind of regularity:

    "the target follows a pinnable variable k ticks later" (k >= 2)

(k = 1 is already an enumerated DIRECT claim.) A pattern qualifies only if,
across every recorded run where the target was left free:

  * before tick k the target keeps its initial value, and from tick k on it
    equals the source's value k ticks earlier -- no exception; and
  * at least one run shows the target actually *changing* and the pattern
    explaining it (a pattern that only ever predicts "stays the same" says
    nothing a NO_EFFECT claim would not).

A noticed pattern becomes a DELAYED claim and joins the question's live
hypotheses -- but it was fitted to the data it came from, so that data is
*not* evidence for it. It is only ever tested by experiments run after it
was noticed (the loop seals it like any other hypothesis from then on). If
no experiment remains to test it, it stays a proposal, never an answer.

What this cannot do, stated plainly: the detector itself already knows the
concept "follows k ticks later" -- a person wrote that search. B finds *which*
variable, *which* lag and *whether*, from data; it does not invent the
concept of delay. Inverted delays ("target is the opposite of the source k
ticks earlier") are not searched: grammar v2 has no word for them.

B-facing: imports only B-side modules (checked transitively by tests).
"""
from __future__ import annotations

from typing import Mapping, Sequence

from .blind_execution import BlindRun
from .blind_hypothesis import DELAYED, BlindCausalClaim
from .blind_hypothesis_generator import BlindQuestion
from .blind_session import BlindControlDescriptor, BlindObservableDescriptor, BlindWorldDescriptor


def notice_delayed_relations(
    question: BlindQuestion,
    world: BlindWorldDescriptor,
    controls: tuple[BlindControlDescriptor, ...],
    observables: tuple[BlindObservableDescriptor, ...],
    observations: Sequence[tuple[Mapping[str, bool], BlindRun]],
) -> tuple[BlindCausalClaim, ...]:
    """Every DELAYED claim about `question`'s target that fits all of
    `observations` (pinned variables -> the run observed under them), and
    is not already one of the question's claims. Deterministic order: by
    source variable, then lag."""
    target_var, target_obs = question.target_variable_id, question.target_observable_id
    observable_of = {o.alias_variable_id: o.alias_observable_id for o in observables}
    sources = sorted(c.alias_variable_id for c in controls if c.alias_variable_id != target_var)
    known = {claim.claim_id for claim in question.claims}

    def value(variable: str, pinned: Mapping[str, bool], run: BlindRun, tick: int) -> bool | None:
        if variable in pinned:
            return pinned[variable]
        observable = observable_of.get(variable)
        checkpoint = run.checkpoint_at(tick)
        return checkpoint.value_of(observable) if observable and checkpoint else None

    found: list[BlindCausalClaim] = []
    for source in sources:
        for lag in range(2, world.ticks + 1):
            consistent, explains_change = True, False
            for pinned, run in observations:
                if target_var in pinned:
                    continue
                start = value(target_var, pinned, run, 0)
                for checkpoint in run.checkpoints:
                    seen = checkpoint.value_of(target_obs)
                    if checkpoint.tick < lag:
                        expected = start
                    else:
                        expected = value(source, pinned, run, checkpoint.tick - lag)
                        if expected is None:
                            continue
                        if seen != start:
                            explains_change = True
                    if seen != expected:
                        consistent = False
                        break
                if not consistent:
                    break
            if consistent and explains_change:
                claim = BlindCausalClaim(DELAYED, target_var, (source,), lag=lag)
                if claim.claim_id not in known:
                    found.append(claim)
    return tuple(found)
