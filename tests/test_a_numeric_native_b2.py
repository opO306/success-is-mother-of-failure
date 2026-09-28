"""B2 (CUDA) against the A-Numeric VM, at several block sizes (E9).

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md 4.1. One program per block; the
block's threads share every SUM/DOT exactly. The block size must not change a
single bit. Skipped without MSVC, nvcc or an NVIDIA GPU.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from a_numeric_native import harness as H

pytestmark = pytest.mark.skipif(not H.have_gpu_toolchain(),
                                reason="C++ toolchain, nvcc or CUDA device missing")

BLOCKS = (1, 32, 64, 128, 256)
MUTANTS = {
    201: ("each thread sums its share in floats, partials added in floats", {"b64_sum_dot", "long_reduction"}),
    203: ("ADD rounds toward zero (__dadd_rz)", {"b64_hard", "b64_stream"}),
    204: ("device exact rounding ties away from zero", {"b64_sum_dot"}),
    205: ("FX range check skipped", {"fx_exhaustive", "fx_wide"}),
    206: ("high word of the 106-bit DOT product dropped", {"b64_sum_dot", "distance"}),
    207: ("FX SQRT floor instead of nearest", {"fx_exhaustive", "fx_wide"}),
    212: ("EXP through CUDA's exp()", {"exp"}),
    213: ("EXP at one modest precision, no refinement", {"exp"}),
}


@pytest.fixture(scope="module")
def cases():
    progs = {name: make() for name, make in H.FAMILIES.items()}
    return progs, {name: H.vm_expected(p) for name, p in progs.items()}


# (block, grid blocks, launch chunk); 0 = default. One block for everything, grids that do not divide
# the program count, tiny chunks, a chunk that leaves a last partial launch, one program per launch.
LAYOUTS = [(64, 0, 0), (64, 1, 0), (64, 7, 0), (32, 3, 1000), (128, 5, 7), (256, 64, 333), (64, 1, 1), (32, 0, 997)]
# defects that depend on the launch layout -- each is invisible in at least one layout
GRID_MUTANTS = {
    208: "one program per block assumed (programs past gridDim.x never run)",
    209: "a last partial launch skipped",
    210: "result depends on blockIdx.x (block 1 drops a term)",
}


@pytest.fixture(scope="module")
def exes(tmp_path_factory):
    out = tmp_path_factory.mktemp("b2")
    ids = (0, 202, 211, 214, *MUTANTS, *GRID_MUTANTS)
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


# --- E9: grid / launch layout and program order -------------------------------

@pytest.mark.parametrize("layout", LAYOUTS, ids=lambda l: "B{}_G{}_C{}".format(*l))
def test_b2_matches_vm_in_every_launch_layout(layout, cases, exes) -> None:
    progs, expected = cases
    for family in H.FAMILIES:
        assert not H.mismatches(expected[family], H.run_native(exes[0], progs[family], layout)), (family, layout)


def test_b2_is_independent_of_program_order(cases, exes) -> None:
    progs, expected = cases
    for family in H.FAMILIES:
        for tag in ("order-a", "order-b"):
            got = H.run_native_permuted(exes[0], progs[family], (64, 5, 101), tag)
            assert not H.mismatches(expected[family], got), (family, tag)


@pytest.mark.parametrize("mutant", sorted(GRID_MUTANTS))
def test_layout_dependent_defects_are_caught_and_need_layout_variation(mutant, cases, exes) -> None:
    progs, expected = cases
    families = ("b64_stream", "b64_sum_dot", "long_reduction")   # every one of these defects shows in them
    caught = {lay for lay in LAYOUTS
              if any(H.mismatches(expected[f], H.run_native(exes[mutant], progs[f], lay)) for f in families)}
    assert caught, GRID_MUTANTS[mutant]
    assert caught != set(LAYOUTS), "each of these defects hides in some layout -- that is why E9 varies the layout"


# --- width contract: NATIVE_MAX_REDUCTION_TERMS ---------------------------------

def test_declared_limit_matches_the_source() -> None:
    src = (H.HERE / "b2_cuda.cu").read_text(encoding="utf-8")
    assert f"#define NATIVE_MAX_REDUCTION_TERMS {H.NATIVE_MAX_REDUCTION_TERMS}" in src
    # the proof in the source: 4196 bits per DOT term + ceil(log2 N) + 1 sign bit <= 4480
    assert 4196 + (H.NATIVE_MAX_REDUCTION_TERMS - 1).bit_length() + 1 <= 140 * 32


@pytest.fixture(scope="module")
def width():
    n = H.NATIVE_MAX_REDUCTION_TERMS
    at, over = H.width_programs(n), H.width_programs(n + 1)
    return at, H.vm_expected(at), over, H.vm_expected(over)


def test_reductions_of_exactly_the_limit_match_the_vm(width, exes) -> None:
    at, expected, _, _ = width
    assert {tuple(e["halt"]) if e["halt"] else None for e in expected} == {None, (0, "overflow")}
    for layout in ((64,), (256, 3, 0), (1,)):
        assert not H.mismatches(expected, H.run_native(exes[0], at, layout)), layout


def test_one_term_more_is_refused_before_running(width, exes) -> None:
    _, _, over, _ = width
    for prog in over:
        with pytest.raises(H.NativeRejected, match="native_reduction_too_long"):
            H.run_native(exes[0], [prog], (64,))


def test_b0_b1_have_no_such_limit(width, tmp_path_factory) -> None:
    _, _, over, expected = width
    out = tmp_path_factory.mktemp("b01w")
    assert not H.mismatches(expected, H.run_native(H.build_native("b0", out), over))
    assert not H.mismatches(expected, H.run_native(H.build_native("b1", out), over, (8,)))


def test_too_narrow_accumulator_is_caught_by_the_wrap_probe(width, exes) -> None:
    """INJECT 211: 4192 bits. Wraparound is modular, so only a sum that is huge but small modulo
    2^4192 exposes it -- the wrap probe (last program)."""
    at, expected, _, _ = width
    bad = H.mismatches(expected, H.run_native(exes[211], at, (64,)))
    assert bad == [len(at) - 1]


# --- EXP precision contract ------------------------------------------------------

def test_exp_precision_cap_refuses_instead_of_answering(cases, exes) -> None:
    """INJECT 214 never lets the two ends of the enclosure agree: B2 must refuse the batch after
    NATIVE_EXP_MAX_ATTEMPTS -- a capability limit, never a wrong result."""
    progs, _ = cases
    with pytest.raises(H.NativeRejected, match="native_exp_precision_exhausted"):
        H.run_native(exes[214], progs["exp"][:50], (64,))
    src = (H.HERE / "b2_cuda.cu").read_text(encoding="utf-8")
    assert "#define NATIVE_EXP_MAX_ATTEMPTS 4" in src
