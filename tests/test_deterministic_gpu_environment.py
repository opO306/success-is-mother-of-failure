import inspect
import json
from pathlib import Path

import pytest

from engine.deterministic import EnvironmentWorldSpec, load_environment_world_spec, reference_scale_family
from engine.deterministic.gpu_environment import (
    benchmark_cuda_resident,
    cuda_available,
    run_cpu_cuda_parity,
    run_cuda_resident_fields,
    verify_cuda_resident_every_tick,
)
import engine.deterministic.gpu_environment as gpu_module
from engine.deterministic.physical_environment_scaling import make_physical_channel_spec

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "worlds" / "deterministic_open_water_cycle_v3.json"
V4 = ROOT / "worlds" / "deterministic_physical_flux_v4.json"

cuda = pytest.mark.skipif(not cuda_available(), reason="CUDA is not available")


@cuda
def test_cuda_transport_matches_cpu_every_tick() -> None:
    report = run_cpu_cuda_parity(load_environment_world_spec(V4))

    assert report.complete_match is True
    assert tuple(item.tick for item in report.steps) == (1, 2, 3, 4)
    assert all(item.cpu_digest == item.gpu_digest for item in report.steps)
    assert report.backend_kind == "cuda-int64-transport-with-cpu-local-rules"


@cuda
@pytest.mark.parametrize("channel", ["heat", "water_surface", "solute", "vapor"])
def test_each_physical_channel_matches_cpu(channel: str) -> None:
    level = reference_scale_family().levels[0]
    report = run_cpu_cuda_parity(make_physical_channel_spec(level, channel))

    assert report.complete_match is True


@cuda
def test_cuda_transport_with_cpu_external_and_phase_rules_matches() -> None:
    raw = json.loads(V3.read_text(encoding="utf-8"))
    scale = json.loads(V4.read_text(encoding="utf-8"))["physical_scale"]
    raw["format"] = "deterministic-environment-world-spec-v4"
    raw["physical_scale"] = scale
    spec = EnvironmentWorldSpec.from_mapping(raw)

    report = run_cpu_cuda_parity(spec)

    assert report.complete_match is True
    assert len(report.steps) == 6


def test_cuda_baseline_source_has_no_forbidden_parallel_operations() -> None:
    source = inspect.getsource(gpu_module)

    assert "float32" not in source
    assert "float64" not in source
    assert "torch.scatter" not in source
    assert ".scatter_" not in source
    assert "index_add" not in source
    assert "atomic_add" not in source
    assert "import random" not in source
    assert "dtype=torch.int64" in source



@cuda
def test_resident_cuda_matches_cpu_with_one_final_download() -> None:
    spec = load_environment_world_spec(V4)
    resident = run_cuda_resident_fields(spec)
    from engine.deterministic import run_environment_world
    cpu = run_environment_world(spec).final_state

    assert resident.digest == cpu.digest
    assert resident == cpu


@cuda
def test_resident_cuda_validation_matches_every_tick() -> None:
    report = verify_cuda_resident_every_tick(load_environment_world_spec(V4))

    assert report.complete_match is True
    assert report.backend_kind == "cuda-resident-int64-fields"
    assert tuple(item.tick for item in report.steps) == (1, 2, 3, 4)


@cuda
def test_resident_cuda_refuses_active_cpu_local_rules() -> None:
    raw = json.loads(V3.read_text(encoding="utf-8"))
    raw["format"] = "deterministic-environment-world-spec-v4"
    raw["physical_scale"] = json.loads(V4.read_text(encoding="utf-8"))["physical_scale"]
    spec = EnvironmentWorldSpec.from_mapping(raw)

    with pytest.raises(ValueError, match="energy_boundaries.*mineral_conversion.*water_phase_change"):
        run_cuda_resident_fields(spec)


@cuda
def test_resident_benchmark_timing_is_external_to_state_digest() -> None:
    first = benchmark_cuda_resident((64,), 2)[0]
    second = benchmark_cuda_resident((64,), 2)[0]

    assert first.complete_match is True
    assert second.complete_match is True
    assert first.final_digest == second.final_digest
    assert first.cpu_seconds > 0 and first.gpu_seconds > 0
    assert first.gpu_peak_bytes > 0
