"""C1-B1 state-width microbenchmark kernels (designer 13th ed. item 10): the benchmarked operations are exact.

Timings are reported in the design doc, not asserted. What is asserted: for the three drift rules under comparison
(designer 14th ed.) -- v1 round(r + p dt/m) and v2 r + round(p dt/m) at position FX(64,48), FX(96,48), FX(128,48),
and exact drift at 160-bit positions in units 2^-48 / B bohr -- with momentum FX(64,48), the CPU and CUDA kernels give
exactly the bits of an exact Python model (drift, exact Delta r and R^2, +-J). Every 8th input pair drifts on an exact
tie, so v1 and v2 are really told apart. Skipped without MSVC / nvcc / GPU.
"""
from __future__ import annotations

import pytest

from a_numeric_native.harness import have_cxx, have_gpu_toolchain
from a_physics_native import bench_state as S


CASES = [("v1", 2), ("v1", 3), ("v1", 4), ("v2", 2), ("v2", 3), ("v2", 4), ("exact", 5)]


def test_the_inputs_contain_ties_that_separate_v1_and_v2() -> None:
    assert S.expected(3, 64, "v1") != S.expected(3, 64, "v2")


@pytest.fixture(scope="module")
def cpu_exe(tmp_path_factory):
    if not have_cxx():
        pytest.skip("C++ toolchain (MSVC / g++) not installed")
    return S.build("cpu", tmp_path_factory.mktemp("bcpu"))


@pytest.fixture(scope="module")
def cuda_exe(tmp_path_factory):
    if not have_gpu_toolchain():
        pytest.skip("C++ toolchain, nvcc or a CUDA device missing")
    return S.build("cuda", tmp_path_factory.mktemp("bgpu"))


@pytest.mark.parametrize("rule,limbs", CASES)
def test_cpu_kernels_are_exact(rule, limbs, cpu_exe) -> None:
    assert S.check(cpu_exe, limbs, 400, rule)


@pytest.mark.parametrize("rule,limbs", CASES)
def test_cuda_kernels_are_exact(rule, limbs, cuda_exe) -> None:
    assert S.check(cuda_exe, limbs, 400, rule)


MOM_KINDS = ["fx64_48", "fx80_64", "fx96_80", "fx128_112", "carry"]


@pytest.mark.parametrize("kind", MOM_KINDS)
def test_cpu_momentum_kernels_are_exact(kind, cpu_exe) -> None:
    """Momentum comparison (15th ed.): position FX(96,48) + drift v2 with each momentum representation."""
    assert S.check_mom(cpu_exe, kind, 400)


@pytest.mark.parametrize("kind", MOM_KINDS)
def test_cuda_momentum_kernels_are_exact(kind, cuda_exe) -> None:
    assert S.check_mom(cuda_exe, kind, 400)
