"""W5_PLACEMENT_V1: ExecutionPlan validation and dispatch, bit identity of dedicated/shared placements through the
plan path, the sealed topology guard, and the shared contamination rule."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.w5_placement_v1 import campaign as CA
from experiments.w5_placement_v1 import checker as CK
from experiments.w5_placement_v1.plan import ExecutionPlan, execute

ROOT = Path(__file__).resolve().parents[1]


def test_plan_validation_and_roundtrip():
    p = ExecutionPlan("rw:R1+R2", 128, "CPU_PARALLEL", 5, 0, (1, 2, 3, 4, 5)).validate(logical_cpus=6)
    assert not p.shares_main_core()
    assert ExecutionPlan.from_json(p.to_json()) == p
    assert ExecutionPlan("rw:R1+R2", 128, "CPU_PARALLEL", 6, 0, (1, 2, 3, 4, 5, 0)).validate(6).shares_main_core()
    for bad in [ExecutionPlan("rw:R1+R2", 128, "CPU_PARALLEL", 5, 0, (1, 2, 3, 4)),        # count mismatch
                ExecutionPlan("rw:R1+R2", 128, "CPU_PARALLEL", 2, 0, (1, 1)),               # CPU used twice
                ExecutionPlan("rw:R1+R2", 128, "CPU_SERIAL", 1, 0, (1,)),                   # serial with workers
                ExecutionPlan("float64", 128, "CPU_SERIAL", 0, 0, ()),                      # unknown evaluator
                ExecutionPlan("rw:R1+R2", 128, "FPGA", 0, 0, ())]:                          # unknown backend
        with pytest.raises(ValueError):
            bad.validate()
    with pytest.raises(ValueError):
        ExecutionPlan("rw:R1+R2", 128, "CPU_PARALLEL", 1, 0, (6,)).validate(logical_cpus=6)


def test_gpu_backend_is_reserved_only():
    p = ExecutionPlan("rw:R1+R2", 128, "GPU", 0, 0, ()).validate()
    with pytest.raises(NotImplementedError):
        execute(p, 3, 1)


def _run(plan, n, T, tmp_path, tag):
    pf, out = tmp_path / f"{tag}.plan.json", tmp_path / f"{tag}.json"
    pf.write_text(plan.to_json(), encoding="utf-8")
    subprocess.run([sys.executable, "-m", "experiments.w5_placement_v1.run", str(pf), str(n), str(T), str(out)],
                   cwd=ROOT, check=True)
    return json.loads(out.read_text(encoding="utf-8"))


def test_dedicated_and_shared_placements_bit_identical_to_serial(tmp_path):
    s = _run(ExecutionPlan("rw:R1+R2", 128, "CPU_SERIAL", 0, 2, ()), 6, 3, tmp_path, "s")
    dedicated = _run(ExecutionPlan("rw:R1+R2", 128, "CPU_PARALLEL", 5, 1, (2, 4, 6, 8, 10)), 6, 3, tmp_path, "w5")
    shared = _run(ExecutionPlan("rw:R1+R2", 128, "CPU_PARALLEL", 6, 1, (2, 4, 6, 8, 10, 1)), 6, 3, tmp_path, "w6")
    for r in (dedicated, shared):
        for k in CK.RESULT_KEYS:
            assert r[k] == s[k], k
        assert r["plan"]["backend"] == "CPU_PARALLEL" and r["workers_exited"] == [0] * r["plan"]["worker_count"]
    assert s["plan"]["backend"] == "CPU_SERIAL"


def test_topology_guard():
    good = {"logical": 6, "physical": 6, "cores": [{"smt": False, "group_cpus": [[0, [k]]]} for k in range(6)]}
    assert CA.expected_topology_ok(good)
    smt = {"logical": 12, "physical": 6, "cores": [{"smt": True, "group_cpus": [[0, [2 * k, 2 * k + 1]]]} for k in range(6)]}
    assert not CA.expected_topology_ok(smt)
    swapped = json.loads(json.dumps(good))
    swapped["cores"][0]["group_cpus"] = [[0, [1]]]
    assert not CA.expected_topology_ok(swapped)


def test_sealed_plans_match_protocol():
    for cfg in CA.CONFIGS:
        p = CA.plan_for(cfg).validate(logical_cpus=6)
        c = CA.PROTO["configurations"][cfg]
        assert (p.backend, p.worker_count, p.main_cpu, list(p.worker_cpus)) == \
            (c["backend"], c["worker_count"], c["main_cpu"], c["worker_cpus"])
    assert CA.plan_for("W6_SHARED").shares_main_core() and not CA.plan_for("W5_DEDICATED").shares_main_core()


@pytest.mark.parametrize("rows,expect", [([("dwm.exe", 1, 60.0), ("System", 4, 45.0)], True),
                                         ([("python.exe", 9, 24.9)], False), ([("Codex.exe", 9, 30.0)], True)])
def test_contamination_rule_shared(rows, expect):
    assert CA.contamination(rows)["contaminated"] is expect
    assert CK.my_contaminated(rows) is expect
