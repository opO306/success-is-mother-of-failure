"""The independent trace reader must stay independent, and must actually bite.

Two failure modes matter here:

1. The second reader quietly grows a dependency on the engine and stops being
   a second opinion at all. `test_audit_package_imports_nothing_from_engine`
   makes that a test failure rather than a matter of discipline.

2. Both readers pass everything, because neither looks. The tampering tests
   corrupt a trace in ways the engine's own verifier rejects and require the
   independent reader to reject them too — by its own route.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from audit.independent_trace import (
    CanonicalError,
    DeltaError,
    apply_delta,
    canonical_text,
    digest,
    parse_path,
    sha256_via_external_tool,
    verify_trace_independently,
)
from engine.deterministic import (
    PrivateTraceWriter,
    load_environment_world_spec,
    trace_environment_run,
    verify_trace,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_environment_v1.json"
AUDIT = ROOT / "audit"


def _build_trace(tmp_path: Path) -> tuple[Path, dict]:
    spec = load_environment_world_spec(EXAMPLE)
    run_dir = tmp_path / "private-run"
    writer = PrivateTraceWriter(run_dir, "private-run")
    final_state = trace_environment_run(spec, writer)
    manifest = writer.close(spec.digest, final_state.digest)
    return run_dir, manifest


def _rewrite(run_dir: Path, records: list[dict]) -> None:
    """Write records back without touching the manifest."""
    text = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for item in records
    )
    (run_dir / "records.jsonl").write_text(text, encoding="utf-8", newline="\n")


def _records(run_dir: Path) -> list[dict]:
    return [json.loads(line)
            for line in (run_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()]


def _codes(run_dir: Path) -> set[str]:
    return {finding.code for finding in verify_trace_independently(run_dir).findings}


# --- independence -----------------------------------------------------------

def test_audit_package_imports_nothing_from_engine() -> None:
    """Every audit subpackage except `ground_truth` must never import `engine`.

    `ground_truth` is a different kind of checker by design: it drives the A0
    causal kernel directly to build an answer key from interventions on A
    itself (see `audit/ground_truth/README.md`), rather than independently
    re-reading a record the engine already produced. Its own, narrower
    boundary -- nothing from B0.3 upward -- is enforced by
    `tests/test_audit_ground_truth.py::test_no_ground_truth_module_imports_b_code`.
    """
    offenders = []
    for path in sorted(AUDIT.rglob("*.py")):
        if "ground_truth" in path.relative_to(AUDIT).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name == "engine" or name.startswith("engine."):
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} imports {name}")
    assert offenders == [], "the audit package must not depend on the engine: " + "; ".join(offenders)


def test_independent_reader_does_not_reuse_engine_helpers() -> None:
    """The canonical form is restated here, not delegated to json.dumps.

    Checked against the parsed code rather than the raw text, so the module
    may still name `json.dumps` in prose explaining why it avoids it.
    """
    path = AUDIT / "independent_trace" / "canonical.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("dumps", "dump")
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "json"
    ]
    assert calls == [], "canonical hashing must not delegate to json.dumps"


# --- agreement with the engine on honest traces -----------------------------

def test_agrees_with_engine_on_an_untampered_trace(tmp_path: Path) -> None:
    run_dir, manifest = _build_trace(tmp_path)
    engine_result = verify_trace(run_dir)
    independent = verify_trace_independently(run_dir)

    assert independent.valid is True
    assert independent.findings == []
    assert independent.record_count == engine_result["record_count"] == manifest["record_count"]
    assert independent.final_chain_hash == engine_result["final_chain_hash"]
    assert independent.records_sha256 == manifest["records_sha256"]
    assert independent.tick_digests == engine_result["tick_digests"]


def test_external_tool_confirms_the_records_hash(tmp_path: Path) -> None:
    run_dir, manifest = _build_trace(tmp_path)
    external = sha256_via_external_tool(run_dir / "records.jsonl")
    if not external.available:
        pytest.skip(f"external sha256sum unavailable: {external.detail}")
    assert external.digest == manifest["records_sha256"]


# --- tampering must be caught, by this reader's own route -------------------

def test_catches_a_changed_snapshot_value(tmp_path: Path) -> None:
    run_dir, _ = _build_trace(tmp_path)
    records = _records(run_dir)
    target = next(item for item in records if item["kind"] == "tick_commit")
    target["payload"]["full_snapshot"]["causal"]["tick"] += 1
    _rewrite(run_dir, records)

    with pytest.raises(ValueError):
        verify_trace(run_dir)
    assert _codes(run_dir) & {"tick_commit_digest_mismatch", "tick_commit_discontinuous"}


def test_catches_a_delta_that_does_not_reconstruct_its_successor(tmp_path: Path) -> None:
    """The engine regenerates the delta; this reader applies it. Both must object."""
    run_dir, _ = _build_trace(tmp_path)
    records = _records(run_dir)
    stage = next(item for item in records
                 if item["kind"] == "stage_commit" and item["payload"]["delta"])
    stage["payload"]["delta"] = []
    stage["payload"]["delta_count"] = 0
    _rewrite(run_dir, records)

    with pytest.raises(ValueError):
        verify_trace(run_dir)
    assert "delta_does_not_reconstruct" in _codes(run_dir)


def test_catches_a_delta_whose_before_value_is_wrong(tmp_path: Path) -> None:
    run_dir, _ = _build_trace(tmp_path)
    records = _records(run_dir)
    stage = next(item for item in records
                 if item["kind"] == "stage_commit" and item["payload"]["delta"])
    entry = stage["payload"]["delta"][0]
    if isinstance(entry.get("before"), int) and entry.get("op") == "replace":
        entry["before"] = entry["before"] + 1000
    else:
        entry["before"] = "not-the-recorded-value"
    _rewrite(run_dir, records)

    assert _codes(run_dir) & {"delta_not_applicable", "delta_does_not_reconstruct"}


def test_catches_a_broken_hash_chain(tmp_path: Path) -> None:
    run_dir, _ = _build_trace(tmp_path)
    records = _records(run_dir)
    records[3]["previous_hash"] = "0" * 64
    _rewrite(run_dir, records)

    with pytest.raises(ValueError):
        verify_trace(run_dir)
    assert "chain_broken" in _codes(run_dir)


def test_catches_a_removed_record(tmp_path: Path) -> None:
    run_dir, _ = _build_trace(tmp_path)
    records = _records(run_dir)
    del records[5]
    _rewrite(run_dir, records)

    with pytest.raises(ValueError):
        verify_trace(run_dir)
    assert _codes(run_dir) & {"sequence_not_contiguous", "chain_broken", "record_count_mismatch"}


def test_catches_a_forged_record_hash(tmp_path: Path) -> None:
    """Re-chaining a tampered trace still fails: the body no longer hashes to its label."""
    run_dir, _ = _build_trace(tmp_path)
    records = _records(run_dir)
    target = next(item for item in records if item["kind"] == "tick_start")
    target["payload"]["state_digest"] = "f" * 64
    _rewrite(run_dir, records)

    assert _codes(run_dir) & {"record_hash_mismatch", "tick_start_digest_mismatch"}


def test_reports_every_finding_rather_than_stopping_at_the_first(tmp_path: Path) -> None:
    run_dir, _ = _build_trace(tmp_path)
    records = _records(run_dir)
    for item in records:
        if item["kind"] == "tick_commit":
            item["payload"]["state_digest"] = "e" * 64
    _rewrite(run_dir, records)

    findings = verify_trace_independently(run_dir).findings
    assert len({item.sequence for item in findings}) > 1


def test_manifest_and_records_must_both_be_present(tmp_path: Path) -> None:
    run_dir, _ = _build_trace(tmp_path)
    (run_dir / "manifest.json").unlink()
    assert "manifest_missing" in _codes(run_dir)


def test_records_hash_mismatch_is_reported(tmp_path: Path) -> None:
    run_dir, _ = _build_trace(tmp_path)
    path = run_dir / "records.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
    assert "records_sha256_mismatch" in _codes(run_dir)


# --- the point of the exercise: catching what the engine cannot -------------

def test_catches_a_recorder_bug_the_engines_own_verifier_cannot_see(tmp_path: Path) -> None:
    """A fault shared by writer and verifier is invisible to the engine alone.

    `verify_trace` re-runs the same `_delta()` that wrote the trace, so a delta
    the recorder computes wrongly is compared against an equally wrong
    regeneration and passes. Here `_delta` is patched to drop a real change;
    the engine accepts the result, and the independent reader — which applies
    the recorded delta instead of regenerating it — rejects it.

    This is the test that justifies the second implementation existing.
    """
    from engine.deterministic import provenance

    original = provenance._delta

    def dropping_delta(before, after, path="$"):
        changes = original(before, after, path)
        return [item for item in changes if not item["path"].endswith(".causal.tick")]

    spec = load_environment_world_spec(EXAMPLE)
    run_dir = tmp_path / "faulty-run"
    monkeypatched = getattr(provenance, "_delta")
    try:
        provenance._delta = dropping_delta
        writer = PrivateTraceWriter(run_dir, "faulty-run")
        final_state = trace_environment_run(spec, writer)
        writer.close(spec.digest, final_state.digest)

        # The engine re-derives the delta with the same faulty function.
        assert verify_trace(run_dir)["valid"] is True
    finally:
        provenance._delta = monkeypatched

    independent = verify_trace_independently(run_dir)
    assert independent.valid is False
    assert {item.code for item in independent.findings} == {"delta_does_not_reconstruct"}
    assert len(independent.findings) == spec.causal_world.ticks


# --- the canonical form and delta application, checked on their own ---------

def test_canonical_form_sorts_keys_and_rejects_floats() -> None:
    assert canonical_text({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert canonical_text([1, True, False, None]) == "[1,true,false,null]"
    assert canonical_text({"k": "a\"b\\c"}) == '{"k":"a\\"b\\\\c"}'
    with pytest.raises(CanonicalError):
        canonical_text({"k": 1.5})


def test_canonical_digest_matches_the_engines_on_shared_values() -> None:
    """Two independent implementations of the same stated form must agree."""
    import hashlib

    for value in ({"a": 1, "b": [1, 2, 3]}, {"nested": {"x": {"y": 0}}}, {"s": "héllo"}):
        engine_style = hashlib.sha256(
            json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")).hexdigest()
        assert digest(value) == engine_style


def test_parse_path_rejects_array_indexing() -> None:
    assert parse_path("$") == ()
    assert parse_path("$.a.b") == ("a", "b")
    for bad in ("a.b", "$.a..b", "$.cells[0]"):
        with pytest.raises(DeltaError):
            parse_path(bad)


def test_apply_delta_checks_the_before_value() -> None:
    before = {"a": 1, "b": {"c": 2}}
    good = [{"op": "replace", "path": "$.b.c", "before": 2, "after": 9}]
    assert apply_delta(before, good) == {"a": 1, "b": {"c": 9}}
    assert before == {"a": 1, "b": {"c": 2}}, "apply_delta must not mutate its input"

    wrong = [{"op": "replace", "path": "$.b.c", "before": 77, "after": 9}]
    with pytest.raises(DeltaError):
        apply_delta(before, wrong)


def test_apply_delta_handles_add_and_remove() -> None:
    before = {"a": 1}
    assert apply_delta(before, [{"op": "add", "path": "$.b", "after": 2}]) == {"a": 1, "b": 2}
    assert apply_delta(before, [{"op": "remove", "path": "$.a", "before": 1}]) == {}
    with pytest.raises(DeltaError):
        apply_delta(before, [{"op": "add", "path": "$.a", "after": 5}])
    with pytest.raises(DeltaError):
        apply_delta(before, [{"op": "remove", "path": "$.missing", "before": 1}])
