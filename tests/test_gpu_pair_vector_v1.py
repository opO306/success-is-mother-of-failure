"""GPU_PAIR_VECTOR_V1: the checker's own forces loop equals the recorded real-run F, and the fourteen fault
injections the independent checker must detect. Fixture: the N = 12 step-0 and step-100 states (p = 163), the
N = 40 step-0 state (p = 109) and the six domain probe states. Skips without a CUDA toolchain / device."""

import json

import pytest

from a_numeric_native import harness as H
from experiments.gpu_pair_vector_v1 import campaign as CA
from experiments.gpu_pair_vector_v1 import checker as CK

GPU = pytest.mark.skipif(not H.have_gpu_toolchain(), reason="CUDA toolchain or device missing")


@pytest.fixture(scope="module")
def bundle():
    return CA.load_bundle()


@pytest.fixture(scope="module")
def fixture_states(bundle):
    pick = [x for x in bundle["main"] if (x["N"], x["step"]) in ((12, 0), (12, 100), (40, 0))]
    return [("main", x) for x in pick] + [("test", x) for x in bundle["test_only"] if x["role"].startswith("PROBE")]


def test_checker_loop_equals_recorded_forces(bundle):
    from experiments.gpu_force_feasibility_v1.dyadic import decode_iv
    for x in [y for y in bundle["main"] if y["N"] == 12][:2] + [y for y in bundle["test_only"] if y["role"].startswith("PROBE")]:
        q = [[decode_iv(e) for e in row] for row in x["q"]]
        pairs, first, F = CK.own_forces(q, x["p"])
        assert (first, pairs[first][0] if first is not None else "PROVEN") == (x["cpu_first_stop_pair"], x["cpu_status"])
        if x["F_cpu"]:
            assert F == [[decode_iv(e) for e in r] for r in x["F_cpu"]]


@pytest.fixture(scope="module")
def pv(tmp_path_factory):
    if not H.have_gpu_toolchain():
        pytest.skip("CUDA toolchain or device missing")
    from experiments.gpu_pair_vector_v1 import pv_host as PH
    lib, arch, log = PH.build(tmp_path_factory.mktemp("pv1build"))
    g = PH.PV(lib)
    yield g
    g.lib.pv_free()


def _ev(tmp_path, pv, states, layouts=((128, 0),), **kw):
    d = tmp_path / "ev"
    for kind, st in states:
        for block, grid in (layouts if kind == "main" else ((128, 0),)):
            CA.run_state(pv, d, kind, st, block, grid, **kw)
    return CK.check(d, expect_layouts=False)


def _failed(v, name):
    return v["counts"].get(name, [0, 0])[1] > 0


@GPU
def test_clean_fixture_exact(pv, fixture_states, tmp_path):
    v = _ev(tmp_path, pv, fixture_states, layouts=((32, 1), (64, 7), (128, 0), (256, 0)))
    assert v["verdict"] == "EVIDENCE OK", v["issues"]
    assert v["stats"]["PAIR_UNSOUND"] == v["stats"]["PAIR_SOUND_ONLY"] == v["stats"]["DOMAIN_MISMATCH"] == 0
    assert v["stats"]["F_DIFF"] == 0 and v["stats"]["F_EXACT"] > 0


@GPU
@pytest.mark.parametrize("fault,check", [(1, "pair_J_exact"), (2, "pair_J_exact"), (3, "pair_J_exact"), (4, "pair_J_exact"),
                                         (5, "r2_equal"), (6, "domain_status"), (9, "atom_F_exact"),
                                         (10, "atom_F_exact")])
def test_device_faults(pv, fixture_states, tmp_path, fault, check):
    assert _failed(_ev(tmp_path, pv, fixture_states, fault=fault), check)


@GPU
def test_11_unordered_reduction(pv, fixture_states, tmp_path):
    v = _ev(tmp_path, pv, fixture_states, layouts=((32, 0), (64, 0), (128, 1)), fault=11)
    assert _failed(v, "layouts_bit_identical") or _failed(v, "atom_F_exact")


@GPU
@pytest.mark.parametrize("tamper,check", [("drop_pair", "pair_count"), ("swap_pairs", "pair_id_echo"),
                                          ("swap_atoms", "atom_id_echo"), ("p_altered", "precision_echo")])
def test_host_faults(pv, fixture_states, tmp_path, tamper, check):
    assert _failed(_ev(tmp_path, pv, fixture_states, tamper=tamper), check)


@GPU
def test_14_overflow_treated_as_success(pv, fixture_states, tmp_path):
    clean = _ev(tmp_path / "c", pv, fixture_states, wl=8)
    assert clean["stats"]["REFUSED"] > 0 and not _failed(clean, "pair_J_exact")
    v = _ev(tmp_path / "f", pv, fixture_states, wl=8, g0fault=8)
    assert _failed(v, "pair_J_exact") or _failed(v, "r2_equal") or _failed(v, "G_equal")


def test_checker_independent_of_gpu_code():
    src = open(CK.__file__, encoding="utf-8").read()
    for mod in ("pv_host", "campaign", "gpu_host", "compile_plan"):
        assert f"import {mod}" not in src


def test_memory_table_monotone():
    from experiments.gpu_pair_vector_v1 import pv_host as PH
    t = PH.memory_table()
    assert [r["N"] for r in t] == [64, 128, 256, 512, 1024]
    assert all(a["total_gpu_bytes"] < b["total_gpu_bytes"] for a, b in zip(t, t[1:]))
    assert json.dumps(t)
