"""RESOURCE_EVOLUTION_PILOT_V1: smallest counterexamples / fault injections (handoff section 23) before any campaign.
Core: affinity applied and read back; ignored affinity and unexited children are flagged. Parallel: pair-parallel
reduction is bit-identical; a duplicate DECIDED candidate is accepted once. Pressure: tiny budget -> RESOURCE_REFUSED;
retry budget exhausted -> BUDGET_STARVATION. Conditioning: neutral cue stays neutral; reversal; leakage flagged.
Risk/speculation: a wrong DECIDED claim is never accepted; false accept detection; p95 not claimed from few samples."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.resource_evolution_v1 import checker as CK
from experiments.resource_evolution_v1 import orch as O
from experiments.resource_evolution_v1 import selector as SEL
from experiments.resource_evolution_v1 import verifier as VF

PKG = Path(SEL.__file__).resolve().parent


def env(cores=(2,), cpu=600.0, wall=600.0, ram=4096, spec=3):
    return {"tier": "test", "cores": len(cores), "cpu_s": cpu, "wall_s": wall, "ram_mb": ram, "spec": spec,
            "core_set": list(cores), "u": 1.0}


@pytest.fixture(scope="module")
def base_run(tmp_path_factory):
    d = tmp_path_factory.mktemp("re")
    return d, O.run_plan(d, "base", "BASE", env(), "A2_bound", 100)


def test_affinity_applied_read_back_and_result_verified(base_run):
    d, r = base_run
    w = r["workers"][0]
    assert r["status"] == "VERIFIED" and w["start"]["affinity_readback"] == [2] and w["parent_pinned"] == [2]
    assert w["exited_confirmed"] and r["all_workers_exited"]


def test_checker_flags_ignored_affinity_and_unexited_child(base_run):
    d, r = base_run
    bad = copy.deepcopy(r)
    bad["workers"][0]["start"]["affinity_readback"] = [0, 1, 2, 3]
    bad["workers"][0]["exited_confirmed"] = False
    inv, fa = [], []
    _run_accept_check(bad, inv, fa)
    assert any("affinity" in x for x in inv) and any("exit not confirmed" in x for x in inv)
    tampered = copy.deepcopy(r)
    tampered["workers"][0]["passes"][-1]["cells"][0] += 1
    inv2, fa2 = [], []
    _run_accept_check(tampered, inv2, fa2)
    assert fa2                                          # an accepted pass that fails re-verification = false accept


def _run_accept_check(rec, inv, fa):
    CK.check_run("synthetic", rec, "A2_bound", 100, [2], inv, fa, {})


def test_tiny_budget_is_resource_refused(tmp_path):
    r = O.run_plan(tmp_path, "tiny", "BASE", env(cpu=0.05), "A3_high", 1000)
    assert r["status"] == "RESOURCE_REFUSED" and r["budget_hit"] == "cpu" and r["all_workers_exited"]
    assert r["total_cpu_s"] >= 0.05


def test_ram_admission_refuses_before_start(tmp_path):
    r = O.run_plan(tmp_path, "ram", "AGG3", env(cores=(2, 4, 6), ram=256), "A2_bound", 100)
    assert r["status"] == "RESOURCE_REFUSED" and r["refusal"] == "RAM admission" and r["workers"] == []


def test_failed_first_attempt_then_budget_out_is_starvation(tmp_path):
    # AGG1 starts at L-16 = 125 for A3_high@1000 (true algebra minimum 127): the first pass fails, the retry is cut
    r = O.run_plan(tmp_path, "starve", "AGG1", env(cpu=3.6), "A3_high", 1000)
    assert r["status"] == "BUDGET_STARVATION", (r["status"], [p["outcome"] for w in r["workers"] for p in w["passes"]])


def test_duplicate_decided_candidates_accepted_once(tmp_path):
    r = O.run_plan(tmp_path, "dup", "SPEC_EVAL", env(cores=(2, 4)), "A2_bound", 100)
    assert r["status"] == "VERIFIED" and sum(w["accepted"] for w in r["workers"]) == 1
    acc = next(w for w in r["workers"] if w["accepted"])
    assert abs(r["waste_cpu_s"] - (r["total_cpu_s"] - acc["cpu_s"])) < 1e-9


def test_wrong_decided_claim_is_rejected_by_verifier(base_run):
    d, r = base_run
    p = copy.deepcopy(r["workers"][0]["passes"][-1])
    assert VF.verify(p, "A2_bound", 100)["verified"]
    p["cells"][0] += 1
    assert not VF.verify(p, "A2_bound", 100)["verified"]
    q = copy.deepcopy(r["workers"][0]["passes"][-1])
    q["completed_steps"] = 99
    assert not VF.verify(q, "A2_bound", 100)["verified"]
    assert not CK.my_verify(p, "A2_bound", 100)


def test_pair_parallel_reduction_is_bit_identical(tmp_path):
    out = tmp_path / "s4.json"
    subprocess.run([sys.executable, "-m", "experiments.resource_evolution_v1.pairloop", "A3_high", "20", "128", "3",
                    "2,4,6,8", str(out)], check=True, cwd=SEL.ROOT)
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["bit_identical"] and d["parallel"]["workers_exited"]


def test_neutral_cue_stays_neutral_and_reversal_learns():
    rw = SEL.RW()
    vis = {"cores": 6, "cpu_u": 50.0, "spec": 3, "ram_mb": 4096}
    for cues, pressure in SEL.schedule("T5"):
        plan, inp = rw.choose(vis, cues)
        assert plan == "AGG3" and set(inp) <= SEL.ALLOWED_SELECTOR_INPUTS
        rw.update(cues, pressure)
    assert rw.V.get("A", 0.0) == 0.0
    for cues, pressure in SEL.schedule("T6")[:16]:
        rw.update(cues, pressure)
    assert rw.choose(vis, ["A"])[0] == "CONS" and rw.choose(vis, [])[0] == "AGG3"
    for cues, pressure in SEL.schedule("T6")[16:] + SEL.schedule("T7A"):
        rw.update(cues, pressure)
    assert rw.choose(vis, ["A"])[0] == "AGG3"                        # extinction
    for cues, pressure in SEL.schedule("T7B"):
        rw.update(cues, pressure)
    assert rw.choose(vis, ["B"])[0] == "CONS" and rw.choose(vis, ["A"])[0] == "AGG3"   # reversal


def test_adaptive_never_exceeds_visible_cores_or_spec():
    for t in SEL.TIERS.values():
        vis = {"cores": t["cores"], "cpu_u": t["cpu_u"], "spec": t["spec"], "ram_mb": t["ram_mb"]}
        plan = SEL.adaptive(vis)
        assert len(SEL.PLANS[plan]["workers"]) <= min(vis["cores"], vis["spec"]) or not SEL.PLANS[plan]["spec"]


def test_latency_stats_refuse_tail_claims_from_few_samples():
    s = CK.lat([1.0] * 9 + [10.0])
    assert s["p95"] == "INSUFFICIENT_SAMPLES" and s["p99"] == "INSUFFICIENT_SAMPLES" and s["max"] == 10.0


def test_checker_and_verifier_import_no_executor_module():
    banned = ("worker", "orch", "selector", "vserver", "pairloop", "floatcand", "campaign", "adapter",
              "evaluator_adapter", "policies", "probe", "harness")
    for f, extra in (("checker.py", ("verifier",)), ("verifier.py", ())):
        tree = ast.parse((PKG / f).read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names.add(node.module or "")
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
        assert not any(n.split(".")[-1] in banned + extra for n in names), (f, names)


def test_cpu_figure_is_consistent_max_of_poll_and_self_report():
    """run-1 defect 2: a worker ending between the budget decision and the kill was booked with its self-report
    (which misses the interpreter start), so a CPU refusal was recorded below its budget."""
    import types
    fake = types.SimpleNamespace(cpu=0.38, end=lambda: {"child_cpu_s": 0.359})
    assert O.Worker.cpu_final(fake) == 0.38
    fake2 = types.SimpleNamespace(cpu=0.30, end=lambda: {"child_cpu_s": 0.359})
    assert O.Worker.cpu_final(fake2) == 0.359


def test_budget_stop_records_trigger_point_and_late_results(tmp_path):
    """run-1 defect 1: a DECIDED line read only after the stop decision must be recorded as a discarded late result,
    and the trigger point must be on the record so the checker can adjudicate."""
    r = O.run_plan(tmp_path, "trig", "AGG3", env(cores=(2, 4, 6), cpu=0.9), "A3_low", 100)
    if r["status"] != "VERIFIED":
        assert r["cpu_at_trigger"] >= 0.9 and r["total_cpu_s"] >= r["cpu_at_trigger"] - 1e-9
        assert "late_results_discarded" in r
