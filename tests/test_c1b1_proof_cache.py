"""Proof Cache V0 (C1-B1): a shelf of verified witnesses, re-verified from their bytes on every use.

Verdicts 2026-09-30: Q-PC1 one append-only shelf (objects / index / events), Q-PC2 the precision schedule is admission
metadata and a production shelf admits only production-cap STOPs (the wrapper never reads the cap), Q-PC3 STALE /
REJECTED / REFUSED are distinct and REFUSED is not a falsity, contract S6: results with and without the cache are equal.
Everything runs on temporary shelves; the formal shelf runs/c1b1_proof_cache_v0/ is never touched by tests.
"""
import ast
import json
import types
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path

import pytest

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_point_prover as P
import a_reference.c1b1_proof_cache as PC
import a_reference.c1b1_runtime_local_witness as W
import a_reference.c1b1_runtime_wrapper as RW
import a_reference.c1b1_stress_survey as X
import a_reference.c1b1_two_atom as C

CACHE_SRC = Path(PC.__file__).read_text(encoding="utf-8")
REAL_PROVE = P.prove


def mk(e=Q(9), bf=Q(1, 2)):
    st = X.canonical(Q(e), Q(bf) * X.RE)
    return C.new_run(X.POS, X.DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=X.MOM)


def _first_refusal_state():
    """The next step of this run is refused at cap 128 (e = 9 De, b = Re/2, after 3 plain steps)."""
    run = mk()
    for _ in range(3):
        C.step(run)
    return run


@pytest.fixture(scope="module")
def stop():
    """One real cap-128 STOP: its key, the verified witness bytes, and the plain full-cap state after the step."""
    run = _first_refusal_state()
    with W.precision_cap(128):
        o = RW.step(run)
    assert o.status == RW.WITNESS_RESOLVED and len(o.new_certificates) == 1
    ref = _first_refusal_state()
    C.step(ref)
    key, data = o.new_certificates[0]
    return {"key": key, "data": data, "after": W._raw(ref)}


class _Spy:
    def __init__(self, monkeypatch):
        self.prove, self.check = 0, 0
        real_check = K2.check_certificate

        def prove(*a, **k):
            self.prove += 1
            return REAL_PROVE(*a, **k)

        def check(*a, **k):
            self.check += 1
            return real_check(*a, **k)
        monkeypatch.setattr(P, "prove", prove)
        monkeypatch.setattr(K2, "check_certificate", check)


def _test_admission():
    return PC._admission(PC.TEST_ONLY, 128, 128)


def _step_from_refusal(cache, config=None, module=PC):
    run = _first_refusal_state()
    before = dict(vars(run))
    with W.precision_cap(128):
        o = module.step(run, cache, config)
    return o, W._raw(run), before, run


def _lookup_only(cache, config=None):
    """A wrapper step that may READ the cache but admits nothing (to see what the shelf itself does)."""
    run = _first_refusal_state()
    config = config or RW.Config()
    with W.precision_cap(128):
        return RW.step(run, RW.Config(config.budget, config.limits, config.max_certificate_bytes,
                                      config.max_attempts_per_step, cache))


def _uses(cache):
    return [e for e in cache.events.records if e["event"] == "use"]


# --- S6 / reuse: the cache changes nothing but who found the witness -------------------------------------------------

def test_a_second_pass_takes_every_witness_from_the_cache_and_equals_the_plain_run_at_every_step(tmp_path, monkeypatch):
    n = 1640
    ref = mk()
    plain = [W._raw(ref)]
    for _ in range(n):
        C.step(ref)
        plain.append(W._raw(ref))
    spy = _Spy(monkeypatch)
    seen = []
    for rnd in (1, 2):
        spy.prove = spy.check = 0
        cache = PC.ProofCache(tmp_path, PC.TEST_ONLY, run_id=f"pass{rnd}")
        run, outs = mk(), []
        states = [W._raw(run)]
        with W.precision_cap(128):
            for _ in range(n):
                o = PC.step(run, cache)
                outs.append(o)
                assert o.advanced
                states.append(W._raw(run))
        assert states == plain, "every raw state, with the cache empty and full"
        sources = Counter(w["source"] for o in outs for w in o.witnesses)
        seen.append((sources, spy.prove, spy.check, cache.status(run)))
    (s1, p1, c1, st1), (s2, p2, c2, st2) = seen
    assert s1 == {"prover": 25} and p1 == 25 and c1 == 50                 # prover's check + the wrapper's bytes check
    assert s2 == {"cache": 25} and p2 == 0 and c2 == 25                   # the search is skipped, the check is not
    assert st2 == {"corrupt": None, "entries": 25, PC.STALE: 0, PC.REJECTED: 0, "usable": 25}
    objs = sorted(p.name for p in (tmp_path / "objects").iterdir())
    assert len(objs) == 25 and all(len(name) == 64 for name in objs)


def test_every_witness_record_carries_the_content_address_of_the_bytes_on_the_shelf(tmp_path, stop):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    o1 = _step_from_refusal(cache)[0]
    o2 = _step_from_refusal(cache)[0]
    (w1,), (w2,) = o1.witnesses, o2.witnesses
    assert (w1["source"], w2["source"]) == ("prover", "cache")
    assert w1["certificate_sha256"] == w2["certificate_sha256"] == PC._sha(stop["data"])
    assert (tmp_path / "objects" / w1["certificate_sha256"]).read_bytes() == stop["data"]
    json.dumps([w1, w2])                                                   # records stay plain JSON (bytes live on the shelf)


# --- Q-PC2: admission is the caller's layer; a production shelf takes production-cap STOPs only ------------------------

def test_a_production_shelf_refuses_rehearsal_witnesses_and_the_world_is_unaffected(tmp_path, stop):
    cache = PC.ProofCache(tmp_path, PC.PRODUCTION)
    o, state, _, _ = _step_from_refusal(cache)
    assert o.status == RW.WITNESS_RESOLVED and state == stop["after"]
    assert cache.index.records == [] and list((tmp_path / "objects").iterdir()) == []
    (ev,) = cache.events.records
    assert (ev["event"], ev["reason"]) == ("admission_refused", "not_production_cap")
    assert ev["admission"]["schedule"] == [128] and ev["admission"]["production_stop"] is False


@pytest.mark.parametrize("admission,accepted", (
    ({"kind": "production", "cap_before": 16384, "cap_after": 16384, "production_stop": True}, True),
    ({"kind": "production", "cap_before": 16384, "cap_after": 128, "production_stop": True}, False),
    ({"kind": "production", "cap_before": 128, "cap_after": 128, "production_stop": True}, False),
    ({"kind": "production", "cap_before": 16384, "cap_after": 16384, "production_stop": False}, False),
    ({"kind": "test_only", "cap_before": 16384, "cap_after": 16384, "production_stop": True}, False),
), ids=("production_cap", "cap_changed", "rehearsal_cap", "not_a_stop", "test_only_kind"))
def test_the_production_admission_rule(tmp_path, stop, admission, accepted):
    """The rule itself (a real production-cap STOP costs ~13 min; the end-to-end case is the survey's)."""
    cache = PC.ProofCache(tmp_path, PC.PRODUCTION)
    got = cache.admit(stop["key"], _first_refusal_state(), stop["data"], admission)
    assert (got is not None) == accepted
    assert len(cache.index.records) == int(accepted)


def test_the_shelf_kind_is_fixed_at_creation(tmp_path):
    PC.ProofCache(tmp_path, PC.TEST_ONLY)
    with pytest.raises(ValueError, match="not a production"):
        PC.ProofCache(tmp_path, PC.PRODUCTION)
    with pytest.raises(ValueError):
        PC.ProofCache(tmp_path / "x", "scratch")


def test_the_admission_layer_is_the_only_code_that_reads_the_cap_and_nothing_assigns_it():
    tree = ast.parse(CACHE_SRC)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AugAssign)):
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                for x in ast.walk(t):
                    assert not (isinstance(x, ast.Attribute) and x.attr in ("MAX_PRECISION_BITS", "START_PRECISION_BITS"))
    wrapper = ast.parse(Path(RW.__file__).read_text(encoding="utf-8"))
    names = {x.attr for x in ast.walk(wrapper) if isinstance(x, ast.Attribute)}
    assert "MAX_PRECISION_BITS" not in names
    imported = {a.name for n in ast.walk(wrapper) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module for n in ast.walk(wrapper) if isinstance(n, ast.ImportFrom)}
    assert "a_reference.c1b1_proof_cache" not in imported, "the wrapper never depends on the cache"
    cache_imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert "a_reference.c1b1_exact_impulse_checker" not in cache_imports and "proof_warehouse" not in cache_imports


# --- Q-PC3: STALE / REJECTED / REFUSED ---------------------------------------------------------------------------------

def _bad_bytes(kind, stop):
    doc = json.loads(stop["data"])
    if kind == "invalid_raw":
        doc["output"]["raw"] = str(int(doc["output"]["raw"]) + 1)
    elif kind == "other_input":
        cert = REAL_PROVE([int(v) for v in doc["input"]["dr_raw"]], doc["input"]["component"], stop["key"][2] * 2).certificate
        doc = dict(cert, runtime_binding=doc["runtime_binding"])
    elif kind == "stale_binding":
        doc["runtime_binding"]["executor_sha256"] = "0" * 64
    elif kind == "malformed":
        return b"{not json"
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


@pytest.mark.parametrize("kind,result,reason", (
    ("invalid_raw", PC.REJECTED, "checker_invalid"),
    ("other_input", PC.REJECTED, "input_mismatch"),
    ("malformed", PC.REJECTED, "bad_json"),
    ("stale_binding", PC.STALE, "stale_binding"),
))
def test_a_bad_entry_is_never_used_is_kept_and_the_step_falls_back_to_the_prover(tmp_path, stop, kind, result, reason):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    bad = _bad_bytes(kind, stop)
    cache.admit(stop["key"], _first_refusal_state(), bad, _test_admission())
    o, state, _, _ = _step_from_refusal(cache)
    assert o.status == RW.WITNESS_RESOLVED and o.witnesses[0]["source"] == "prover" and state == stop["after"]
    use = _uses(cache)[0]
    assert use["result"] == result and use["reason"].startswith(reason)
    assert (tmp_path / "objects" / PC._sha(bad)).read_bytes() == bad, "kept, not deleted"
    assert cache.status(_first_refusal_state())[result] == 1


@pytest.mark.parametrize("damage", ("flip_byte", "missing", "swapped"))
def test_a_damaged_object_is_rejected_by_its_address(tmp_path, stop, damage):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), stop["data"], _test_admission())
    path = tmp_path / "objects" / PC._sha(stop["data"])
    if damage == "flip_byte":
        b = bytearray(stop["data"])
        b[len(b) // 2] ^= 1
        path.write_bytes(bytes(b))
    elif damage == "missing":
        path.unlink()
    else:
        path.write_bytes(_bad_bytes("other_input", stop))                 # a valid witness of another input
    o, state, _, _ = _step_from_refusal(cache)
    assert o.witnesses[0]["source"] == "prover" and state == stop["after"]
    assert _uses(cache)[0]["result"] == PC.REJECTED
    assert _uses(cache)[0]["reason"] == ("missing_object" if damage == "missing" else "address_mismatch")


def test_a_rejected_entry_is_not_checked_again(tmp_path, stop):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), _bad_bytes("invalid_raw", stop), _test_admission())
    _lookup_only(cache)
    _lookup_only(cache)
    assert [u["result"] for u in _uses(cache)] == [PC.REJECTED]


def test_rejected_never_revives_even_when_the_bytes_are_repaired_or_the_shelf_reopened(tmp_path, stop, monkeypatch):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    entry = cache.admit(stop["key"], _first_refusal_state(), stop["data"], _test_admission())
    path = tmp_path / "objects" / entry["address"]
    path.write_bytes(stop["data"][:-1] + b" ")
    _step_from_refusal(cache)
    path.write_bytes(stop["data"])                                         # repaired: still not used
    for c in (cache, PC.ProofCache(tmp_path, PC.TEST_ONLY)):
        spy = _Spy(monkeypatch)
        o = _lookup_only(c)
        assert o.witnesses[0]["source"] == "prover" and spy.prove == 1
    assert [u["result"] for u in _uses(PC.ProofCache(tmp_path, PC.TEST_ONLY))] == [PC.REJECTED]
    assert cache.admit(stop["key"], _first_refusal_state(), stop["data"], _test_admission())["seq"] != entry["seq"]


@pytest.mark.parametrize("config,reason", (
    (RW.Config(limits=K2.Limits(order_max=1)), "checker_refused:order_limit"),
    (RW.Config(max_certificate_bytes=100), "certificate_too_large"),
), ids=("checker_refused", "byte_limit"))
def test_refused_is_not_rejected_this_use_fails_the_world_does_not_move_and_the_entry_stays(tmp_path, stop, config, reason):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), stop["data"], _test_admission())
    o, state, before, run = _step_from_refusal(cache, config)
    assert o.status == RW.UNPROVED and dict(vars(run)) == before           # the prover is refused the same way
    assert (_uses(cache)[0]["result"], _uses(cache)[0]["reason"]) == (PC.REFUSED, reason)
    assert cache.dead == {} and cache.status()["usable"] == 1
    o2, state2, _, _ = _step_from_refusal(cache)                           # later, under the default limits
    assert o2.witnesses[0]["source"] == "cache" and state2 == stop["after"]


# --- the logs: hash chains, and a broken one disables the shelf --------------------------------------------------------

@pytest.mark.parametrize("log,damage", (("index.jsonl", "edit"), ("events.jsonl", "edit"), ("index.jsonl", "truncate"),
                                        ("events.jsonl", "drop_line")))
def test_a_broken_log_disables_lookup_and_admission_but_never_the_world(tmp_path, stop, log, damage, monkeypatch):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), stop["data"], _test_admission())
    _step_from_refusal(cache)                                             # one hit event
    path = tmp_path / log
    raw = path.read_bytes()
    if damage == "edit":
        raw = raw.replace(b'"address":"', b'"address":"0', 1)
    elif damage == "truncate":
        raw = raw[:-5]
    else:
        raw = b"".join(raw.split(b"\n")[1:])
    path.write_bytes(raw)
    reopened = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    assert reopened.corrupt is not None
    spy = _Spy(monkeypatch)
    o, state, _, _ = _step_from_refusal(reopened)
    assert o.witnesses[0]["source"] == "prover" and state == stop["after"] and spy.prove == 1
    assert path.read_bytes() == raw, "a corrupt shelf is not written to"


def test_known_limit_an_edit_of_the_last_event_line_is_not_seen_but_safety_holds(tmp_path, stop):
    """A hash chain cannot see an edit of its last line. Forging the last event from REJECTED to REFUSED revives the
    entry for a re-check: it is verified again and rejected again. Availability, never safety."""
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), _bad_bytes("invalid_raw", stop), _test_admission())
    _lookup_only(cache)
    path = tmp_path / "events.jsonl"
    raw = path.read_bytes()
    assert raw.count(b'"result":"REJECTED"') == 1
    path.write_bytes(raw.replace(b'"result":"REJECTED"', b'"result":"REFUSED"'))
    reopened = PC.ProofCache(tmp_path, PC.TEST_ONLY)
    assert reopened.corrupt is None and reopened.dead == {}, "the limit is real"
    o = _lookup_only(reopened)
    assert o.witnesses[0]["source"] == "prover" and _uses(reopened)[-1]["result"] == PC.REJECTED


def test_the_logs_hold_no_certificate_bytes_and_the_index_holds_only_key_to_address(tmp_path, stop):
    cache = PC.ProofCache(tmp_path, PC.TEST_ONLY, run_id="r")
    _step_from_refusal(cache)
    _step_from_refusal(cache)
    (entry,) = cache.index.records
    assert set(entry) == {"seq", "prev", "key_id", "key", "address"}
    assert entry["key"]["input"]["dr_raw"] == json.loads(stop["data"])["input"]["dr_raw"]
    admit = [e for e in cache.events.records if e["event"] == "admit"][0]
    assert admit["admission"]["kind"] == PC.TEST_ONLY and admit["run_id"] == "r" and admit["prover"]["status"] == P.FOUND
    for f in ("index.jsonl", "events.jsonl"):
        assert b'"proof"' not in (tmp_path / f).read_bytes()


# --- fault injection: mutants of the cache module ----------------------------------------------------------------------

def _mutant(*replacements):
    src = CACHE_SRC
    for old, new in replacements:
        assert src.count(old) == 1, f"mutation target must occur exactly once: {old!r}"
        src = src.replace(old, new)
    mod = types.ModuleType("mutant_cache")
    mod.__file__ = PC.__file__
    exec(compile(src, "mutant_cache.py", "exec"), mod.__dict__)
    return mod


def test_mutant_that_trusts_the_stored_bytes_accepts_a_forgery_and_the_differential_catches_it(tmp_path, stop):
    mod = _mutant(("            raw = RW.verify_witness(data, key, run, None, config)\n",
                   "            raw = int(json.loads(data)['output']['raw'])\n"))
    cache = mod.ProofCache(tmp_path, mod.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), _bad_bytes("invalid_raw", stop), _test_admission())
    o, state, _, _ = _step_from_refusal(cache, module=mod)
    assert o.witnesses[0]["source"] == "cache" and state != stop["after"]


def test_mutant_that_calls_refused_rejected_loses_the_entry_for_good(tmp_path, stop):
    mod = _mutant(('    if reason.startswith("checker_refused:") or reason == "certificate_too_large":\n        return REFUSED\n',
                   '    if reason.startswith("checker_refused:") or reason == "certificate_too_large":\n        return REJECTED\n'))
    cache = mod.ProofCache(tmp_path, mod.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), stop["data"], _test_admission())
    _step_from_refusal(cache, RW.Config(limits=K2.Limits(order_max=1)), module=mod)
    o2 = _step_from_refusal(cache, module=mod)[0]
    assert o2.witnesses[0]["source"] == "prover", "the REFUSED test must see a mutant that buries a true proof"


def test_mutant_without_the_cap_rule_fills_a_production_shelf_with_rehearsal_witnesses(tmp_path):
    mod = _mutant(('        if not (admission.get("cap_before") == admission.get("cap_after") == PRODUCTION_CAP):\n'
                   '            return "not_production_cap"\n', ""),
                  ('        if admission.get("production_stop") is not True:\n            return "not_a_production_stop"\n', ""))
    cache = mod.ProofCache(tmp_path, mod.PRODUCTION)
    _step_from_refusal(cache, module=mod)
    assert len(cache.index.records) == 1, "the production-shelf test must see a mutant that ignores the cap"


def test_mutant_that_forgets_dead_entries_keeps_retrying_a_rejected_object(tmp_path, stop):
    mod = _mutant(('            if entry["key_id"] != kid or entry["seq"] in self.dead:\n',
                   '            if entry["key_id"] != kid:\n'))
    cache = mod.ProofCache(tmp_path, mod.TEST_ONLY)
    cache.admit(stop["key"], _first_refusal_state(), _bad_bytes("invalid_raw", stop), _test_admission())
    _lookup_only(cache)
    _lookup_only(cache)
    assert len(_uses(cache)) == 2, "the sticky-REJECTED test must see a mutant that re-checks a rejected entry"
