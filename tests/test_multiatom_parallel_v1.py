"""MULTIATOM_PARALLEL_V1: scenario rule, pair partition, independent regeneration, serial/parallel bit identity through
the real entry points, and identical domain stops (first non-PROVEN pair in canonical order)."""

import json
import subprocess
import sys
from fractions import Fraction as Q
from pathlib import Path

import psutil
import pytest

from experiments.multiatom_parallel_v1 import checker as CH
from experiments.multiatom_parallel_v1 import run as RUN
from experiments.multiatom_parallel_v1 import scenarios as SC

ROOT = Path(__file__).resolve().parents[1]
N_LIST = [2, 3, 4, 6, 8, 12, 16, 24, 32, 48]


@pytest.mark.parametrize("n", N_LIST)
def test_independent_regeneration_and_zero_momentum(n):
    q0, p0 = SC.initial(n)
    assert RUN.initial_digest(q0, p0) == CH.my_digest(*CH.my_initial(n))
    assert all(sum(p0[i][k] for i in range(n)) == 0 for k in range(3))
    assert len({tuple(r) for r in q0}) == n


@pytest.mark.parametrize("n,w", [(2, 1), (3, 2), (8, 6), (12, 4), (48, 6), (4, 6)])
def test_pair_blocks_partition(n, w):
    blocks = SC.pair_blocks(n, w)
    flat = [p for b in blocks for p in b]
    assert flat == [(i, j) for i in range(n) for j in range(i + 1, n)]
    sizes = [len(b) for b in blocks]
    assert len(blocks) == w and max(sizes) - min(sizes) <= 1


def _run(args, tmp_path, tag):
    out = tmp_path / f"{tag}.json"
    subprocess.run([sys.executable, "-m", "experiments.multiatom_parallel_v1.run", *args, str(out)], cwd=ROOT,
                   check=True)
    return json.loads(out.read_text(encoding="utf-8"))


@pytest.mark.parametrize("n,T,ws", [(3, 6, (1, 2)), (6, 3, (4,))])
def test_parallel_bit_identical_to_repository_loop(tmp_path, n, T, ws):
    s = _run(["serial", "algebra", str(n), str(T), "128", "2"], tmp_path, "s")
    assert s["force_swap_restored"] is True and s["completed_steps"] == T
    for w in ws:
        cpus = ",".join(str(c) for c in [2, 4, 6, 8, 10, 0][:w])
        p = _run(["parallel", str(n), str(T), "128", str(w), "1", cpus], tmp_path, f"p{w}")
        for k in ("outcome", "completed_steps", "stop", "endpoints_key", "cells"):
            assert p[k] == s[k], k
        assert p["workers_exited"] == [0] * w and p["initial_sha256"] == s["initial_sha256"]


def _close_state(n=3):
    # pairs (0,1), (0,2) far apart; pair (1,2) is 2 bohr (< r_min 2.27), last in canonical order -> VIOLATED at step 0
    q0 = [[Q(0), Q(0), Q(0)], [Q(10), Q(0), Q(0)], [Q(12), Q(0), Q(0)]]
    p0 = [[Q(0)] * 3 for _ in range(n)]
    return q0, p0


def test_domain_stop_identical(monkeypatch):
    me = psutil.Process()
    keep = me.cpu_affinity()
    monkeypatch.setattr(SC, "initial", lambda n: _close_state(n))
    try:
        s = RUN.run_serial("algebra", 3, 4, 128, keep[0])
        p = RUN.run_parallel(3, 4, 128, 2, keep[0], [keep[0], keep[-1]])
    finally:
        me.cpu_affinity(keep)
    assert s["stop"] == "VIOLATED" and s["stop_step"] == 0 and s["completed_steps"] == 0
    for k in ("outcome", "completed_steps", "stop", "stop_step", "endpoints_key", "cells"):
        assert p[k] == s[k], k
    assert p["workers_exited"] == [0, 0]


def test_cycle_counter_counts_busy_time():
    rate = RUN.cycle_rate(trials=5, ms=30)
    c0, w0 = RUN.cycles(), __import__("time").perf_counter()
    x = 0
    while __import__("time").perf_counter() - w0 < 0.2:
        x += 1
    secs = (RUN.cycles() - c0) / rate
    assert 0.15 < secs < 0.3
