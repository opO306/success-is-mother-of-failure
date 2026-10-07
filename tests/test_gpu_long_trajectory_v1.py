"""GPU_LONG_TRAJECTORY_V1: gate P (new precisions, precision disguise), fixed-p T1000 passes, the long domain stop, the
GPU P2 service (restart from the original state, explicit CPU fallback) and the 18 + 2 fault injections the independent
checker must detect. Fixture: N = 12 only (p 64, 73, 161, 163; the checker's own passes are computed once, in
parallel). Slow (about 10 min on the desktop). Skips without a CUDA toolchain / device."""

import gzip
import json
from concurrent.futures import ProcessPoolExecutor

import pytest

from a_numeric_native import harness as H
from experiments.gpu_long_trajectory_v1 import checker as CK

GPU = pytest.mark.skipif(not H.have_gpu_toolchain(), reason="CUDA toolchain or device missing")
SUPPORT = {64, 73, 78, 109, 128, 161, 163, 166, 192}


@pytest.fixture(scope="module")
def bundle():
    return json.loads(gzip.decompress(CK.BUNDLE.read_bytes()))


@pytest.fixture(scope="module")
def own():
    # kept vectors at every step a fault test dumps (so the checker never recomputes a pass)
    tasks = [(12, 64, (500, 995)), (12, 73, (0,)), (12, 161, ()), (12, 163, (2, 500))]
    with ProcessPoolExecutor(4) as pool:
        for (N, p), o in pool.map(CK._own_task, tasks):
            CK._OWN[(N, p, next(k for n, q, k in tasks if (n, q) == (N, p)))] = o
    return CK._OWN


def test_checker_independent_of_runner():
    src = open(CK.__file__, encoding="utf-8").read()
    for mod in ("long", "campaign", "support", "traj", "one_step", "pv_host", "gpu_host", "policies"):
        assert f"import {mod}" not in src and f"import {mod} " not in src


def test_own_passes_equal_bundle_v2_and_p2(own, bundle):
    from experiments.precision_pilot_a1 import policies as POL
    tr = {(t["N"], t["p"]): t for t in bundle["trajectories"]}
    for p in (64, 73, 161, 163):
        o = CK._own_task((12, p, ()))[1]
        t = tr[(12, p)]
        assert o["steps"] == t["steps"] and o["stop"] == t["stop"]
        ref = CK.v2_reference(12, p)
        for k in ("outcome", "completed_steps", "stop", "stop_step", "cells", "endpoints_key"):
            assert o["record"][k] == ref[k], (p, k)
    assert CK._own_task((12, 64, ()))[1]["stop"] == {"status": "DOMAIN_STOP_UNPROVEN", "stop_state": 996, "stop_pair": 0}
    for p, nxt in ((64, 73), (73, 161)):                     # the checker's own P2 = the frozen P2 = V2's sequence
        r = {"requested_p": p, **CK._own_task((12, p, ()))[1]["record"]}
        assert CK.my_p2(r) == POL.p2_next(r, 1000) == nxt
    assert CK.own_service(12, "BASE64", lambda n, p: CK._own_task((n, p, ()))[1]) == ([64, 73, 161], "DECIDED")


@pytest.fixture(scope="module")
def ex(tmp_path_factory):
    if not H.have_gpu_toolchain():
        pytest.skip("CUDA toolchain or device missing")
    from experiments.gpu_long_trajectory_v1 import long as LG
    from experiments.gpu_pair_vector_v1 import pv_host as PH
    lib, arch, log = PH.build(tmp_path_factory.mktemp("ltbuild"))
    e = LG.LongExecutor(lib, block=32)
    yield e
    e.pv.lib.pv_free()


def _failed(v, name):
    return v["counts"].get(name, [0, 0])[1] > 0


def _fixed(tmp_path, ex, bundle, p, blocks=(32,), fault=0):
    from experiments.gpu_long_trajectory_v1 import campaign as CA
    t = next(x for x in bundle["trajectories"] if (x["N"], x["p"]) == (12, p))
    d = tmp_path / "ev"
    for b in blocks:
        CA.fixed_one(ex, d, t, b, fault=fault)
    return CK.check(d, phase="fixed", expect_complete=False, support_override=sorted(SUPPORT))


def _service(tmp_path, ex, bundle, policy="BASE64", support=SUPPORT, fault=0, **kw):
    from experiments.gpu_long_trajectory_v1 import campaign as CA
    d = tmp_path / "ev"
    CA.service_one(ex, d, bundle, 12, policy, set(support), fault=fault, **kw)
    return CK.check(d, phase="service", expect_complete=False, support_override=sorted(SUPPORT))


# ---------------------------------------------------------------- gate P
@GPU
def test_gate_p_new_precisions_and_disguise(ex, bundle, tmp_path):
    from experiments.gpu_long_trajectory_v1 import campaign as CA
    states = [g for g in bundle["gate_P_states"] if g["N"] == 12 and g["p"] in (73, 161) and g["state"] in (0, 1000)]
    d = tmp_path / "clean"
    for g in states:
        for b in (32, 128):
            CA.gate_p_one(ex, d, g, b)
    v = CK.check(d, phase="gateP", expect_complete=False)
    assert v["support"]["verified_in_gate_P"] == [73, 161] and not v["support"]["failed_in_gate_P"], v["issues"]
    for req, dev in ((73, 78), (161, 163)):                  # faults P1, P2: precision disguise
        d = tmp_path / f"disguise{req}"
        for g in [x for x in states if x["p"] == req]:
            for b in (32, 128):
                CA.gate_p_one(ex, d, g, b, device_p=dev, fault=f"disguise_{dev}")
        v = CK.check(d, phase="gateP", expect_complete=False)
        assert _failed(v, "gateP_precision_echo") and req in v["support"]["failed_in_gate_P"]
        assert req in v["support"]["GPU_UNSUPPORTED_P"]


# ---------------------------------------------------------------- fixed p
@GPU
def test_fixed_p163_exact_and_layouts(own, ex, bundle, tmp_path):
    v = _fixed(tmp_path, ex, bundle, 163, blocks=(32, 64))
    assert v["verdict"] == "EVIDENCE OK", v["issues"]
    assert v["stats"]["passes_exact"] == 2 and v["stats"]["steps_compared"] == 2000


@GPU
def test_fixed_p64_long_stop_exact(own, ex, bundle, tmp_path):
    v = _fixed(tmp_path, ex, bundle, 64)
    assert v["verdict"] == "EVIDENCE OK", v["issues"]
    assert v["stats"]["stops_exact"] == 1


@GPU
@pytest.mark.parametrize("fault,stage", [(1, "F_s"), (2, "F1"), (4, "p1"), (5, "q1"), (6, "F1")])
def test_step500_faults(own, ex, bundle, tmp_path, fault, stage):
    v = _fixed(tmp_path, ex, bundle, 163, fault=fault)
    fd = v["first_divergence"][0]
    assert (fd["first_divergence_step"], fd["first_divergence_stage"], fd["precision"]) == (500, stage, 163), fd
    assert "atom" in fd


@GPU
@pytest.mark.parametrize("fault,stage", [(7, "q1"), (8, "p1"), (9, "F1")])
def test_one_ulp_faults_located(own, ex, bundle, tmp_path, fault, stage):
    fd = _fixed(tmp_path, ex, bundle, 163, fault=fault)["first_divergence"][0]
    assert (fd["first_divergence_step"], fd["first_divergence_stage"], fd["atom"], fd["component"], fd["end"]) == \
        (500, stage, 0, "x", "upper"), fd


@GPU
def test_3_step_label_skipped(own, ex, bundle, tmp_path):
    v = _fixed(tmp_path, ex, bundle, 163, fault=3)
    assert _failed(v, "step_indices_contiguous") and _failed(v, "per_step_digests_equal")


@GPU
def test_18_block_dependent_after_500(own, ex, bundle, tmp_path):
    v = _fixed(tmp_path, ex, bundle, 163, blocks=(32, 64), fault=18)
    assert _failed(v, "layouts_identical")
    fd = v["first_divergence"][0]
    assert (fd["first_divergence_step"], fd["first_divergence_stage"]) == (500, "F1"), fd


@GPU
def test_10_continue_after_long_stop(own, ex, bundle, tmp_path):
    v = _fixed(tmp_path, ex, bundle, 64, fault=10)
    assert _failed(v, "step_count_equal") and _failed(v, "force_evaluations_reuse")


@GPU
def test_11_stop_pair_changed(own, ex, bundle, tmp_path):
    assert _failed(_fixed(tmp_path, ex, bundle, 64, fault=11), "stop_equal")


# ---------------------------------------------------------------- service
@GPU
def test_service_base64_and_family_max(own, ex, bundle, tmp_path):
    from experiments.gpu_long_trajectory_v1 import campaign as CA
    d = tmp_path / "ev"
    s1 = CA.service_one(ex, d, bundle, 12, "BASE64", SUPPORT)
    s2 = CA.service_one(ex, d, bundle, 12, "FAMILY_MAX", SUPPORT)
    assert s1["p_sequence"] == [64, 73, 161] and s2["p_sequence"] == [163]
    assert s1["execution_label"] == s2["execution_label"] == "GPU_FULL_RETRY"
    v = CK.check(d, phase="service", expect_complete=False, support_override=sorted(SUPPORT))
    assert v["verdict"] == "EVIDENCE OK", v["issues"]
    assert v["stats"]["services_exact"] == 2 and v["final_cells_across_policies_equal"] == {"12": True}


@GPU
def test_service_cpu_fallback_for_unsupported_p(own, ex, bundle, tmp_path):
    from experiments.gpu_long_trajectory_v1 import campaign as CA
    d = tmp_path / "ev"
    s = CA.service_one(ex, d, bundle, 12, "BASE64", SUPPORT - {73}, demonstration=True)
    assert [x["backend"] for x in s["passes"]] == ["GPU", "CPU_E2_FALLBACK", "GPU"]
    assert s["p_sequence"] == [64, 73, 161] and s["execution_label"] == "GPU_WITH_CPU_PRECISION_FALLBACK"
    v = CK.check(d, phase="service", expect_complete=False, support_override=sorted(SUPPORT))
    assert v["verdict"] == "EVIDENCE OK", v["issues"]


@GPU
@pytest.mark.parametrize("fault,check,support", [
    (12, "C0_pass_starts_from_original_state", SUPPORT),
    (13, "service_p2_sequence", SUPPORT),
    (14, "gpu_only_for_supported_p", SUPPORT - {73}),
    (15, "device_precision_echo", SUPPORT),
    (16, "service_start_p", SUPPORT),
    (17, "checkpoint_endpoints_equal", SUPPORT)])
def test_service_faults(own, ex, bundle, tmp_path, fault, check, support):
    # faults 12 / 14 / 15 corrupt pass 2; the service is cut after it (max_passes = 2, a test-only bound) so that P2
    # does not chase the corrupted record into arbitrary precisions; the injected pass is still fully checked
    kw = {"max_passes": 2} if fault in (12, 14, 15) else {}
    v = _service(tmp_path, ex, bundle, support=support, fault=fault, **kw)
    assert _failed(v, check), {k: c for k, c in v["counts"].items() if c[1]}
    if fault in (14, 15):
        assert _failed(v, "device_precision_echo") and _failed(v, "per_step_digests_equal")
