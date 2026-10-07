"""GPU_ONE_STEP_V1: the checker's own step equals the recorded real next state, and the fourteen fault injections the
independent checker must detect. Fixture: the N = 12 states (p = 163), the N = 40 s = 10 state (p = 109) and the domain
probes at p = 109. Skips without a CUDA toolchain / device."""

import pytest

from a_numeric_native import harness as H
from experiments.gpu_one_step_v1 import campaign as CA
from experiments.gpu_one_step_v1 import checker as CK

GPU = pytest.mark.skipif(not H.have_gpu_toolchain(), reason="CUDA toolchain or device missing")


@pytest.fixture(scope="module")
def bundle():
    return CA.load_bundle()


@pytest.fixture(scope="module")
def fix(bundle):
    main = [x for x in bundle["main"] if x["N"] == 12 or (x["N"], x["step"]) == (40, 10)]
    probes = [x for x in bundle["test_only"] if x["p"] == 109]
    return [("main", x) for x in main] + [("test", x) for x in probes]


def test_own_step_equals_recorded_next_state(bundle):
    for x in [y for y in bundle["main"] if y["N"] == 12][:2]:
        o = CK.my_step(CK._rows(x["q"]), CK._rows(x["p_mom"]), x["p"])
        assert o["status"] == "OK" and o["F0"] == CK._rows(x["F"])
        assert (o["q1"], o["p1"], o["F1"]) == (CK._rows(x["next_q"]), CK._rows(x["next_p_mom"]), CK._rows(x["next_F"]))


def test_probe_outcomes(bundle):
    seen = set()
    for x in bundle["test_only"]:
        o = CK.my_step(CK._rows(x["q"]), CK._rows(x["p_mom"]), x["p"])
        stage, kind, pid = x["cpu_outcome"]
        assert (o["status"], o["stop_stage"], o["stop_pair"]) == \
            (("OK", None, None) if stage == "OK" else ("DOMAIN_STOP_" + kind, stage, pid))
        seen.add(x["role"])
    assert seen == {"PROBE_NORMAL", "PROBE_F0_VIOLATED", "PROBE_F1_VIOLATED", "PROBE_F1_UNPROVEN"}


@pytest.fixture(scope="module")
def ex(tmp_path_factory):
    if not H.have_gpu_toolchain():
        pytest.skip("CUDA toolchain or device missing")
    from experiments.gpu_one_step_v1 import one_step as OS
    from experiments.gpu_pair_vector_v1 import pv_host as PH
    lib, arch, log = PH.build(tmp_path_factory.mktemp("osbuild"))
    e = OS.GpuForceExecutor(lib, block=32)
    yield e
    e.pv.lib.pv_free()


def _ev(tmp_path, ex, fix, blocks=(32,), **kw):
    d = tmp_path / "ev"
    for kind, st in fix:
        for b in blocks:
            CA.run_one(ex, d, kind, st, b, 0, **kw)
    return CK.check(d, expect_layouts=False)


def _failed(v, name):
    return v["counts"].get(name, [0, 0])[1] > 0


@GPU
def test_clean_fixture_exact(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, blocks=(32, 64, 128, 256))
    assert v["verdict"] == "EVIDENCE OK", v["issues"]
    assert v["stats"]["steps_mismatch"] == v["stats"]["stops_mismatch"] == 0
    assert v["stats"]["stops_exact"] > 0 and v["stats"]["steps_exact"] > 0


@GPU
@pytest.mark.parametrize("fault,check", [(1, "C1_F0"), (2, "C2_p_half"), (3, "C2_p_half"), (4, "C3_q1"), (5, "C3_q1"),
                                         (6, "C4_F1"), (7, "C5_p1"), (8, "C4_F1"),
                                         (9, "C0_runner_inputs_equal_bundle"), (10, "C0_runner_inputs_equal_bundle"),
                                         (11, "C4_F1"), (13, "C1_F0")])
def test_runner_faults(ex, fix, tmp_path, fault, check):
    assert _failed(_ev(tmp_path, ex, fix, fault=fault), check)


@GPU
def test_12_precision_altered(ex, fix, tmp_path):
    d = tmp_path / "ev"
    for kind, st in fix:
        if st["p"] == 109:
            CA.run_one(ex, d, kind, st, 32, 0, upload_p=128)
    v = CK.check(d, expect_layouts=False)
    assert _failed(v, "C1_F0") or _failed(v, "status_equal")


@GPU
def test_14_layout_dependent_result(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, blocks=(32, 64, 128), pvfault=11)
    assert _failed(v, "layouts_identical") or _failed(v, "C1_F0")


def test_checker_independent_of_runner():
    src = open(CK.__file__, encoding="utf-8").read()
    for mod in ("one_step", "campaign", "pv_host", "gpu_host"):
        assert f"import {mod}" not in src
