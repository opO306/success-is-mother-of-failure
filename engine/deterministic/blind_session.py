"""G7.1: the information-blocking boundary between a real `SyntheticWorldSpec`
and whatever B is allowed to see of it.

This module does NOT implement discovery, scoring, or held-out evaluation --
see `CURRENT_STATE.md`'s G7.1 scope note. It implements exactly one thing:
a B-facing object graph that cannot express the real world's identity, and
an evaluator-only manifest that can, kept apart so B-side code never even
receives the manifest as an argument.

Two object graphs, never merged:

    Evaluator side                          B (blind) side
    ---------------                         --------------
    real SyntheticWorldSpec                 BlindWorldDescriptor
    BlindTranslationManifest    -- alias -->   .alias_world_id
      .real_world_id                           .variables (aliased)
      .real_world_revision                     .public_controls (aliased)
      .variable_alias / .real_variable          .public_observables (aliased)
      .control_alias / .real_control            .ticks
      .observable_alias / .real_observable

`make_blind_session(spec, seed)` is the only function that ever holds both a
real spec and a manifest in scope at once, and it returns them as two
separate values -- never as fields of one object a B-facing function could
receive. Every B-facing function in this module takes a
`BlindWorldDescriptor` (or another Blind* type) and nothing that could ever
resolve back to `manifest.real_world_id` etc. `BlindTranslationManifest`
itself is applied only on the evaluator side, via `translate_control`/
`translate_observable`/`resolve_real_spec`, which are not part of any
B-facing call path.

Why this is a separate module from `synthetic_spec.py`: `SyntheticWorldSpec`
already withholds unobserved variable *values* (see its own docstring's
threat model), but it is still the real spec -- its `world_id`/
`world_revision` identify the real world directly, and nothing stopped a
caller from handing that whole object to B. This module's job is narrower:
make it structurally impossible for a B-facing object to carry
`real_world_id`/`real_world_revision`/`ground_truth_id`/`rule`/`fingerprint`/
`source` at all, not just discourage reading them.

Alias generation is deterministic from `(spec.digest, seed)` only -- no
wall-clock, no process-global counters -- so the same real spec and seed
always produce the same aliasing (`test_make_blind_session_is_deterministic`),
and a different seed produces a different permutation
(`test_make_blind_session_seed_changes_permutation`). 3-permutation
robustness across a full alias set (G7.6) is out of scope here; this module
only guarantees the mapping itself is seed-reproducible.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .synthetic_spec import SyntheticWorldSpec

FORMAT = "blind-session-v1"


class ForbiddenBlindAccess(Exception):
    """Raised when B-side code reaches for an evaluator-only accessor.

    Production code never raises this on its own -- it exists so a test can
    monkeypatch a manifest accessor to raise it, run the blind path, and
    confirm zero trips; and separately monkeypatch it to confirm a
    deliberately-forbidden path does trip. See
    `tests/test_deterministic_blind_session.py`'s runtime tripwire tests.
    """


def _alias_token(spec_digest: str, seed: int, kind: str, real_name: str) -> str:
    raw = f"{spec_digest}:{seed}:{kind}:{real_name}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:8].upper()
    return f"ALIAS-{digest}"


@dataclass(frozen=True)
class BlindWorldDescriptor:
    """Everything a B-facing candidate may know about a world's shape.

    Deliberately absent, by field, not by value: `real_world_id`,
    `real_world_revision`, `ground_truth_id`, `rule`, `fingerprint`,
    `source`. Adding any of those fields back defeats this type's purpose
    even if every instance happened to leave them `None`.
    """
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
    """Names one control in alias terms only."""
    alias_control_id: str

    def canonical(self) -> dict[str, object]:
        return {"alias_control_id": self.alias_control_id}


@dataclass(frozen=True)
class BlindObservableDescriptor:
    """Names one observable in alias terms only."""
    alias_observable_id: str

    def canonical(self) -> dict[str, object]:
        return {"alias_observable_id": self.alias_observable_id}


@dataclass(frozen=True)
class BlindTranslationManifest:
    """Evaluator-only: the real<->alias mapping for one blind session.

    Never passed to, stored on, or reachable from any B-facing object.
    `make_blind_session` returns this as an independent value alongside a
    `BlindWorldDescriptor` -- callers on the B side must not be given both.
    """
    real_world_id: str
    real_world_revision: str
    alias_world_id: str
    variable_alias: Mapping[str, str]
    control_alias: Mapping[str, str]
    observable_alias: Mapping[str, str]
    seed: int

    def __post_init__(self) -> None:
        if not self.real_world_id or not self.real_world_id.strip():
            raise ValueError("real_world_id must be non-empty")
        if not self.real_world_revision or not self.real_world_revision.strip():
            raise ValueError("real_world_revision must be non-empty")

    @property
    def real_variable(self) -> Mapping[str, str]:
        return {alias: real for real, alias in self.variable_alias.items()}

    @property
    def real_control(self) -> Mapping[str, str]:
        return {alias: real for real, alias in self.control_alias.items()}

    @property
    def real_observable(self) -> Mapping[str, str]:
        return {alias: real for real, alias in self.observable_alias.items()}


def make_blind_session(spec: SyntheticWorldSpec, seed: int) -> tuple[BlindWorldDescriptor, BlindTranslationManifest]:
    """The only function in this module that sees both a real spec and the
    manifest that can unmask it. Returns them as two independent values,
    never bundled into one object a B-facing caller could hold."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    variable_alias = {name: _alias_token(spec.digest, seed, "variable", name)
                      for name in spec.variables}
    control_alias = {name: _alias_token(spec.digest, seed, "control", name)
                     for name in spec.public_controls}
    observable_alias = {name: _alias_token(spec.digest, seed, "observable", name)
                        for name in spec.public_observables}
    alias_world_id = _alias_token(spec.digest, seed, "world", spec.world_id)

    descriptor = BlindWorldDescriptor(
        alias_world_id=alias_world_id,
        variables=tuple(sorted(variable_alias.values())),
        public_controls=tuple(sorted(control_alias.values())),
        public_observables=tuple(sorted(observable_alias.values())),
        ticks=spec.ticks,
    )
    manifest = BlindTranslationManifest(
        real_world_id=spec.world_id,
        real_world_revision=spec.world_revision,
        alias_world_id=alias_world_id,
        variable_alias=variable_alias,
        control_alias=control_alias,
        observable_alias=observable_alias,
        seed=seed,
    )
    return descriptor, manifest


# ---------------------------------------------------------------------------
# Evaluator-only translation surface. Not part of any B-facing call path --
# nothing in this module's B-facing functions (above) calls these, and no
# B-facing type carries a `BlindTranslationManifest` field for these to be
# reached through.
# ---------------------------------------------------------------------------

def translate_control(manifest: BlindTranslationManifest, alias_control_id: str) -> str:
    try:
        return manifest.real_control[alias_control_id]
    except KeyError:
        raise ForbiddenBlindAccess(f"no real control bound to alias {alias_control_id!r}") from None


def translate_observable(manifest: BlindTranslationManifest, alias_observable_id: str) -> str:
    try:
        return manifest.real_observable[alias_observable_id]
    except KeyError:
        raise ForbiddenBlindAccess(f"no real observable bound to alias {alias_observable_id!r}") from None
