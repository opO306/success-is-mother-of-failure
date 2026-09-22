"""G7.1: the B-facing half of the blind information-blocking boundary.

This module holds only what a blind B session may see: `BlindWorldDescriptor`,
`BlindControlDescriptor`, `BlindObservableDescriptor`. It does not define, import,
or re-export `BlindTranslationManifest`, `make_blind_session`,
`translate_control`, or `translate_observable` -- those live in
`blind_evaluator.py`, the evaluator-only module, and the dependency
boundary here runs one direction only: nothing in this file imports
`blind_evaluator`, so any code whose import closure bottoms out at this
module (and nothing else) cannot reach the real<->alias mapping at all,
regardless of what object graph it is handed at runtime.

    B side                                   Evaluator
    ------                                   ---------
    blind_session.py            <-------     blind_evaluator.py
      BlindWorldDescriptor                     BlindTranslationManifest
      BlindControlDescriptor                   make_blind_session()
      BlindObservableDescriptor                translate_control()
                                                translate_observable()

`blind_evaluator.py` imports from here (Blind*Descriptor are its return
shape); this module never imports back. That one-way edge is what makes
"B cannot reach the manifest" a property of the module graph, not just of
which object references happen to exist at runtime -- see
`tests/test_deterministic_blind_session.py`'s dependency-boundary tests,
which check this file's own import closure never names `blind_evaluator`,
`ground_truth`, or `synthetic_runtime`.

Why this split exists (G7.1 module-boundary repair, same day as initial
G7.1 landing): the first version of this module put `BlindWorldDescriptor`
and `BlindTranslationManifest` side by side in one file. The B-facing
object graph never carried a reference from one to the other, which is
real and was already tested -- but nothing stopped code that imports this
module from also reaching for `BlindTranslationManifest` by name, since it
lived right here. Splitting the file makes "B-facing code cannot express
the real world's identity" a fact about what this module *contains*, not
just about what any one object happens to reference.

Deliberately absent from every type below, by field, not by value:
`real_world_id`, `real_world_revision`, `ground_truth_id`, `rule`,
`fingerprint`, `source`. Adding any of those fields back defeats this
type's purpose even if every instance happened to leave them `None`.

G7.1 alias-model repair (same Gate, after the module-boundary repair):
`BlindControlDescriptor`/`BlindObservableDescriptor` carry `alias_variable_id`,
the alias of the underlying variable each names -- not a real name, but
enough for B to know that the control it manipulates and an observable it
reads are the *same* public variable, when that happens to be true. Without
this, B has no way to notice "the thing I turned and the thing I'm reading
are the same knob" and a mediator/gate structure spanning a variable that is
both a control and an observable (as GT-M1/GT-3-shaped worlds need) becomes
undiscoverable not because B reasoned poorly but because the harness never
exposed that the two aliases name one variable. This is public interface
structure, not an answer -- hiding it turns a blind causal-discovery test
into a "guess the wiring diagram, not just the physics" test, which is a
different and harder problem this project is not trying to pose. See
`blind_evaluator.py`'s `make_blind_session` for how `alias_variable_id` is
derived from the same canonical per-variable alias token a control and an
observable naming the same real variable share.
"""
from __future__ import annotations

from dataclasses import dataclass

FORMAT = "blind-session-v1"


@dataclass(frozen=True)
class BlindWorldDescriptor:
    """Everything a B-facing candidate may know about a world's shape."""
    alias_world_id: str
    variables: tuple[str, ...]
    public_controls: tuple[str, ...]
    public_observables: tuple[str, ...]
    ticks: int
    format: str = FORMAT

    def canonical(self) -> dict[str, object]:
        return {
            "alias_world_id": self.alias_world_id,
            "format": self.format,
            "public_controls": sorted(self.public_controls),
            "public_observables": sorted(self.public_observables),
            "ticks": self.ticks,
            "variables": sorted(self.variables),
        }


@dataclass(frozen=True)
class BlindControlDescriptor:
    """Names one control in alias terms, plus which alias variable it manipulates."""
    alias_control_id: str
    alias_variable_id: str

    def canonical(self) -> dict[str, object]:
        return {"alias_control_id": self.alias_control_id, "alias_variable_id": self.alias_variable_id}


@dataclass(frozen=True)
class BlindObservableDescriptor:
    """Names one observable in alias terms, plus which alias variable it reads."""
    alias_observable_id: str
    alias_variable_id: str

    def canonical(self) -> dict[str, object]:
        return {"alias_observable_id": self.alias_observable_id, "alias_variable_id": self.alias_variable_id}
