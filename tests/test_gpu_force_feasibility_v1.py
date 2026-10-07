"""GPU_FORCE_FEASIBILITY_V1 (G0): exact serialization, trace fidelity, and the twelve fault injections the independent
checker must detect. Uses a prefix of the sealed bundle (150 samples at p=109, 60 at p=163, the 3 domain probes at
p=109). Skips without nvcc / MSVC or g++ / a CUDA device."""

import json
import random

import pytest

from a_numeric_native import harness as H
from experiments.gpu_force_feasibility_v1 import campaign as CA
from experiments.gpu_force_feasibility_v1 import checker as CK
from experiments.gpu_force_feasibility_v1 import compile_plan as CP
from experiments.gpu_force_feasibility_v1.dyadic import decode, decode_iv, encode, encode_iv

GPU = pytest.mark.skipif(not H.have_gpu_toolchain(), reason="CUDA toolchain or device missing")
NAMES = ("main_p109", "main_p163", "probe_p109")


@pytest.fixture(scope="module")
def bundle():
    return CA.load_bundle()


@pytest.fixture(scope="module")
def subs(bundle):
    full = CA.subsets(bundle)
    take = {"main_p109": 150, "main_p163": 60, "probe_p109": 3}
    return {k: (full[k][0], full[k][1][:n], full[k][2][:n]) for k, n in take.items()}


def test_encoding_round_trip(bundle):
    rnd = random.Random(1)
    for x in rnd.sample(bundle["main"], 200) + bundle["test_only"]:
        for key in ("r2", "g_cpu"):
            if x[key]:
                assert encode_iv(decode_iv(x[key])) == x[key]
    for t in [(0, 0, 0, 0), (1, 1, -3, 1), (0, (1 << 191) | 1, -500, 192)]:
        assert decode(encode(t)) == t


def test_trace_replay_equals_frozen_force(bundle):
    from mpmath import iv

    from experiments.gpu_force_feasibility_v1.samples import make_force
    for p in (109, 163):
        prog = CP.trace(p)
        assert sum(op[0] == "REQPOS" for op in prog["ops"]) == 2 and sum(op[0] == "EXP" for op in prog["ops"]) == 9
        f = make_force(p)
        for x in [y for y in bundle["main"] if y["p"] == p][:40]:
            r2 = decode_iv(x["r2"])
            iv.prec = p
            assert CP.replay(prog, r2) == ("OK", f(iv.make_mpf(r2))._mpi_) == ("OK", decode_iv(x["g_cpu"]))


@pytest.fixture(scope="module")
def lib(tmp_path_factory):
    if not H.have_gpu_toolchain():
        pytest.skip("CUDA toolchain or device missing")
    from experiments.gpu_force_feasibility_v1 import gpu_host as GH
    path, arch, log = GH.build(tmp_path_factory.mktemp("g0build"))
    g = GH.G0(path)
    yield g
    g.lib.g0_free()


def _evidence(tmp_path, g, subs, fault=0, wl=16, tamper=None, layouts=((128, 0),), names=NAMES):
    d = tmp_path / f"ev_f{fault}_{tamper}_{wl}"
    for name in names:
        p, ids, ivs = subs[name]
        for block, grid in layouts:
            CA.run_one(g, d, name, p, ids, ivs, block, grid, fault, wl, tamper if name.startswith("main") else None)
    return CK.check(d, require=list(names), expect_layouts=False, full=False)


def _failed(v, name):
    return v["counts"].get(name, [0, 0])[1] > 0


@GPU
def test_clean_fixture_exact(lib, subs, tmp_path):
    v = _evidence(tmp_path, lib, subs, layouts=((32, 1), (64, 7), (128, 0), (256, 0)))
    assert v["verdict"] == "EVIDENCE OK", v["issues"]
    assert v["summary"]["main_p109"]["EXACT"] == 150 and v["summary"]["main_p163"]["EXACT"] == 60
    assert v["summary"]["probe_p109"]["DOMAIN_OK"] == 3


@GPU
@pytest.mark.parametrize("fault", [1, 2, 3, 4, 5, 6])
def test_device_arithmetic_faults_unsound(lib, subs, tmp_path, fault):
    v = _evidence(tmp_path, lib, subs, fault=fault)
    assert _failed(v, "containment") or _failed(v, "output_canonical"), (fault, v["summary"])


@GPU
def test_07_den_obligation_removed(lib, subs, tmp_path):
    assert _failed(_evidence(tmp_path, lib, subs, fault=7), "obligations_complete")


@GPU
def test_08_overflow_ignored(lib, subs, tmp_path):
    clean = _evidence(tmp_path / "c", lib, subs, wl=8)              # a too-small width: refusals, never wrong bits
    assert clean["summary"]["main_p109"]["REFUSED"] > 0 and not _failed(clean, "containment")
    v = _evidence(tmp_path / "f", lib, subs, fault=8, wl=8)
    assert _failed(v, "containment") or _failed(v, "output_canonical")


@GPU
def test_09_pair_dropped(lib, subs, tmp_path):
    assert _failed(_evidence(tmp_path, lib, subs, tamper="drop"), "pair_count")


@GPU
def test_10_block_dependent_branch(lib, subs, tmp_path):
    v = _evidence(tmp_path, lib, subs, fault=10, layouts=((32, 0), (64, 0)))
    assert _failed(v, "layouts_bit_identical")


@GPU
def test_11_h2d_input_altered(lib, subs, tmp_path):
    assert _failed(_evidence(tmp_path, lib, subs, tamper="input"), "input_echo_equals_bundle")


@GPU
def test_12_output_order_swapped(lib, subs, tmp_path):
    assert _failed(_evidence(tmp_path, lib, subs, tamper="swap"), "output_index_echo")


@GPU
def test_unsupported_precision_refused(lib):
    from experiments.gpu_force_feasibility_v1 import gpu_host as GH
    with pytest.raises(GH.Refused):
        lib.upload(100)


def test_checker_independent_of_gpu_code():
    src = open(CK.__file__, encoding="utf-8").read()
    for mod in ("gpu_host", "compile_plan", "campaign", "g0"):
        assert f"import {mod}" not in src and f"gpu_force_feasibility_v1 import {mod}" not in src


def test_checker_cost_classes():
    a = (0, 3, -2, 2)
    assert CK.classify(((0, 1, -1, 1), (0, 1, 0, 1)), ((0, 1, -1, 1), (0, 1, 0, 1)))[0] == "EXACT"
    assert CK.classify(((0, 1, -2, 1), (0, 1, 0, 1)), ((0, 1, -1, 1), (0, 1, 0, 1)))[0] == "SOUND_TIGHT"
    assert CK.classify(((0, 1, -1, 1), (0, a[1], a[2], a[3])), ((0, 1, -2, 1), (0, 1, 0, 1)))[0] == "UNSOUND"
    assert CK.classify(((0, 0, 0, 0), (0, 1, 2, 1)), ((0, 1, -1, 1), (0, 1, 0, 1)))[0] == "SOUND_WIDE"
    assert CK.classify(((0, 1, -1, 1), (0, 1, 0, 1)), ((0, 1, -1, 1), (0, 1, -1, 1))) == ("SOUND_WIDE", "inf")
