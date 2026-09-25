"""B1 (parallel C++) against the A-Numeric VM, at several thread counts (E9).

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md 4.2. The thread count may change
how SUM/DOT terms are split and which thread runs which program; it must not
change a single bit of any result. Skipped when MSVC is not installed.
"""
from __future__ import annotations

import pytest

from a_numeric_native import harness as H

pytestmark = pytest.mark.skipif(H.find_vcvars() is None, reason="MSVC not installed")

THREADS = (1, 2, 4, 8, 12)


@pytest.fixture(scope="module")
def cases():
    progs = {name: make() for name, make in H.FAMILIES.items()}
    return progs, {name: H.vm_expected(p) for name, p in progs.items()}


@pytest.fixture(scope="module")
def exes(tmp_path_factory):
    out = tmp_path_factory.mktemp("b1")
    return {i: H.build_native("b1", out, i) for i in (0, 101, 102)}


@pytest.mark.parametrize("threads", THREADS)
def test_b1_matches_vm_at_every_thread_count(threads, cases, exes) -> None:
    progs, expected = cases
    for family in H.FAMILIES:
        got = H.run_native(exes[0], progs[family], (threads,))
        bad = H.mismatches(expected[family], got)
        assert not bad, (family, threads, [(progs[family][i][2], expected[family][i], got[i]) for i in bad[:2]])


def test_long_reductions_are_not_vacuous(cases) -> None:
    progs, expected = cases
    rows = expected["long_reduction"]
    lengths = {len(p[1]) for p in progs["long_reduction"]}
    assert any(n % t for n in lengths for t in THREADS[1:])      # uneven splits exist
    assert max(lengths) > 2000
    assert sum(1 for e in rows if e["halt"] is None) > 50


def test_float_chunk_reduction_is_caught_and_depends_on_threads(cases, exes) -> None:
    """INJECT 101: each thread sums its chunk in hardware floats -- the usual parallel reduction."""
    progs, expected = cases
    outs = {t: H.run_native(exes[101], progs["long_reduction"], (t,)) for t in THREADS}
    for t in THREADS:
        assert H.mismatches(expected["long_reduction"], outs[t]), t
    assert outs[1] != outs[12]                    # the result depends on the thread count


def test_partition_off_by_one_only_shows_with_threads(cases, exes) -> None:
    """INJECT 102 drops the tail when the length does not divide by T: invisible serially (E9)."""
    progs, expected = cases
    assert not H.mismatches(expected["long_reduction"], H.run_native(exes[102], progs["long_reduction"], (1,)))
    for t in THREADS[1:]:
        assert H.mismatches(expected["long_reduction"], H.run_native(exes[102], progs["long_reduction"], (t,))), t
