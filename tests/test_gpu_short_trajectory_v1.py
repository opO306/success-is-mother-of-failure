"""GPU_SHORT_TRAJECTORY_V1: the checker's own trajectory equals the sealed bundle (the stream.run replica), and the
sixteen fault injections the independent checker must detect, with the first divergence where it was injected.
Fixture: N12_p163_s0 at T = 10 and the p = 109 probes (multi-step stops). Skips without a CUDA toolchain / device."""

import pytest

from a_numeric_native import harness as H
from experiments.gpu_short_trajectory_v1 import checker as CK

GPU = pytest.mark.skipif(not H.have_gpu_toolchain(), reason="CUDA toolchain or device missing")


@pytest.fixture(scope="module")
def bundle():
    import gzip
    import json
    return json.loads(gzip.decompress(CK.BUNDLE.read_bytes()))


@pytest.fixture(scope="module")
def fix(bundle):
    main = [t for t in bundle["main"] if t["id"] == "N12_p163_s0"]
    probes = [t for t in bundle["probes"] if t["p"] == 109]
    return main, probes


def test_checker_independent_of_runner():
    src = open(CK.__file__, encoding="utf-8").read()
    for mod in ("traj", "campaign", "one_step", "pv_host", "gpu_host"):
        assert f"import {mod}" not in src


def test_own_trajectories_equal_bundle(fix):
    main, probes = fix
    for t in main + probes:
        _, _, o = CK._own_task((t, 10, []))
        assert o["steps"] == t["steps"][:10], t["id"]
        assert (o["stop"] or {"status": "OK", "stop_state": None, "stop_pair": None}) == t["cpu_outcome"], t["id"]
        assert o["initial"]["q"] == CK._rows(t["q0"]) and o["initial"]["p_mom"] == CK._rows(t["p0"])
    kinds = {(t["role"], t["cpu_outcome"]["status"], t["cpu_outcome"]["stop_state"], t["cpu_outcome"]["stop_pair"])
             for t in probes}
    assert ("N12_MULTI_PAIR", "DOMAIN_STOP_VIOLATED", 7, 30) in kinds
    assert {k[1] for k in kinds} == {"DOMAIN_STOP_VIOLATED", "DOMAIN_STOP_UNPROVEN"}


@pytest.fixture(scope="module")
def ex(tmp_path_factory):
    if not H.have_gpu_toolchain():
        pytest.skip("CUDA toolchain or device missing")
    from experiments.gpu_pair_vector_v1 import pv_host as PH
    from experiments.gpu_short_trajectory_v1 import traj as TR
    lib, arch, log = PH.build(tmp_path_factory.mktemp("stbuild"))
    e = TR.TrajExecutor(lib, block=32)
    yield e
    e.pv.lib.pv_free()


def _ev(tmp_path, ex, fix, blocks=(32,), main_only=False, probes_only=False, **kw):
    from experiments.gpu_short_trajectory_v1 import campaign as CA
    main, probes = fix
    d = tmp_path / "ev"
    for t in ([] if probes_only else main):
        for b in blocks:
            CA.run_one(ex, d, t, 10, b, **kw)
    for t in ([] if main_only else probes):
        CA.run_one(ex, d, t, 10, 32, **kw)
    return CK.check(d, expect_complete=False)


def _failed(v, name):
    return v["counts"].get(name, [0, 0])[1] > 0


def _fd(v, traj="N12_p163_s0"):
    return next(x for x in v["first_divergence"] if x["traj"] == traj)


@GPU
def test_clean_fixture_exact(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, blocks=(32, 64, 128, 256))
    assert v["verdict"] == "EVIDENCE OK", v["issues"]
    s = v["stats"]
    assert s["traj_mismatch"] == s["stops_mismatch"] == s["steps_mismatch"] == 0
    assert s["traj_exact"] == 4 and s["stops_exact"] == 4


@GPU
@pytest.mark.parametrize("fault,check,stage", [
    (1, "per_step_digests_equal", "F_s"), (3, "per_step_digests_equal", "F1"), (5, "per_step_digests_equal", "p1"),
    (6, "per_step_digests_equal", "p_half"), (7, "per_step_digests_equal", "q1"), (8, "per_step_digests_equal", "F1"),
    (16, "per_step_digests_equal", "F1")])
def test_step3_faults(ex, fix, tmp_path, fault, check, stage):
    v = _ev(tmp_path, ex, fix, main_only=True, fault=fault)
    assert _failed(v, check)
    fd = _fd(v)
    assert (fd["first_divergence_step"], fd["first_divergence_stage"]) == (3, stage), fd
    assert "atom" in fd, fd                                    # the runner's dump located the endpoint


@GPU
@pytest.mark.parametrize("fault,stage", [(10, "q1"), (11, "p1"), (12, "F1")])
def test_one_ulp_faults_located(ex, fix, tmp_path, fault, stage):
    fd = _fd(_ev(tmp_path, ex, fix, main_only=True, fault=fault))
    assert (fd["first_divergence_step"], fd["first_divergence_stage"], fd["atom"], fd["component"], fd["end"]) == \
        (3, stage, 0, "x", "upper"), fd
    assert fd["cpu"] != fd["gpu"]


@GPU
def test_2_force_recomputed_instead_of_reused(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, main_only=True, fault=2)
    assert _failed(v, "force_evaluations_reuse")
    assert not _failed(v, "per_step_digests_equal")            # values identical by determinism (disclosed)


@GPU
def test_4_step_label_skipped(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, main_only=True, fault=4)
    assert _failed(v, "step_indices_contiguous") and _failed(v, "per_step_digests_equal")


@GPU
def test_9_precision_changed_after_step_5(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, main_only=True, fault=9)
    assert _failed(v, "executor_persistent_in_trajectory")
    fd = _fd(v)
    assert (fd["first_divergence_step"], fd["first_divergence_stage"]) == (5, "F1"), fd


@GPU
def test_13_continue_after_stop(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, probes_only=True, fault=13)
    assert _failed(v, "step_count_equal") and _failed(v, "completed_steps_equal")
    assert v["stats"]["stops_mismatch"] > 0


@GPU
def test_14_digest_order_changed(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, main_only=True, fault=14)
    assert _failed(v, "digest_self_consistent") and _failed(v, "per_step_digests_equal")
    fd = _fd(v)
    assert fd["first_divergence_step"] == 0 and fd.get("note", "").startswith("endpoints equal"), fd


@GPU
def test_15_block_dependent_branch(ex, fix, tmp_path):
    v = _ev(tmp_path, ex, fix, blocks=(32, 64), main_only=True, fault=15)
    assert _failed(v, "layouts_identical")
    fd = _fd(v)
    assert (fd["first_divergence_step"], fd["first_divergence_stage"]) == (2, "F1"), fd


@GPU
def test_refusals_are_not_mismatches(ex, fix, tmp_path):
    from experiments.gpu_short_trajectory_v1 import campaign as CA
    main, _ = fix
    d = tmp_path / "ev"
    r = CA.run_one(ex, d, main[0], 10, 32, p=100, kind="REFUSAL")
    assert r["status"] == "REFUSED_DEVICE_PRECISION" and r["steps"] == [] and r["read"] is None
    v = CK.check(d, expect_complete=False)
    assert v["verdict"] == "EVIDENCE OK" and v["stats"]["refused"] == 1, v["issues"]
    w = CA.run_one(ex, tmp_path / "w", main[0], 10, 32, wl=8)        # a device width refusal: a status, not physics
    assert w["status"].startswith("REFUSED") and w["read"] is None and w["stop_state"] == 0
