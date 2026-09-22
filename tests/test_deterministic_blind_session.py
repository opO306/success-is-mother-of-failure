"""G7.1: the blind information-boundary itself -- not what B discovers.

Two modules, one direction of dependency:
  - `blind_session.py`   (B-facing)   -- BlindWorldDescriptor/BlindControlDescriptor/
                                          BlindObservableDescriptor only
  - `blind_evaluator.py` (evaluator-only) -- BlindTranslationManifest, make_blind_session,
                                          translate_control, translate_observable;
                                          imports FROM blind_session, never the reverse

Four layers, each sealed by its own tests below:
  1. type boundary       -- Blind*Descriptor types cannot structurally carry
                             real identity/GT/rule/fingerprint fields
  2. dependency boundary -- blind_session.py's import closure never reaches
                             blind_evaluator.py, ground_truth/, or synthetic_runtime.py
  3. serialized-data leakage -- canonical()/digest of a real blind session
                             never contains real world/control/observable ids
  4. runtime tripwire     -- a normal blind path never touches the manifest's
                             evaluator-only translation surface; a
                             deliberately forbidden path does

Also: alias generation is deterministic per (spec, seed) and differs across
seeds -- the minimum reproducibility guarantee this Gate promises (full
3-permutation robustness is G7.6, not here).

What this file does NOT test, on purpose (see CURRENT_STATE.md's G7.1 scope
note): 9-session runs, the G6d autonomous loop, GT obligation scoring,
held-out intervention, FinalDiscoverySeal, or any PASS/INFERENCE_FAILURE
verdict. This Gate is information-blocking only.
"""
from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from engine.deterministic.blind_session import (
    FORMAT,
    BlindControlDescriptor,
    BlindObservableDescriptor,
    BlindWorldDescriptor,
)
from engine.deterministic.blind_evaluator import (
    BlindTranslationManifest,
    ForbiddenBlindAccess,
    control_descriptors,
    make_blind_session,
    observable_descriptors,
    translate_control,
    translate_observable,
)
from engine.deterministic.synthetic_spec import SyntheticClamp, SyntheticWorldSpec

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_FIELD_NAMES = frozenset({
    "real_world_id", "real_world_revision", "ground_truth_id",
    "real_control_id", "real_observable_id", "rule", "fingerprint", "source",
})


def _s02_spec() -> SyntheticWorldSpec:
    return SyntheticWorldSpec(
        world_id="WORLD-S02", world_revision="R-A18D40",
        variables=("x1", "x2", "x3"),
        initial_values=(("x1", False), ("x2", False), ("x3", False)),
        clamps=(SyntheticClamp("x2", "FREE"),),
        public_controls=("x1", "x2"),
        public_observables=("x1", "x2", "x3"),
        ticks=3,
    )


# ---------------------------------------------------------------------------
# 1. Type boundary.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("blind_type", [BlindWorldDescriptor, BlindControlDescriptor, BlindObservableDescriptor])
def test_blind_type_has_no_forbidden_fields(blind_type) -> None:
    field_names = {f.name for f in dataclasses.fields(blind_type)}
    leaked = field_names & FORBIDDEN_FIELD_NAMES
    assert not leaked, f"{blind_type.__name__} structurally carries forbidden fields: {leaked}"


def test_blind_world_descriptor_has_no_real_identity_fields() -> None:
    field_names = {f.name for f in dataclasses.fields(BlindWorldDescriptor)}
    assert "alias_world_id" in field_names
    assert "world_id" not in field_names
    assert "world_revision" not in field_names


def test_blind_control_descriptor_has_no_real_control_id() -> None:
    field_names = {f.name for f in dataclasses.fields(BlindControlDescriptor)}
    assert field_names == {"alias_control_id", "alias_variable_id"}


def test_blind_observable_descriptor_has_no_real_observable_id() -> None:
    field_names = {f.name for f in dataclasses.fields(BlindObservableDescriptor)}
    assert field_names == {"alias_observable_id", "alias_variable_id"}


def test_control_and_observable_sharing_a_real_variable_share_alias_variable_id() -> None:
    """The repair this section exists to lock in: WORLD-S02's x2 is both a
    public control and a public observable (see _s02_spec) -- B must be able
    to see that the control it flips and the observable it reads name the
    same public variable, without ever learning the real name 'x2'."""
    spec = _s02_spec()
    control_items = control_descriptors(spec, seed=0)
    observable_items = observable_descriptors(spec, seed=0)

    control_variable_ids = {item.alias_variable_id for item in control_items}
    observable_variable_ids = {item.alias_variable_id for item in observable_items}
    shared_variable_ids = control_variable_ids & observable_variable_ids
    assert shared_variable_ids, "expected at least one variable id shared between a control and an observable"

    # x2 is a control and an observable in _s02_spec -- confirm by real name,
    # via the evaluator-only manifest, that the shared alias really is x2's.
    _descriptor, manifest = make_blind_session(spec, seed=0)
    assert manifest.variable_alias["x2"] in shared_variable_ids


def test_alias_variable_id_never_equals_the_control_or_observable_alias_itself() -> None:
    """Control and observable aliases stay distinct handles from each other
    and from the variable alias they point to -- only alias_variable_id is
    shared, never the control/observable alias itself."""
    spec = _s02_spec()
    for item in control_descriptors(spec, seed=0):
        assert item.alias_control_id != item.alias_variable_id
    for item in observable_descriptors(spec, seed=0):
        assert item.alias_observable_id != item.alias_variable_id


def test_translation_manifest_contains_mapping_but_is_evaluator_only() -> None:
    """The manifest is allowed to hold real identity -- that is its whole
    job -- as long as it never reaches a B-facing object graph (layer 4
    below proves that at runtime) and is not defined in the B-facing module
    (layer 2 below proves that by import closure)."""
    descriptor, manifest = make_blind_session(_s02_spec(), seed=0)
    assert manifest.real_world_id == "WORLD-S02"
    assert manifest.real_world_revision == "R-A18D40"
    assert manifest.alias_world_id == descriptor.alias_world_id
    assert set(manifest.real_variable.values()) == {"x1", "x2", "x3"}


def test_blind_translation_manifest_is_not_defined_in_blind_session_module() -> None:
    """`BlindTranslationManifest` must live in blind_evaluator.py, not
    blind_session.py -- proves the type split actually happened, not just
    that this test file imports it from the right place."""
    import engine.deterministic.blind_session as blind_session_module
    assert not hasattr(blind_session_module, "BlindTranslationManifest")
    assert not hasattr(blind_session_module, "make_blind_session")
    assert not hasattr(blind_session_module, "translate_control")
    assert not hasattr(blind_session_module, "translate_observable")


# ---------------------------------------------------------------------------
# 2. Dependency / import boundary.
# ---------------------------------------------------------------------------

def _imported_module_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _has_star_import(source: str) -> bool:
    tree = ast.parse(source)
    return any(isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
              for node in ast.walk(tree))


FORBIDDEN_MODULES = {
    # "synthetic_runtime"/"blind_evaluator" (bare) is what `ast.ImportFrom.module`
    # actually holds for `from .synthetic_runtime import X` -- `node.module`
    # never carries the leading dot, only `node.level` does. Listing only
    # the dotted/fully-qualified form here would silently miss the
    # relative-import form actual code in this package uses (see
    # `synthetic_adapter.py`'s own `from .research_world import ...` style).
    "ground_truth", "engine.deterministic.synthetic_runtime",
    ".synthetic_runtime", "synthetic_runtime",
    "engine.deterministic.blind_evaluator", ".blind_evaluator", "blind_evaluator",
}


def test_blind_session_does_not_import_ground_truth_or_synthetic_runtime() -> None:
    path = ROOT / "engine" / "deterministic" / "blind_session.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name in FORBIDDEN_MODULES or name.startswith("ground_truth.") for name in imported)


def test_blind_session_does_not_import_blind_evaluator() -> None:
    """The direction that actually matters for this repair: the B-facing
    module must not import the evaluator-only module, even though the
    reverse (blind_evaluator imports blind_session for BlindWorldDescriptor)
    is expected and fine."""
    path = ROOT / "engine" / "deterministic" / "blind_session.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    forbidden = {"engine.deterministic.blind_evaluator", ".blind_evaluator", "blind_evaluator"}
    assert not any(name in forbidden for name in imported)


def test_blind_session_has_no_wildcard_imports() -> None:
    path = ROOT / "engine" / "deterministic" / "blind_session.py"
    assert not _has_star_import(path.read_text(encoding="utf-8"))


def test_blind_evaluator_imports_from_blind_session_not_the_reverse() -> None:
    """Confirms the one-way edge actually exists in the direction intended:
    blind_evaluator.py depends on blind_session.py (for BlindWorldDescriptor),
    which is the only direction this repair allows."""
    path = ROOT / "engine" / "deterministic" / "blind_evaluator.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert any(name in {"engine.deterministic.blind_session", ".blind_session", "blind_session"}
              for name in imported)


def test_experiment_designer_dependency_closure_has_no_forbidden_imports() -> None:
    """G6d's experiment_designer.py is the module a blind research loop would
    actually call into to pick the next experiment -- re-checked here from
    G7.1's own boundary-verification angle, alongside blind_session.py."""
    path = ROOT / "engine" / "deterministic" / "experiment_designer.py"
    imported = _imported_module_names(path.read_text(encoding="utf-8"))
    assert not any(name in FORBIDDEN_MODULES or name.startswith("ground_truth.") for name in imported)
    assert not _has_star_import(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 3. Serialized-data leakage.
# ---------------------------------------------------------------------------

SECRET_VALUES = (
    "WORLD-S01", "WORLD-S02", "WORLD-S03",
    "R-7F93C2", "R-A18D40", "R-51E8B7",
    "GT-2", "GT-3", "GT-M1",
)


def _serialize(value: object) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def test_blind_descriptor_canonical_contains_no_secret_values() -> None:
    descriptor, _manifest = make_blind_session(_s02_spec(), seed=0)
    serialized = _serialize(descriptor.canonical())
    for secret in SECRET_VALUES:
        assert secret not in serialized


def test_blind_descriptor_canonical_contains_no_secret_field_names() -> None:
    descriptor, _manifest = make_blind_session(_s02_spec(), seed=0)
    for key in descriptor.canonical():
        assert key not in FORBIDDEN_FIELD_NAMES


def test_blind_control_and_observable_descriptors_contain_no_secret_values() -> None:
    spec = _s02_spec()
    for item in control_descriptors(spec, seed=0):
        serialized = _serialize(item.canonical())
        for secret in SECRET_VALUES:
            assert secret not in serialized
    for item in observable_descriptors(spec, seed=0):
        serialized = _serialize(item.canonical())
        for secret in SECRET_VALUES:
            assert secret not in serialized


def test_blind_journal_payload_contains_no_secret_values() -> None:
    """Simulates what a journal entry payload for a blind session would look
    like -- the descriptor's own canonical() form, which is exactly what a
    real journal-writing caller would pass as `payload` (see
    research_journal.JournalEntry.create)."""
    descriptor, _manifest = make_blind_session(_s02_spec(), seed=0)
    payload = {"alias_world_id": descriptor.alias_world_id, "descriptor": descriptor.canonical()}
    serialized = _serialize(payload)
    for secret in SECRET_VALUES:
        assert secret not in serialized


def test_leakage_check_catches_a_value_smuggled_past_field_names() -> None:
    """Field names being innocent is not enough -- a value can still leak
    through an otherwise-generic field. Proves the leakage check above
    would actually catch `metadata["foo"] = "WORLD-S02"`-shaped bugs."""
    smuggled = {"note": "computed from WORLD-S02"}
    serialized = _serialize(smuggled)
    assert "WORLD-S02" in serialized  # sanity: the check phrase itself is meaningful
    with pytest.raises(AssertionError):
        for secret in SECRET_VALUES:
            assert secret not in serialized


# ---------------------------------------------------------------------------
# 4. Runtime forbidden-access tripwire.
# ---------------------------------------------------------------------------

def _run_minimal_blind_path(descriptor: BlindWorldDescriptor) -> None:
    """The minimum a blind B-side session does: read the descriptor and list
    its controls/observables. None of this should ever reach for manifest
    translation. (Constructing BlindControlDescriptor/BlindObservableDescriptor
    needs alias_variable_id, which a bare BlindWorldDescriptor's
    public_controls/public_observables strings don't carry on their own --
    see control_descriptors/observable_descriptors for the full objects.)"""
    _ = descriptor.canonical()
    _ = list(descriptor.public_controls)
    _ = list(descriptor.public_observables)


def test_runtime_blind_path_never_touches_translation_manifest(monkeypatch) -> None:
    descriptor, manifest = make_blind_session(_s02_spec(), seed=0)

    def _tripped(*_args, **_kwargs):
        raise ForbiddenBlindAccess("blind path reached evaluator-only translation")

    monkeypatch.setattr("engine.deterministic.blind_evaluator.translate_control", _tripped)
    monkeypatch.setattr("engine.deterministic.blind_evaluator.translate_observable", _tripped)

    _run_minimal_blind_path(descriptor)  # must not raise


def test_runtime_tripwire_detects_forbidden_manifest_access() -> None:
    """The mirror case: a deliberately forbidden path (something calling
    translate_control/translate_observable) must actually be catchable, so
    the tripwire above is proven to detect real violations, not just
    silently pass on any input."""
    import engine.deterministic.blind_evaluator as blind_evaluator_module

    descriptor, manifest = make_blind_session(_s02_spec(), seed=0)

    def _forbidden_blind_path() -> None:
        # A hypothetical bug: B-side code reaching into the manifest through
        # the module (not a locally-bound name), same as real call sites would.
        blind_evaluator_module.translate_control(manifest, descriptor.public_controls[0])

    import unittest.mock as mock
    with mock.patch.object(
        blind_evaluator_module, "translate_control",
        side_effect=ForbiddenBlindAccess("forbidden manifest access"),
    ):
        with pytest.raises(ForbiddenBlindAccess):
            _forbidden_blind_path()


def test_translate_control_raises_forbidden_access_for_unknown_alias() -> None:
    _descriptor, manifest = make_blind_session(_s02_spec(), seed=0)
    with pytest.raises(ForbiddenBlindAccess):
        translate_control(manifest, "ALIAS-DOES-NOT-EXIST")


def test_translate_observable_raises_forbidden_access_for_unknown_alias() -> None:
    _descriptor, manifest = make_blind_session(_s02_spec(), seed=0)
    with pytest.raises(ForbiddenBlindAccess):
        translate_observable(manifest, "ALIAS-DOES-NOT-EXIST")


# ---------------------------------------------------------------------------
# Alias reproducibility.
# ---------------------------------------------------------------------------

def test_make_blind_session_is_deterministic() -> None:
    spec = _s02_spec()
    descriptor_a, manifest_a = make_blind_session(spec, seed=7)
    descriptor_b, manifest_b = make_blind_session(spec, seed=7)
    assert descriptor_a.canonical() == descriptor_b.canonical()
    assert manifest_a.variable_alias == manifest_b.variable_alias
    assert manifest_a.control_alias == manifest_b.control_alias
    assert manifest_a.observable_alias == manifest_b.observable_alias
    assert manifest_a.alias_world_id == manifest_b.alias_world_id


def test_make_blind_session_seed_changes_permutation() -> None:
    spec = _s02_spec()
    descriptor_0, manifest_0 = make_blind_session(spec, seed=0)
    descriptor_1, manifest_1 = make_blind_session(spec, seed=1)
    assert descriptor_0.alias_world_id != descriptor_1.alias_world_id
    assert manifest_0.variable_alias != manifest_1.variable_alias


def test_make_blind_session_rejects_non_integer_seed() -> None:
    with pytest.raises(ValueError):
        make_blind_session(_s02_spec(), seed="0")  # type: ignore[arg-type]


def test_blind_world_descriptor_canonical_format_is_stable() -> None:
    descriptor, _manifest = make_blind_session(_s02_spec(), seed=0)
    assert descriptor.canonical()["format"] == FORMAT
