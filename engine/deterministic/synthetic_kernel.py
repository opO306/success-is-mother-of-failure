"""G6c-2: the hidden, opaque one-tick rules that actually govern a synthetic world.

Each rule function is a private, from-scratch implementation -- it does not
import or call anything from `ground_truth/`. Any resemblance between a rule
here and `ground_truth/world2_direct.py`/`world3_conditional.py`/
`gt_m1_mediator.py` is intentional at the level of "this world is meant to
have the same causal structure as that answer key" and nowhere else: the
Python code itself is written twice, independently, so that a bug in one
cannot silently also be a bug in the other (see `synthetic_spec.py`'s
docstring and CURRENT_STATE.md's "hidden mediator" circularity).

Rule ids (`RULE-S01`/`RULE-S02`/`RULE-S03`) and variable names (`x1`/`x2`/`x3`)
are deliberately anonymous. A `SyntheticWorldSpec`'s `rule_id` selects which
function below governs it; nothing about the id or a variable's name
implies what the rule actually does.
"""
from __future__ import annotations

from typing import Callable, Mapping

from .research_world import WorldCompatibilityError
from .synthetic_spec import SyntheticCheckpoint, SyntheticRun, SyntheticWorldSpec


def _rule_s01(values: Mapping[str, bool]) -> Mapping[str, bool]:
    """x3 copies x1. No third variable is read or written."""
    return {"x1": values["x1"], "x3": values["x1"]}


def _rule_s02(values: Mapping[str, bool]) -> Mapping[str, bool]:
    """x3 is x1 AND x2."""
    return {"x1": values["x1"], "x2": values["x2"], "x3": values["x1"] and values["x2"]}


def _rule_s03(values: Mapping[str, bool]) -> Mapping[str, bool]:
    """Ordinary evolution: x2 follows x1, x3 follows x2.

    Clamping is handled by `run_synthetic_world`, outside this function --
    this rule only ever computes what would happen with no intervention at
    all. A clamp on x2 is reapplied by the caller after this runs, which is
    what lets x3 still follow the *clamped* x2 rather than the one this
    function would have produced unclamped.
    """
    return {"x1": values["x1"], "x2": values["x1"], "x3": values["x2"]}


_RULES: Mapping[str, Callable[[Mapping[str, bool]], Mapping[str, bool]]] = {
    "RULE-S01": _rule_s01,
    "RULE-S02": _rule_s02,
    "RULE-S03": _rule_s03,
}


def _apply_clamps(spec: SyntheticWorldSpec, values: Mapping[str, bool]) -> dict[str, bool]:
    result = dict(values)
    for control in spec.public_controls:
        mode = spec.clamp_for(control)
        if mode == "ON":
            result[control] = True
        elif mode == "OFF":
            result[control] = False
    return result


def _checkpoint(tick: int, values: Mapping[str, bool]) -> SyntheticCheckpoint:
    return SyntheticCheckpoint(tick, tuple(sorted(values.items())))


def run_synthetic_world(spec: SyntheticWorldSpec) -> SyntheticRun:
    """The plain A-loop for a synthetic world: apply clamps, record tick 0,
    then step the hidden rule and reapply clamps once per remaining tick.

    Clamps apply every tick, not just the initial one -- a `SyntheticClamp`
    is a standing intervention for the whole run (`synthetic_spec.py`'s
    docstring), the same way `PortBond`/heat interventions in the physical
    A0 world persist across ticks rather than being consumed once.
    """
    try:
        rule = _RULES[spec.rule_id]
    except KeyError:
        raise WorldCompatibilityError(f"no synthetic rule registered for rule_id {spec.rule_id!r}") from None

    values = _apply_clamps(spec, dict(spec.initial_values))
    checkpoints = [_checkpoint(0, values)]
    for tick in range(1, spec.ticks + 1):
        values = _apply_clamps(spec, dict(rule(values)))
        checkpoints.append(_checkpoint(tick, values))

    return SyntheticRun(spec.world_id, spec.digest, tuple(checkpoints))
