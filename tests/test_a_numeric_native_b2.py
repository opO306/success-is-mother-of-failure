"""B2 (CUDA) against the A-Numeric VM, at several block sizes (E9).

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md 4.1. One program per block; the
block's threads share every SUM/DOT exactly. The block size must not change a
single bit. Skipped without MSVC, nvcc or an NVIDIA GPU.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from a_numeric_native import harness as H

pytestmark = pytest.mark.skipif(H.find_vcvars() is None or H.find_nvcc() is None or not H.cuda_device_present(),
                                reason="MSVC, nvcc or CUDA device missing")

BLOCKS = (1, 32, 64, 128, 256)
MUTANTS = {
    201: ("each thread sums its share in floats, partials added in floats", {"b64_sum_dot", "long_reduction"}),
    203: ("ADD rounds toward zero (__dadd_rz)", {"b64_hard", "b64_stream"}),
    204: ("device exact rounding ties away from zero", {"b64_sum_dot"}),
    205: ("FX range check skipped", {"fx_exhaustive", "fx_wide"}),
    206: ("high word of the 106-bit DOT product dropped", {"b64_sum_dot", "distance"}),
    207: ("FX SQRT floor instead of nearest", {"fx_exhaustive", "fx_wide"}),
}


@pytest.fixture(scope="module")
def cases():
    progs = {name: make() for name, make in H.FAMILIES.items()}
    return progs, {name: H.vm_expected(p) for name, p in progs.items()}


@pytest.fixture(scope="module")
def exes(tmp_path_factory):
    out = tmp_path_factory.mktemp("b2")
    ids = (0, 202, *MUTANTS)
    with ThreadPoolExecutor(4) as pool:
        return dict(zip(ids, pool.map(lambda i: H.build_b2(out, i), ids)))


@pytest.mark.parametrize("block", BLOCKS)
def test_b2_matches_vm_at_every_block_size(block, cases, exes) -> None:
    progs, expected = cases
    for family in H.FAMILIES:
        got = H.run_native(exes[0], progs[family], (block,))
        bad = H.mismatches(expected[family], got)
        assert not bad, (family, block, [(progs[family][i][2], expected[family][i], got[i]) for i in bad[:2]])


def test_b2_source_never_calls_the_vm() -> None:
    src = (H.HERE / "b2_cuda.cu").read_text(encoding="utf-8")
    assert "a_numeric" not in src and "Python.h" not in src


def test_every_injected_defect_is_caught_where_it_should_be(cases, exes) -> None:
    progs, expected = cases
    for i, (label, must) in MUTANTS.items():
        caught = {f for f in must if H.mismatches(expected[f], H.run_native(exes[i], progs[f], (64,)))}
        assert caught == must, (i, label, sorted(must - caught))


def test_one_warp_assumption_only_shows_with_larger_blocks(cases, exes) -> None:
    """INJECT 202 combines only the first 32 partials: correct at B <= 32, wrong above (E9)."""
    progs, expected = cases
    for block in (1, 32):
        assert not H.mismatches(expected["long_reduction"], H.run_native(exes[202], progs["long_reduction"], (block,)))
    for block in (64, 256):
        assert H.mismatches(expected["long_reduction"], H.run_native(exes[202], progs["long_reduction"], (block,)))
