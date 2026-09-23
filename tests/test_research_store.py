"""Research data store: tiers, immutability, provenance, leakage, dependencies.

Every test writes under pytest's tmp_path -- never to the real store on D:.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from engine.deterministic.blind_evaluator import control_descriptors, make_blind_session, observable_descriptors
from engine.deterministic.blind_research_loop import run_blind_research
from engine.deterministic.blind_synthetic_executor import SyntheticBlindAExecutor
from engine.deterministic.research_journal import ResearchJournal
from engine.deterministic.synthetic_spec import SyntheticWorldSpec
from research_store._core import (
    B_VISIBLE, EVALUATOR, GROUND_TRUTH, SemanticsMismatchError, StoreIntegrityError, TierStore,
    require_single_semantics,
)
from research_store.b_visible import BVisibleReader, BVisibleWriter, LeakageError, SchemaViolation, StringPolicy
from research_store.b_visible_schema import VOCABULARY
from research_store.provenance import BLIND_RESEARCH_SEMANTICS
from research_store.evaluator import EvaluatorStore, verify_store
from research_store.ingest_blind import secrets_of, store_blind_research_run

ROOT = Path(__file__).resolve().parents[1]
PROV = {"commit": "test", "dirty": False, "producer": "tests", "semantics": "sem-A"}
SECRETS = ("REAL-SECRET",)
# Generic mechanics tests store toy values; their words are allowlisted here
# explicitly rather than by loosening the real blind-research policy.
TEST_POLICY = StringPolicy(semantics=frozenset({"sem-A", "sem-B"}),
                           vocabulary=VOCABULARY | {"a", "b", "ok", "s", "i", "t", "tests", "test", "x", "real",
                                                    "stuff", "orphan", "deep", "note", "world", "0", "1", "2",
                                                    "forged", "9"})
INGEST_PROV = {"commit": "0" * 40, "dirty": False, "producer": "run_blind_benchmark.py",
               "semantics": BLIND_RESEARCH_SEMANTICS}


def _s03(ticks=2, initial=None) -> SyntheticWorldSpec:
    initial = initial or {}
    v = ("x1", "x2", "x3")
    return SyntheticWorldSpec(world_id="WORLD-S03", world_revision="R-51E8B7", variables=v,
                              initial_values=tuple((x, initial.get(x, False)) for x in v), clamps=(),
                              public_controls=("x1", "x2"), public_observables=v, ticks=ticks)


def _ingested_run(tmp_path: Path, spec: SyntheticWorldSpec | None = None, seed: int = 0):
    spec = spec or _s03()
    world, manifest = make_blind_session(spec, seed)
    journal_path = tmp_path / f"journal-{seed}.jsonl"
    journal = ResearchJournal.create(journal_path)
    outcome = run_blind_research(world, control_descriptors(spec, seed), observable_descriptors(spec, seed),
                                 SyntheticBlindAExecutor(spec, manifest), journal)
    journal.close()
    root = tmp_path / "store"
    records = store_blind_research_run(root, real_spec=spec, seed=seed, manifest=manifest, outcome=outcome,
                                       journal_path=journal_path, provenance=INGEST_PROV)
    return root, spec, manifest, outcome, records


# ---------------------------------------------------------------------------
# Objects and records.
# ---------------------------------------------------------------------------

def test_objects_are_content_addressed_and_stored_once(tmp_path) -> None:
    store = TierStore(tmp_path, B_VISIBLE)
    first = store.put_object({"a": 1, "b": [1, 2]})
    second = store.put_object({"b": [1, 2], "a": 1})
    assert first == second
    assert len(list((tmp_path / B_VISIBLE / "objects").rglob("*.json"))) == 1
    assert store.get_object(first) == {"a": 1, "b": [1, 2]}


def test_edited_object_is_detected(tmp_path) -> None:
    store = TierStore(tmp_path, B_VISIBLE)
    ref = store.put_object({"a": 1})
    store.append_record("t", 1, PROV, {}, ref)
    [path] = list((tmp_path / B_VISIBLE / "objects").rglob("*.json"))
    path.write_text('{"a":2}', encoding="utf-8")
    with pytest.raises(StoreIntegrityError):
        verify_store(tmp_path)


@pytest.mark.parametrize("tamper", ["edit", "delete", "reorder"])
def test_index_chain_detects_any_rewrite_of_history(tmp_path, tamper) -> None:
    store = TierStore(tmp_path, EVALUATOR)
    for i in range(3):
        store.append_record("t", 1, PROV, {"i": str(i)}, store.put_object({"i": i}))
    lines = store.index_path.read_text(encoding="utf-8").splitlines()
    original = list(lines)
    if tamper == "edit":
        lines[1] = lines[1].replace('"i": "1"', '"i": "9"')
    elif tamper == "delete":
        del lines[1]
    else:
        lines[1], lines[2] = lines[2], lines[1]
    assert lines != original  # the tamper really happened
    store.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(StoreIntegrityError):
        verify_store(tmp_path)


def test_a_record_rewritten_with_a_recomputed_digest_breaks_the_chain(tmp_path) -> None:
    """Sequence numbers catch deletion and reordering, the record digest
    catches a naive edit; only the chain catches a careful forgery -- a
    record replaced wholesale with its own digest correctly recomputed."""
    from research_store._core import StoreRecord, digest
    store = TierStore(tmp_path, EVALUATOR)
    for i in range(3):
        store.append_record("t", 1, PROV, {"i": str(i)}, store.put_object({"i": i}))
    records = list(store.records())
    forged_draft = StoreRecord(**{**records[1].__dict__, "tags": {"i": "forged"},
                                  "previous_digest": records[0].record_digest})
    forged = StoreRecord(**{**forged_draft.__dict__, "record_digest": digest(forged_draft.body())})
    lines = store.index_path.read_text(encoding="utf-8").splitlines()
    lines[1] = json.dumps(forged.canonical(), ensure_ascii=False, sort_keys=True)
    store.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(StoreIntegrityError):
        verify_store(tmp_path)


def test_corruption_of_an_unreferenced_object_is_detected(tmp_path) -> None:
    TierStore(tmp_path, B_VISIBLE).put_object({"orphan": True})
    [path] = list((tmp_path / B_VISIBLE / "objects").rglob("*.json"))
    path.write_text('{"orphan":false}', encoding="utf-8")
    with pytest.raises(StoreIntegrityError):
        verify_store(tmp_path)


def test_b_visible_record_may_not_reference_a_secret_tier(tmp_path) -> None:
    secret = EvaluatorStore(tmp_path).put(EVALUATOR, {"real": "stuff"})
    writer = BVisibleWriter(tmp_path)
    own = writer.put({"ok": 1}, forbidden_values=SECRETS, policy=TEST_POLICY)
    with pytest.raises(ValueError):
        writer.record("t", 1, PROV, {}, own, refs=(secret,), forbidden_values=SECRETS, policy=TEST_POLICY)


def test_evaluator_record_may_reference_b_visible(tmp_path) -> None:
    b_ref = BVisibleWriter(tmp_path).put({"ok": 1}, forbidden_values=SECRETS, policy=TEST_POLICY)
    evaluator = EvaluatorStore(tmp_path)
    evaluator.record(EVALUATOR, "t", 1, PROV, {}, evaluator.put(EVALUATOR, {"x": 1}), refs=(b_ref,))
    assert verify_store(tmp_path)[EVALUATOR]["records"] == 1


def test_record_requires_semantics_in_provenance(tmp_path) -> None:
    store = TierStore(tmp_path, GROUND_TRUTH)
    with pytest.raises(ValueError):
        store.append_record("t", 1, {"commit": "x"}, {}, store.put_object({}))


# ---------------------------------------------------------------------------
# Leakage guard and semantics guard.
# ---------------------------------------------------------------------------

def test_b_visible_write_refuses_a_secret_anywhere_in_the_value(tmp_path) -> None:
    writer = BVisibleWriter(tmp_path)
    with pytest.raises(LeakageError):
        writer.put({"deep": [{"note": "from REAL-SECRET"}]}, forbidden_values=SECRETS, policy=TEST_POLICY)
    assert not (tmp_path / B_VISIBLE).exists()


def test_b_visible_write_refuses_a_secret_in_tags(tmp_path) -> None:
    writer = BVisibleWriter(tmp_path)
    ref = writer.put({"ok": 1}, forbidden_values=SECRETS, policy=TEST_POLICY)
    with pytest.raises(LeakageError):
        writer.record("t", 1, PROV, {"world": "REAL-SECRET"}, ref, forbidden_values=SECRETS, policy=TEST_POLICY)


def test_b_visible_write_cannot_skip_the_scan(tmp_path) -> None:
    with pytest.raises(ValueError):
        BVisibleWriter(tmp_path).put({"ok": 1}, forbidden_values=(), policy=TEST_POLICY)
    with pytest.raises(TypeError):
        BVisibleWriter(tmp_path).put({"ok": 1}, policy=TEST_POLICY)
    with pytest.raises(TypeError):
        BVisibleWriter(tmp_path).put({"ok": 1}, forbidden_values=SECRETS)


def test_reader_requires_an_explicit_semantics_and_never_mixes(tmp_path) -> None:
    writer = BVisibleWriter(tmp_path)
    for semantics in ("sem-A", "sem-B"):
        writer.record("t", 1, {**PROV, "semantics": semantics}, {}, writer.put({"s": semantics},
                      forbidden_values=SECRETS, policy=TEST_POLICY), forbidden_values=SECRETS, policy=TEST_POLICY)
    reader = BVisibleReader(tmp_path)
    with pytest.raises(TypeError):
        reader.records("t")
    assert len(reader.records("t", semantics="sem-A")) == 1
    with pytest.raises(SemanticsMismatchError):
        require_single_semantics(reader.all_records())


# ---------------------------------------------------------------------------
# End-to-end: storing a G7.3c blind research run.
# ---------------------------------------------------------------------------

def test_blind_run_is_stored_across_tiers_and_verifies(tmp_path) -> None:
    root, _spec, _manifest, outcome, (b_record, e_record) = _ingested_run(tmp_path)
    counts = verify_store(root)
    assert counts[B_VISIBLE]["records"] == 1 and counts[EVALUATOR]["records"] == 1
    assert counts[GROUND_TRUTH]["records"] == 0
    assert e_record.refs == (b_record.payload,)
    assert b_record.tags["protocol_valid"] == "true"
    payload = BVisibleReader(root).get(b_record.payload)
    assert payload["outcome"] == outcome.canonical()


def test_stored_journal_holds_every_observed_run_not_just_its_digest(tmp_path) -> None:
    """What a learned B would train on: every executed experiment's actual
    observations, recoverable from the b_visible tier alone."""
    root, _spec, _manifest, outcome, (b_record, _e) = _ingested_run(tmp_path)
    journal = BVisibleReader(root).get(b_record.payload)["journal"]
    executed = [e["record_id"] for e in journal if e["event_type"] == "execution_completed"]
    observed = {e["record_id"]: e["payload"]["run"] for e in journal if e["event_type"] == "observation_recorded"}
    assert executed == list(outcome.executed_candidate_ids)
    assert sorted(observed) == sorted(executed)
    assert all(run["checkpoints"] for run in observed.values())


def test_b_visible_tier_on_disk_contains_no_secret(tmp_path) -> None:
    root, spec, manifest, _outcome, _records = _ingested_run(tmp_path)
    text = "".join(p.read_text(encoding="utf-8") for p in (root / B_VISIBLE).rglob("*") if p.is_file())
    for secret in secrets_of(spec, manifest):
        assert secret not in text
    evaluator_text = "".join(p.read_text(encoding="utf-8") for p in (root / EVALUATOR).rglob("*") if p.is_file())
    assert "WORLD-S03" in evaluator_text  # the mapping really is kept -- on the evaluator side


def test_a_run_with_a_broken_protocol_is_kept_and_flagged(tmp_path) -> None:
    spec = _s03()
    world, manifest = make_blind_session(spec, 0)
    journal_path = tmp_path / "j.jsonl"
    journal = ResearchJournal.create(journal_path)
    outcome = run_blind_research(world, control_descriptors(spec, 0), observable_descriptors(spec, 0),
                                 SyntheticBlindAExecutor(spec, manifest), journal)
    # A status change written after the final seal: allowlisted words only,
    # so the run is stored -- and flagged by the protocol audit.
    some_hypothesis = outcome.final_hypothesis_set.hypotheses[0].hypothesis_id
    journal.append("hypothesis_status_changed", some_hypothesis, {"status": "untested"})
    journal.close()
    b_record, _ = store_blind_research_run(tmp_path / "store", real_spec=spec, seed=0, manifest=manifest,
                                           outcome=outcome, journal_path=journal_path, provenance=INGEST_PROV)
    assert b_record.tags["protocol_valid"] == "false"


def test_secret_in_a_run_blocks_ingest_before_anything_is_written(tmp_path, monkeypatch) -> None:
    """If B's outcome ever carried a real name, the whole ingest must stop at
    the b_visible scan -- no partial run on disk."""
    import research_store.ingest_blind as ingest
    root, *_ = _ingested_run(tmp_path)  # a clean run first
    spec = _s03()
    world, manifest = make_blind_session(spec, 1)
    journal_path = tmp_path / "leaky.jsonl"
    journal = ResearchJournal.create(journal_path)
    outcome = run_blind_research(world, control_descriptors(spec, 1), observable_descriptors(spec, 1),
                                 SyntheticBlindAExecutor(spec, manifest), journal)
    journal.append("anomaly_recorded", "LEAK", {"note": "WORLD-S03"})
    journal.close()
    before = verify_store(root)
    with pytest.raises(LeakageError):
        ingest.store_blind_research_run(root, real_spec=spec, seed=1, manifest=manifest, outcome=outcome,
                                        journal_path=journal_path, provenance=INGEST_PROV)
    assert verify_store(root) == before


# ---------------------------------------------------------------------------
# Dependency boundaries.
# ---------------------------------------------------------------------------

STORE = ROOT / "research_store"


def _store_imports(module: str) -> set[str]:
    tree = ast.parse((STORE / f"{module}.py").read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level >= 1:
                found.add(node.module.split(".")[0] if node.module else "*")
            elif node.module:
                found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


def _store_closure(start: str) -> set[str]:
    seen, stack = set(), [start]
    while stack:
        module = stack.pop()
        if module in seen or not (STORE / f"{module}.py").exists():
            seen.add(module)
            continue
        seen.add(module)
        stack.extend(_store_imports(module))
    return seen


def test_b_visible_module_cannot_reach_secret_tiers_or_the_engine() -> None:
    closure = _store_closure("b_visible")
    assert "evaluator" not in closure and "ingest_blind" not in closure
    assert not any(name.startswith("engine") or name.startswith("ground_truth") for name in closure)


def test_package_init_imports_nothing() -> None:
    tree = ast.parse((STORE / "__init__.py").read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]


def test_closure_walker_sees_the_evaluator_side() -> None:
    assert "evaluator" in _store_closure("ingest_blind")


def test_no_engine_module_imports_research_store() -> None:
    """B-side code (and the engine generally) never reads the store; only
    harness scripts and the ingest module sit on top of both."""
    for path in (ROOT / "engine").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "research_store" not in text, path


# ---------------------------------------------------------------------------
# Allowlist (second wall).
# ---------------------------------------------------------------------------

BLIND_POLICY = StringPolicy(semantics=frozenset({BLIND_RESEARCH_SEMANTICS}))


@pytest.mark.parametrize("value", [
    {"note": "the gate variable"},          # free text nobody put on a forbidden list
    {"status": "x1"},                       # a real-name-shaped word as a value
    {"x1": True},                           # ...as a key
    ["ALIAS-0000000G"],                     # not a real alias shape (G is not hex)
    ["ALIAS-00000000 -> x3"],               # statement with a non-alias token
    [1.5],                                  # non-JSON-integer number
])
def test_allowlist_refuses_what_no_forbidden_list_names(tmp_path, value) -> None:
    with pytest.raises(SchemaViolation):
        BVisibleWriter(tmp_path).put(value, forbidden_values=SECRETS, policy=BLIND_POLICY)
    assert not (tmp_path / B_VISIBLE).exists()


@pytest.mark.parametrize("value", [
    {"statement": "ALIAS-0A1B2C3D AND ALIAS-11111111 -> ALIAS-22222222"},
    {"statement": "no controllable variable affects ALIAS-0A1B2C3D"},
    {"applicability_conditions": ["alias_world:ALIAS-0A1B2C3D", "baseline:false", "time:one_tick_per_edge"]},
    {"verdicts": "INSEPARABLE,SOLVED"},
    {"hypothesis_id": "BH-0123456789abcdef", "observables": [["ALIAS-0A1B2C3D", True]]},
])
def test_allowlist_admits_the_blind_vocabulary(tmp_path, value) -> None:
    BVisibleWriter(tmp_path).put(value, forbidden_values=SECRETS, policy=BLIND_POLICY)


@pytest.mark.parametrize("value", [
    {"status": "SECRET-LOOKING-TEXT"},   # rejected value under an allowed key
    {"SECRET-LOOKING-TEXT": 1},          # rejected key
])
def test_allowlist_error_never_echoes_the_rejected_string(value) -> None:
    with pytest.raises(SchemaViolation) as caught:
        BLIND_POLICY.check(value)
    assert "SECRET-LOOKING-TEXT" not in str(caught.value)


def test_ingest_refuses_provenance_under_an_unlisted_semantics(tmp_path) -> None:
    spec = _s03()
    world, manifest = make_blind_session(spec, 0)
    journal_path = tmp_path / "j.jsonl"
    journal = ResearchJournal.create(journal_path)
    outcome = run_blind_research(world, control_descriptors(spec, 0), observable_descriptors(spec, 0),
                                 SyntheticBlindAExecutor(spec, manifest), journal)
    journal.close()
    with pytest.raises(SchemaViolation):
        store_blind_research_run(tmp_path / "store", real_spec=spec, seed=0, manifest=manifest, outcome=outcome,
                                 journal_path=journal_path, provenance={**INGEST_PROV, "semantics": "some-old-rule"})


def test_b_visible_schema_module_is_pure() -> None:
    assert not any(n.startswith(("engine", "ground_truth")) or n in {"evaluator", "ingest_blind"}
                   for n in _store_imports("b_visible_schema"))
