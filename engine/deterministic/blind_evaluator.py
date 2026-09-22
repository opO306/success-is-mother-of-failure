"""G7.1: the evaluator-only half of the blind information-blocking boundary.

Everything here can see a real `SyntheticWorldSpec`'s identity and produce
the real<->alias mapping that identity is hidden behind. Nothing in this
module is B-facing -- no B-side call path is meant to import this module at
all, and `tests/test_deterministic_blind_session.py`'s dependency-boundary
tests check that `blind_session.py` (the B-facing module) never does.

`make_blind_session(spec, seed)` is the only function that ever holds both
a real spec and a `BlindTranslationManifest` in scope at once. It returns
them as two independent values -- a `BlindWorldDescriptor` (from
`blind_session.py`) and a `BlindTranslationManifest` (defined here) --
never bundled into one object a caller could hand to B-side code as a
single argument.

Alias generation is deterministic from `(spec.digest, seed)` only -- no
wall-clock, no process-global counters -- so the same real spec and seed
always produce the same aliasing
(`test_make_blind_session_is_deterministic`), and a different seed
produces a different permutation
(`test_make_blind_session_seed_changes_permutation`). 3-permutation
robustness across a full alias set (G7.6) is out of scope here; this
module only guarantees the mapping itself is seed-reproducible.

Why this is a separate module from `synthetic_spec.py`: `SyntheticWorldSpec`
already withholds unobserved variable *values* (see its own docstring's
threat model), but it is still the real spec -- its `world_id`/
`world_revision` identify the real world directly, and nothing stopped a
caller from handing that whole object to B. This module's job is narrower:
translate between that real spec and the alias-only shapes in
`blind_session.py`, and never let that translation surface be reachable
from B-facing code.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .blind_session import BlindWorldDescriptor
from .synthetic_spec import SyntheticWorldSpec


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
class BlindTranslationManifest:
    """Evaluator-only: the real<->alias mapping for one blind session.

    Never passed to, stored on, or reachable from any B-facing object.
    `make_blind_session` returns this as an independent value alongside a
    `BlindWorldDescriptor` -- callers on the B side must not be given both,
    and this type is not defined in `blind_session.py`, so importing that
    module alone cannot bring this type along with it.
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
    """The only function that sees both a real spec and the manifest that
    can unmask it. Returns them as two independent values, never bundled
    into one object a B-facing caller could hold."""
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
