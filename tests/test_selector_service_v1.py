"""SELECTOR_SERVICE_V1: selector rule and domain, service loop with P2, refusals, and the eight fault injections the
independent checker must detect (on a small real evidence directory)."""

import copy
import json
import shutil
from pathlib import Path

import psutil
import pytest

from experiments.precision_pilot_a1 import policies as POL
from experiments.selector_service_v1 import campaign as CA
from experiments.selector_service_v1 import checker as CK
from experiments.selector_service_v1 import selector as SEL
from experiments.selector_service_v1 import service as SV

LAPTOP = {"logical": 6, "physical": 6, "cores": [{"smt": False, "group_cpus": [[0, [k]]]} for k in range(6)]}
DESKTOP = {"logical": 12, "physical": 6, "cores": [{"smt": True, "group_cpus": [[0, [2 * k, 2 * k + 1]]]} for k in range(6)]}


def _inp(N, T, p=64, goal="WALL_MIN", topo=LAPTOP):
    return SEL.SelectorInput(N=N, T=T, p=p, goal=goal, topology=SEL.topology_input(topo))


@pytest.mark.parametrize("N,T,w", [(2, 100, 0), (4, 100, 0), (5, 100, 4), (11, 100, 4), (12, 100, 6), (32, 100, 6),
                                   (3, 1000, 3), (4, 1000, 6), (8, 1000, 6)])
def test_rule_table_and_p_independence(N, T, w):
    for p in (64, 97, 128, 300, 1024):
        plan = SEL.select(_inp(N, T, p))
        assert plan.worker_count == w and plan.precision == p and plan.evaluator == "rw:R1+R2"
        assert CK.my_plan(N, T, p, "WALL_MIN") == json.loads(plan.to_json())
    assert SEL.select(_inp(N, T, goal="CPU_MIN")).backend == "CPU_SERIAL"


@pytest.mark.parametrize("inp", [_inp(5, 500), _inp(5, 200), _inp(2, 1000), _inp(1, 100), _inp(5, 100, topo=DESKTOP),
                                 _inp(5, 100, goal="FASTEST")])
def test_selector_domain_refusals(inp):
    with pytest.raises(SEL.UnsupportedSelectorDomain):
        SEL.select(inp)


def test_selector_accepts_only_selector_input():
    with pytest.raises(TypeError):
        SEL.select({"N": 5, "T": 100, "p": 64, "goal": "WALL_MIN", "topology": None, "outcome": "DECIDED"})
    assert set(_inp(5, 100).as_record()) == CK.ALLOWED_SELECTOR_KEYS


def _fake_executor(outcomes):
    """Returns pass records with the given outcome sequence (UNDECIDED records carry no endpoints)."""
    it = iter(outcomes)

    def ex(plan, N, T):
        o = next(it)
        return {"outcome": o, "completed_steps": T, "endpoints_scaled": None, "effective_p": plan.precision}
    return ex


def test_service_follows_p2_and_stops():
    res = SV.run_request(5, 100, "SELECTOR", LAPTOP, _fake_executor(["UNDECIDED_AT_PRECISION"] * 3 + ["DECIDED"]),
                         goal="WALL_MIN")
    hist, seq = [], []
    for o in ["UNDECIDED_AT_PRECISION"] * 3 + ["DECIDED"]:
        p = POL.next_p("P2", None, hist, 100)
        seq.append(p)
        hist.append({"requested_p": p, "outcome": o, "completed_steps": 100, "endpoints_scaled": None})
    assert res["status"] == "DECIDED" and res["p_sequence"] == seq and res["final_p"] == seq[-1]
    assert all(set(x["selector_input"]) == CK.ALLOWED_SELECTOR_KEYS for x in res["passes"])


def test_service_cap_and_stop():
    res = SV.run_request(5, 100, "FIXED:SERIAL", LAPTOP, _fake_executor(["UNDECIDED_AT_PRECISION"] * 30))
    assert res["status"] == "REFUSED_AT_CAP" and res["p_sequence"][-1] == 1024
    res = SV.run_request(5, 100, "FIXED:SERIAL", LAPTOP, _fake_executor(["DOMAIN_VIOLATED_PROVEN"]))
    assert res["status"] == "STOP_DOMAIN_VIOLATED_PROVEN" and res["n_passes"] == 1


def test_probes_execute_nothing():
    def boom(plan, N, T):
        raise AssertionError("executed")
    assert SV.run_request(5, 500, "SELECTOR", LAPTOP, boom, goal="WALL_MIN")["status"] == "UNSUPPORTED_SELECTOR_DOMAIN"
    assert SV.run_request(5, 500, "FIXED:W6", LAPTOP, boom)["status"] == "UNSUPPORTED_SELECTOR_DOMAIN"
    r = SV.run_request(5, 100, "FIXED:GPU", LAPTOP, boom)
    assert r["status"] == "REFUSED_BACKEND_NOT_IMPLEMENTED" and r["n_passes"] == 0


# ---------------- fault injection on a real small evidence directory ----------------
REQ, REPS = [(5, 100)], 1


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    d = tmp_path_factory.mktemp("sel_ev")
    me = psutil.Process()
    keep = me.cpu_affinity()
    try:
        c = CA.Camp(d)
        c.setup(check_topology=False)
        c.topology = LAPTOP                                    # selector input = the laptop map; CPUs 0..5 exist here
        CA.probes(c)
        c.snapshot("N5_T100__r0")
        seqs = {}
        for label, strategy, goal in CA.STRATEGIES:
            seqs[label] = c.service(f"N5_T100__{label}__r0", 5, 100, strategy, goal)["p_sequence"]
        for p in seqs["SEL_WALL"]:
            for kind in ("W3", "W4"):
                c.shadow(f"N5_T100__p{p}__{kind}__r0", 5, 100, kind, p)
    finally:
        me.cpu_affinity(keep)
    return d


def _failed(d, name):
    v = CK.check(d, requests=REQ, reps=REPS)
    return v["counts"].get(name, [0, 0])[1] > 0, v


def _copy(evidence, tmp_path):
    d = tmp_path / "ev"
    shutil.copytree(evidence, d)
    return d


def _edit(path, fn):
    s = json.loads(path.read_text(encoding="utf-8"))
    fn(s)
    path.write_text(json.dumps(s), encoding="utf-8")


def test_clean_evidence_passes_everything_but_the_dirty_seal(evidence):
    v = CK.check(evidence, requests=REQ, reps=REPS)
    bad = {k for k, c in v["counts"].items() if c[1]}
    assert bad <= {"seal_clean"}, v["issues"]
    assert v["bit_mismatches"] == 0


def test_inject_future_outcome_in_selector_input(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "service/N5_T100__SEL_WALL__r0.json", lambda s: s["passes"][0]["selector_input"].update(outcome="DECIDED"))
    assert _failed(d, "selector_input_allowed_keys_only")[0]


def test_inject_true_min_p_in_selector_input(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "service/N5_T100__SEL_WALL__r0.json", lambda s: s["passes"][0]["selector_input"].update(min_p=96))
    assert _failed(d, "selector_input_allowed_keys_only")[0]


def test_inject_changed_p2_next_p(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        last = s["passes"][-1]
        last["p"] += 7
    _edit(d / "service/N5_T100__SEL_CPU__r0.json", f)
    assert _failed(d, "p2_rederived")[0]


def test_inject_worker_count(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        s["passes"][0]["plan"]["worker_count"] = 6
    _edit(d / "service/N5_T100__SEL_WALL__r0.json", f)
    bad, v = _failed(d, "plan_rederived")
    assert bad and v["counts"]["pass_plan_shape"][1] > 0


def test_inject_endpoint(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        k = s["passes"][-1]["record"]["endpoints_key"]
        s["passes"][-1]["record"]["endpoints_key"] = k[:-2] + ("1" if k[-2] != "1" else "2") + k[-1]
    _edit(d / "service/N5_T100__FIXED_W6__r0.json", f)
    assert _failed(d, "bit_identical_to_serial")[0]


def test_inject_deleted_middle_pass(evidence, tmp_path):
    d = _copy(evidence, tmp_path)

    def f(s):
        i = len(s["passes"]) // 2 if len(s["passes"]) >= 2 else 0
        del s["passes"][i]
        for j, pz in enumerate(s["passes"]):
            pz["index"] = j
        s["p_sequence"] = [pz["p"] for pz in s["passes"]]
        s["n_passes"] = len(s["passes"])
    _edit(d / "service/N5_T100__SEL_WALL__r0.json", f)
    bad1, v = _failed(d, "p2_rederived")
    assert bad1 or v["counts"]["final_status"][1] > 0 or v["counts"]["same_p_sequence_all_strategies"][1] > 0


def test_inject_unsupported_T_executed(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    passes = json.loads((d / "service/N5_T100__SEL_CPU__r0.json").read_text(encoding="utf-8"))["passes"]

    def f(s):
        s["status"], s["passes"], s["n_passes"] = "DECIDED", copy.deepcopy(passes[:1]), 1
    _edit(d / "probes/unsupported_T500_SEL_WALL.json", f)
    assert _failed(d, "probe_unsupported_T_refused")[0]
    s = json.loads((d / "service/N5_T100__SEL_CPU__r0.json").read_text(encoding="utf-8"))
    s["T"] = 500
    (d / "service/N5_T500__sneak.json").write_text(json.dumps(s), encoding="utf-8")
    assert _failed(d, "no_unsupported_or_gpu_pass_anywhere")[0]


def test_inject_gpu_success(evidence, tmp_path):
    d = _copy(evidence, tmp_path)
    _edit(d / "probes/gpu_plan_N5_T100.json", lambda s: s.update(status="DECIDED"))
    assert _failed(d, "probe_gpu_refused")[0]
    d2 = _copy(evidence, tmp_path / "b")
    _edit(d2 / "service/N5_T100__FIXED_W6__r0.json", lambda s: s["passes"][0]["plan"].update(backend="GPU"))
    assert _failed(d2, "pass_backend_cpu")[0]
