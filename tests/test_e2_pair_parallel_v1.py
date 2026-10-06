"""E2_PAIR_PARALLEL_V1: PAR_E1/PAR_E2 bit-identical to the unchanged serial paths, identical domain stops with E2
workers, and the sealed contamination rule shared by campaign and checker."""

import json
import subprocess
import sys
from fractions import Fraction as Q
from pathlib import Path

import psutil
import pytest

from experiments.e2_pair_parallel_v1 import campaign as CA
from experiments.e2_pair_parallel_v1 import checker as CK
from experiments.e2_pair_parallel_v1 import run as RUN
from experiments.multiatom_parallel_v1 import run as MARUN
from experiments.multiatom_parallel_v1 import scenarios as SC

ROOT = Path(__file__).resolve().parents[1]


def _sub(args, tmp_path, tag):
    out = tmp_path / f"{tag}.json"
    subprocess.run([sys.executable, "-m", *args, str(out)], cwd=ROOT, check=True)
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("ev", ["algebra", "rw:R1+R2"])
@pytest.mark.parametrize("n,T,w", [(4, 4, 3), (6, 3, 6)])
def test_parallel_bit_identical_to_serial_same_evaluator(tmp_path, ev, n, T, w):
    s = _sub(["experiments.multiatom_parallel_v1.run", "serial", ev, str(n), str(T), "128", "2"], tmp_path, "s")
    cpus = ",".join(str(c) for c in [2, 4, 6, 8, 10, 0][:w])
    p = _sub(["experiments.e2_pair_parallel_v1.run", ev, str(n), str(T), "128", str(w), "1", cpus], tmp_path, "p")
    for k in ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells", "initial_sha256"):
        assert p[k] == s[k], k
    assert p["workers_exited"] == [0] * w
    assert {h["evaluator"] for h in p["worker_hello"]} == {ev}
    assert {h["force_type"] for h in p["worker_hello"]} == {CK.FORCE_TYPE[ev]}


def test_domain_stop_identical_with_e2_workers(monkeypatch):
    q0 = [[Q(0), Q(0), Q(0)], [Q(10), Q(0), Q(0)], [Q(12), Q(0), Q(0)]]     # pair (1,2) at 2 bohr < r_min
    p0 = [[Q(0)] * 3 for _ in range(3)]
    monkeypatch.setattr(SC, "initial", lambda n: (q0, p0))
    me = psutil.Process()
    keep = me.cpu_affinity()
    try:
        s = MARUN.run_serial("rw:R1+R2", 3, 4, 128, keep[0])
        p = RUN.run_parallel("rw:R1+R2", 3, 4, 128, 2, keep[0], [keep[0], keep[-1]])
    finally:
        me.cpu_affinity(keep)
    assert s["stop"] == "VIOLATED" and s["stop_step"] == 0
    for k in ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells"):
        assert p[k] == s[k], k


@pytest.mark.parametrize("rows,expect", [
    ([("dwm.exe", 1, 60.0), ("System", 4, 30.0)], False),
    ([("dwm.exe", 1, 60.0), ("System", 4, 45.0)], True),
    ([("RobloxPlayerBeta.exe", 9, 26.0)], True),
    ([("python.exe", 9, 24.9)], False),
    ([("python.exe", 9, 25.0)], True),
    ([("Codex.exe", 9, 30.0)], True),
    ([], False),
])
def test_contamination_rule_campaign_equals_checker(rows, expect):
    assert CA.contamination(rows)["contaminated"] is expect
    assert CK.my_contaminated(rows) is expect


def test_configs_and_commands():
    c = CA.Camp.__new__(CA.Camp)
    c.m = CA.PROTO["machines"]["laptop"]
    assert CA.CONFIGS == CK.CONFIGS
    cmd = c.command("PAR_E2_W6", 12, 100, "o")
    assert cmd[3:] == ["rw:R1+R2", "12", "100", "128", "6", "0", "1,2,3,4,5,0", "o"]
    cmd = c.command("SER_E2", 12, 100, "o")
    assert cmd[2:] == ["experiments.multiatom_parallel_v1.run", "serial", "rw:R1+R2", "12", "100", "128", "1", "o"]
