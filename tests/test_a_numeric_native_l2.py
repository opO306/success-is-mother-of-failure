"""L2 numerical structure: +J / -J on pairs, many pairs summed onto one particle.

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md 4.3. No potential is chosen: the
impulses J are test inputs. Checked: exact +J / -J, one order-free SUM per
particle and axis, invariance under pair order / pair direction / particle
relabelling, B0 = B1 (threads) = B2 (block, grid, chunk, program order) = VM,
and total momentum.
"""
from __future__ import annotations

from fractions import Fraction

import pytest

from a_numeric_native import harness as H
from a_numeric_native import l2
from a_numeric_native.harness import F64, FX64

pytestmark = pytest.mark.skipif(not H.have_cxx(), reason="C++ toolchain (MSVC / g++) not installed")
HAVE_GPU = H.have_gpu_toolchain()


@pytest.fixture(scope="module")
def world():
    systems = l2.systems()
    progs = [l2.program(s) for s in systems]
    return systems, progs, H.vm_expected(progs)


def _variant(s, n):
    P, M = len(s.p0), len(s.pairs)
    lab = H.permutation(P, f"lab{n}")
    return ([f"r{lab[i]}" for i in range(P)], H.permutation(M, f"ord{n}"),
            frozenset(k for k in range(M) if k % 3 == 1))


def test_systems_are_not_vacuous(world) -> None:
    systems, _, expected = world
    assert all(e["halt"] is None for e in expected)
    assert max(len(s.pairs) for s in systems) >= 2049                  # one particle, 2049 pairs
    assert {s.profile.name for s in systems} == {F64.name, FX64.name}


def test_every_pair_gets_exactly_plus_and_minus_j(world) -> None:
    systems, progs, expected = world
    for s, (_, inputs, _), e in zip(systems, progs, expected):
        regs = e["registers"]
        for slot in range(len(s.pairs)):
            for x in l2.AXES:
                j = s.profile.to_exact(inputs[f"J{slot}_{x}"])
                raw = regs[f"nJ{slot}_{x}"]
                nj = s.profile.to_exact(int(raw, 16) if s.profile is F64 else int(raw))
                assert nj == -j
    # two particles, fixed point: the momentum changes are exactly +J and -J
    for s, e in zip(systems, expected):
        if s.profile is FX64 and len(s.p0) == 2:
            new = l2.new_momenta(s, e)
            for ax in range(3):
                assert int(new[0][ax]) - s.p0[0][ax] == s.J[0][ax]
                assert int(new[1][ax]) - s.p0[1][ax] == -s.J[0][ax]


def test_executors_agree_with_the_vm(world, tmp_path_factory) -> None:
    _, progs, expected = world
    out = tmp_path_factory.mktemp("l2")
    assert not H.mismatches(expected, H.run_native(H.build_native("b0", out), progs))
    b1 = H.build_native("b1", out)
    for t in (1, 2, 4, 8, 12):
        assert not H.mismatches(expected, H.run_native(b1, progs, (t,))), t
    if HAVE_GPU:
        b2 = H.build_b2(out)
        for layout in ((1,), (32,), (256,), (64, 1, 0), (64, 3, 7), (128, 5, 11)):
            assert not H.mismatches(expected, H.run_native(b2, progs, layout)), layout
        assert not H.mismatches(expected, H.run_native_permuted(b2, progs, (64, 3, 7)))


def _invariance_violations(systems, chained):
    progs, meta = [], []
    for n, s in enumerate(systems):
        names, order, swap = _variant(s, n)
        progs += [l2.program(s, chained=chained), l2.program(s, names=names, order=order, swap=swap, chained=chained)]
        meta.append((s, names))
    res = H.vm_expected(progs)
    return sum(l2.new_momenta(s, res[2 * n]) != l2.new_momenta(s, res[2 * n + 1], names)
               for n, (s, names) in enumerate(meta))


def test_pair_order_direction_and_labels_do_not_change_any_bit(world) -> None:
    systems, _, _ = world
    assert _invariance_violations(systems, chained=False) == 0


def test_chained_add_accumulation_is_caught_by_the_invariance_check(world) -> None:
    """Deliberate structural defect: p += c1; p += c2; ... (one rounding per term). All executors
    agree on it (same program), so only the invariance check can expose it."""
    systems, _, _ = world
    assert _invariance_violations(systems, chained=True) > 0


def test_total_momentum(world) -> None:
    """Fixed point: exactly conserved. A-Binary64-Finite: each particle's new momentum is rounded once,
    so the exact total drifts, bounded by the sum of those half-ulps (a number-system property)."""
    systems, _, expected = world
    drifted = axes = 0
    for s, e in zip(systems, expected):
        new = l2.new_momenta(s, e)
        for ax in range(3):
            raw = [int(m[ax], 16) if s.profile is F64 else int(m[ax]) for m in new]
            before = l2.exact_total(s.profile, [p[ax] for p in s.p0])
            after = l2.exact_total(s.profile, raw)
            if s.profile is FX64:
                assert after == before
            else:
                axes += 1
                assert abs(after - before) <= sum((l2.ulp_half(F64, v) for v in raw), Fraction(0))
                drifted += after != before
    assert drifted > 0 and axes > 0
