"""C1-B1 state-width microbenchmark kernels (designer 13th ed. item 10): the benchmarked operations are exact.

Timings are reported in the design doc, not asserted. What is asserted: for position FX(64,48), FX(96,48),
FX(128,48) with momentum FX(64,48), the CPU and CUDA kernels give exactly the bits of an exact Python model
(drift round-half-even of r + p dt / m, exact Delta r and R^2, +-J). Skipped without MSVC / nvcc / GPU.
"""
from __future__ import annotations

import pytest

from a_numeric_native.harness import cuda_device_present, find_nvcc, find_vcvars
from a_physics_native import bench_state as S


@pytest.mark.skipif(find_vcvars() is None, reason="MSVC not installed")
@pytest.mark.parametrize("limbs", [2, 3, 4])
def test_cpu_kernels_are_exact(limbs, tmp_path_factory) -> None:
    exe = S.build("cpu", tmp_path_factory.mktemp(f"bcpu{limbs}"))
    assert S.check(exe, limbs, 400)


@pytest.mark.skipif(find_vcvars() is None or find_nvcc() is None or not cuda_device_present(),
                    reason="MSVC, nvcc or a CUDA device missing")
@pytest.mark.parametrize("limbs", [2, 3, 4])
def test_cuda_kernels_are_exact(limbs, tmp_path_factory) -> None:
    exe = S.build("cuda", tmp_path_factory.mktemp(f"bgpu{limbs}"))
    assert S.check(exe, limbs, 400)
