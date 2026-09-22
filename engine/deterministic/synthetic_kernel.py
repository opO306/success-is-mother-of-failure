"""G6c-2/G6c-3.1: the hidden, opaque one-tick rules that actually govern a synthetic world.

Each rule function is a private, from-scratch implementation -- it does not
import or call anything from `ground_truth/`. Any resemblance between a rule
here and `ground_truth/world2_direct.py`/`world3_conditional.py`/
`gt_m1_mediator.py` is intentional at the level of "this world is meant to
have the same causal structure as that answer key" and nowhere else: the
Python code itself is written twice, independently, so that a bug in one
cannot silently also be a bug in the other (see `synthetic_spec.py`'s
docstring and CURRENT_STATE.md's "hidden mediator" circularity).

`RULE_S01`/`RULE_S02`/`RULE_S03` are exported so `synthetic_runtime.py` can
bind them to a `(world_id, world_revision)` pair -- this module has no
opinion on which world a rule belongs to, or which rule a spec should run;
see `synthetic_runtime.py` for that binding, and `synthetic_executor.py`
for the only caller allowed to resolve it. Variable names (`x1`/`x2`/`x3`)
are deliberately anonymous.

`run_synthetic_world` takes the rule function directly (not a spec-embedded
id) and returns a `SyntheticRun` whose checkpoints hold only
`public_observables` -- a private variable a rule computes internally (say,
an intermediate `x2` a world does not declare observable) never reaches the
run B's adapter reads, closing the gap where `public_observables` used to
gate only `initial_observation`'s tick-0 payload while every later tick's
full internal state was reachable through any `ObservablePrediction` naming
it by string.
"""
from __future__ import annotations

from typing import Callable, Mapping

from .synthetic_spec import SyntheticCheckpoint, SyntheticRun, SyntheticWorldSpec

SyntheticRule = Callable[[Mapping[str, bool]], Mapping[str, bool]]


def RULE_S01(values: Mapping[str, bool]) -> Mapping[str, bool]:
    """x3 copies x1. No third variable is read or written."""
    return {"x1": values["x1"], "x3": values["x1"]}


def RULE_S02(values: Mapping[str, bool]) -> Mapping[str, bool]:
    """x3 is x1 AND x2."""
    return {"x1": values["x1"], "x2": values["x2"], "x3": values["x1"] and values["x2"]}


def RULE_S03(values: Mapping[str, bool]) -> Mapping[str, bool]:
    """Ordinary evolution: x2 follows x1, x3 follows x2.

    Clamping is handled by `run_synthetic_world`, outside this function --
    this rule only ever computes what would happen with no intervention at
    all. A clamp on x2 is reapplied by the caller after this runs, which is
    what lets x3 still follow the *clamped* x2 rather than the one this
    function would have produced unclamped.
    """
    return {"x1": values["x1"], "x2": values["x1"], "x3": values["x2"]}


def _apply_clamps(spec: SyntheticWorldSpec, values: Mapping[str, bool]) -> dict[str, bool]:
    result = dict(values)
    for control in spec.public_controls:
        mode = spec.clamp_for(control)
        if mode == "ON":
            result[control] = True
        elif mode == "OFF":
            result[control] = False
    return result


def _public_checkpoint(spec: SyntheticWorldSpec, tick: int, values: Mapping[str, bool]) -> SyntheticCheckpoint:
    """Only `public_observables` survive into a checkpoint B can ever read.

    A variable a rule computes but the spec does not declare observable
    (an internal-only intermediate, say) is discarded here -- not merely
    absent from `initial_observation`'s tick-0 payload the way an earlier
    draft left it, but genuinely unrecoverable from any later tick's
    checkpoint either, closing the "read a private variable by naming it in
    an ObservablePrediction" gap.
    """
    return SyntheticCheckpoint(tick, tuple(sorted((k, v) for k, v in values.items()
                                                  if k in spec.public_observables)))


def run_synthetic_world(spec: SyntheticWorldSpec, rule: SyntheticRule) -> SyntheticRun:
    """The plain A-loop for a synthetic world: apply clamps, record tick 0,
    then step the hidden rule and reapply clamps once per remaining tick.

    `rule` is resolved by the caller (`synthetic_executor.py`, via
    `synthetic_runtime.resolve_rule`) -- this function has no registry of
    its own and does not know or care which world a rule "belongs to".

    Clamps apply every tick, not just the initial one -- a `SyntheticClamp`
    is a standing intervention for the whole run (`synthetic_spec.py`'s
    docstring), the same way `PortBond`/heat interventions in the physical
    A0 world persist across ticks rather than being consumed once.
    """
    values = _apply_clamps(spec, dict(spec.initial_values))
    checkpoints = [_public_checkpoint(spec, 0, values)]
    for tick in range(1, spec.ticks + 1):
        values = _apply_clamps(spec, dict(rule(values)))
        checkpoints.append(_public_checkpoint(spec, tick, values))

    return SyntheticRun(spec.world_id, spec.digest, tuple(checkpoints))
