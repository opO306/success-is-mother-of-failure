"""Deterministic CUDA transport accelerator for A2.3 environment v4.

Only the four edge-transport fields run on CUDA in this baseline. A1 causal
steps and same-cell conversions remain on the sealed CPU reference functions.
No floating point, atomics, scatter reductions, or random operations are used.
"""
from __future__ import annotations

from dataclasses import dataclass
import time

try:
    import torch
except ImportError:  # pragma: no cover - exercised on hosts without torch
    torch = None

from .causal_kernel import CausalWorldState, step_causal_world
from .causal_spec import HeatCellSpec
from .environment_kernel import (
    EnvironmentState,
    _change_water_phase,
    _convert_local_mineral,
    _exchange_external_energy,
    initial_environment_state,
    run_environment_world,
    step_environment_world,
)
from .environment_spec import EnvironmentCellSpec, EnvironmentWorldSpec, FORMAT_V4


def cuda_available() -> bool:
    return bool(torch is not None and torch.cuda.is_available())


def _require_cuda(spec: EnvironmentWorldSpec) -> None:
    if spec.format != FORMAT_V4: raise ValueError("CUDA transport baseline supports environment v4 only")
    if spec.physical_scale is None: raise ValueError("environment v4 needs a physical scale")
    if not cuda_available(): raise RuntimeError("CUDA is not available")


def _pair_indices(width: int, height: int, phase: str):
    device = torch.device("cuda")
    if phase.startswith("horizontal"):
        parity = 0 if phase.endswith("even") else 1
        left_x = torch.arange(parity, width, 2, device=device, dtype=torch.int64)
        right_x = (left_x + 1) % width
        ys = torch.arange(height, device=device, dtype=torch.int64)
        y_grid, left_grid = torch.meshgrid(ys, left_x, indexing="ij")
        _, right_grid = torch.meshgrid(ys, right_x, indexing="ij")
        return y_grid, left_grid, y_grid, right_grid
    parity = 0 if phase.endswith("even") else 1
    top_y = torch.arange(parity, height, 2, device=device, dtype=torch.int64)
    bottom_y = (top_y + 1) % height
    xs = torch.arange(width, device=device, dtype=torch.int64)
    top_grid, x_grid = torch.meshgrid(top_y, xs, indexing="ij")
    bottom_grid, _ = torch.meshgrid(bottom_y, xs, indexing="ij")
    return top_grid, x_grid, bottom_grid, x_grid


def _blocked_mask(spec: EnvironmentWorldSpec, first_y, first_x, second_y, second_x):
    blocked = {frozenset((edge.first, edge.second)) for edge in spec.blocked_edges}
    mask = torch.zeros(first_x.shape, device="cuda", dtype=torch.bool)
    if not blocked: return mask
    first_x_cpu = first_x.cpu().tolist(); first_y_cpu = first_y.cpu().tolist()
    second_x_cpu = second_x.cpu().tolist(); second_y_cpu = second_y.cpu().tolist()
    values = []
    for row in range(len(first_x_cpu)):
        values.append([frozenset(((first_x_cpu[row][col], first_y_cpu[row][col]),
                                  (second_x_cpu[row][col], second_y_cpu[row][col]))) in blocked
                       for col in range(len(first_x_cpu[row]))])
    return torch.tensor(values, device="cuda", dtype=torch.bool)


def _move(spec: EnvironmentWorldSpec, left, right, limit: int, channel: str, blocked):
    fraction = spec.physical_scale.tick_fraction(channel)
    difference = left - right
    magnitude = torch.abs(difference)
    amount = torch.div(magnitude * fraction.numerator, fraction.denominator, rounding_mode="floor")
    amount = torch.minimum(amount, torch.div(magnitude, 2, rounding_mode="floor"))
    amount = torch.clamp(amount, max=limit)
    amount = torch.where(blocked, torch.zeros_like(amount), amount)
    return torch.where(difference > 0, amount, -amount)


def _dense_state(spec: EnvironmentWorldSpec, state: EnvironmentState):
    height, width = spec.causal_world.kernel.height, spec.causal_world.kernel.width
    shape = (height, width); device = torch.device("cuda")
    heat = torch.zeros(shape, dtype=torch.int64, device=device)
    elevation = torch.zeros(shape, dtype=torch.int64, device=device)
    water = torch.zeros(shape, dtype=torch.int64, device=device)
    mineral = torch.zeros(shape, dtype=torch.int64, device=device)
    vapor = torch.zeros(shape, dtype=torch.int64, device=device)
    solutes = torch.zeros((spec.solute_kinds, height, width), dtype=torch.int64, device=device)
    for item in state.causal.heat: heat[item.y, item.x] = item.energy
    for item in state.cells:
        elevation[item.y, item.x] = item.elevation; water[item.y, item.x] = item.water
        mineral[item.y, item.x] = item.mineral; vapor[item.y, item.x] = item.vapor
        for kind, amount in enumerate(item.solutes): solutes[kind, item.y, item.x] = amount
    return heat, elevation, water, mineral, vapor, solutes


def _gpu_phase(spec: EnvironmentWorldSpec, tensors, phase: str):
    heat, elevation, water, mineral, vapor, solutes = tensors
    first_y, first_x, second_y, second_x = _pair_indices(
        spec.causal_world.kernel.width, spec.causal_world.kernel.height, phase)
    blocked = _blocked_mask(spec, first_y, first_x, second_y, second_x)

    heat_left, heat_right = heat[first_y, first_x], heat[second_y, second_x]
    heat_move = _move(spec, heat_left, heat_right, spec.law.max_heat_transfer, "heat", blocked)

    water_left, water_right = water[first_y, first_x], water[second_y, second_x]
    surface_left = elevation[first_y, first_x] + water_left
    surface_right = elevation[second_y, second_x] + water_right
    water_move = _move(spec, surface_left, surface_right, spec.law.max_water_transfer, "water_surface", blocked)
    water_move = torch.where(water_move > 0, torch.minimum(water_move, water_left),
                             -torch.minimum(-water_move, water_right))
    water_left_after = water_left - water_move; water_right_after = water_right + water_move

    vapor_left, vapor_right = vapor[first_y, first_x], vapor[second_y, second_x]
    vapor_move = _move(spec, vapor_left, vapor_right, spec.law.max_vapor_transfer, "vapor", blocked)

    solute_moves = []
    for kind in range(spec.solute_kinds):
        left = solutes[kind, first_y, first_x]; right = solutes[kind, second_y, second_x]
        carrying_limit = torch.abs(water_move) * spec.law.max_carried_solute_per_water
        left_denominator = torch.clamp(water_left, min=1); right_denominator = torch.clamp(water_right, min=1)
        carried_left = torch.div(left * torch.clamp(water_move, min=0), left_denominator, rounding_mode="floor")
        carried_right = torch.div(right * torch.clamp(-water_move, min=0), right_denominator, rounding_mode="floor")
        carried = torch.where(water_move > 0, torch.minimum(torch.minimum(carrying_limit, carried_left), left),
                    torch.where(water_move < 0, -torch.minimum(torch.minimum(carrying_limit, carried_right), right),
                                torch.zeros_like(left)))
        left_after = left - carried; right_after = right + carried
        diffused = _move(spec, left_after, right_after, spec.law.max_solute_transfer, "solute", blocked)
        wet = (water_left_after > 0) & (water_right_after > 0)
        diffused = torch.where(wet, diffused, torch.zeros_like(diffused))
        diffused = torch.where(diffused > 0, torch.minimum(diffused, left_after),
                               -torch.minimum(-diffused, right_after))
        solute_moves.append(carried + diffused)

    heat[first_y, first_x] = heat_left - heat_move; heat[second_y, second_x] = heat_right + heat_move
    water[first_y, first_x] = water_left_after; water[second_y, second_x] = water_right_after
    vapor[first_y, first_x] = vapor_left - vapor_move; vapor[second_y, second_x] = vapor_right + vapor_move
    for kind, move in enumerate(solute_moves):
        left = solutes[kind, first_y, first_x]; right = solutes[kind, second_y, second_x]
        solutes[kind, first_y, first_x] = left - move; solutes[kind, second_y, second_x] = right + move
    return heat, elevation, water, mineral, vapor, solutes


def _sparse_state(spec: EnvironmentWorldSpec, previous: EnvironmentState, tensors) -> EnvironmentState:
    heat, elevation, water, mineral, vapor, solutes = (item.cpu() for item in tensors)
    height, width = heat.shape
    heat_cells = []
    cells = []
    for y in range(height):
        for x in range(width):
            heat_value = int(heat[y, x])
            if heat_value: heat_cells.append(HeatCellSpec(x, y, heat_value))
            values = tuple(int(solutes[kind, y, x]) for kind in range(spec.solute_kinds))
            elevation_value = int(elevation[y, x]); water_value = int(water[y, x])
            mineral_value = int(mineral[y, x]); vapor_value = int(vapor[y, x])
            if elevation_value or water_value or mineral_value or vapor_value or any(values):
                cells.append(EnvironmentCellSpec(x, y, elevation_value, water_value, mineral_value, values, vapor_value))
    causal = CausalWorldState(previous.tick, previous.causal.particles, tuple(heat_cells), previous.causal.bonds)
    return EnvironmentState(causal, tuple(cells), previous.energy_supplied, previous.energy_removed, previous.format)


def step_cuda_environment_world(spec: EnvironmentWorldSpec, state: EnvironmentState) -> EnvironmentState:
    _require_cuda(spec)
    resources = state.conserved_resources(spec); accounted = state.energy_account(spec)["accounted"]
    causal = step_causal_world(spec.causal_world, state.causal)
    transported = EnvironmentState(causal, state.cells, state.energy_supplied, state.energy_removed, state.format)
    tensors = _dense_state(spec, transported)
    phases = list(spec.law.phase_order); start = state.tick % len(phases)
    with torch.no_grad():
        for phase in phases[start:] + phases[:start]: tensors = _gpu_phase(spec, tensors, phase)
        torch.cuda.synchronize()
    result = _sparse_state(spec, transported, tensors)
    result = _exchange_external_energy(spec, result)
    result = _convert_local_mineral(spec, result)
    result = _change_water_phase(spec, result)
    if result.conserved_resources(spec) != resources: raise AssertionError("CUDA tick changed conserved resources")
    if result.energy_account(spec)["accounted"] != accounted: raise AssertionError("CUDA tick violated energy account")
    return result


@dataclass(frozen=True)
class GpuParityStep:
    tick: int
    cpu_digest: str
    gpu_digest: str

    @property
    def matches(self) -> bool: return self.cpu_digest == self.gpu_digest

    def canonical(self) -> dict[str, object]:
        return {"cpu_digest": self.cpu_digest, "gpu_digest": self.gpu_digest,
                "matches": self.matches, "tick": self.tick}


@dataclass(frozen=True)
class GpuParityReport:
    spec_digest: str
    device: str
    backend_kind: str
    steps: tuple[GpuParityStep, ...]

    @property
    def complete_match(self) -> bool: return all(item.matches for item in self.steps)

    def canonical(self) -> dict[str, object]:
        return {"backend_kind": self.backend_kind, "complete_match": self.complete_match,
                "device": self.device, "format": "deterministic-gpu-parity-v1", "spec_digest": self.spec_digest,
                "steps": [item.canonical() for item in self.steps]}


def run_cpu_cuda_parity(spec: EnvironmentWorldSpec, ticks: int | None = None) -> GpuParityReport:
    _require_cuda(spec)
    horizon = spec.causal_world.ticks if ticks is None else ticks
    if isinstance(horizon, bool) or not isinstance(horizon, int) or not 0 <= horizon <= spec.causal_world.ticks:
        raise ValueError("parity ticks must fit the world execution horizon")
    cpu_state = initial_environment_state(spec); gpu_state = initial_environment_state(spec); steps = []
    for _ in range(horizon):
        cpu_state = step_environment_world(spec, cpu_state)
        gpu_state = step_cuda_environment_world(spec, gpu_state)
        steps.append(GpuParityStep(cpu_state.tick, cpu_state.digest, gpu_state.digest))
    return GpuParityReport(spec.digest, torch.cuda.get_device_name(0),
                           "cuda-int64-transport-with-cpu-local-rules", tuple(steps))



def _require_resident_eligible(spec: EnvironmentWorldSpec) -> None:
    _require_cuda(spec)
    reasons = []
    if spec.causal_world.particles: reasons.append("particles")
    if spec.causal_world.bond_rules: reasons.append("bond_rules")
    if spec.energy_boundaries: reasons.append("energy_boundaries")
    if spec.law.max_mineral_conversion: reasons.append("mineral_conversion")
    if spec.law.max_water_phase_change: reasons.append("water_phase_change")
    if reasons:
        raise ValueError("resident CUDA baseline does not support: " + ", ".join(reasons))


def _horizon(spec: EnvironmentWorldSpec, ticks: int | None) -> int:
    value = spec.causal_world.ticks if ticks is None else ticks
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= spec.causal_world.ticks:
        raise ValueError("resident ticks must fit the world execution horizon")
    return value


def _resident_snapshot(spec: EnvironmentWorldSpec, initial: EnvironmentState, tensors, tick: int) -> EnvironmentState:
    causal = CausalWorldState(tick, initial.causal.particles, (), initial.causal.bonds)
    metadata = EnvironmentState(causal, (), initial.energy_supplied, initial.energy_removed, initial.format)
    return _sparse_state(spec, metadata, tensors)


def run_cuda_resident_fields(spec: EnvironmentWorldSpec, ticks: int | None = None) -> EnvironmentState:
    """Run eligible transport-only v4 worlds with one upload and one final download."""
    _require_resident_eligible(spec)
    horizon = _horizon(spec, ticks)
    initial = initial_environment_state(spec)
    tensors = _dense_state(spec, initial)
    phases = list(spec.law.phase_order)
    with torch.no_grad():
        for tick in range(horizon):
            start = tick % len(phases)
            for phase in phases[start:] + phases[:start]: tensors = _gpu_phase(spec, tensors, phase)
        torch.cuda.synchronize()
    result = _resident_snapshot(spec, initial, tensors, horizon)
    if result.conserved_resources(spec) != initial.conserved_resources(spec):
        raise AssertionError("resident CUDA run changed conserved resources")
    if result.energy_account(spec)["accounted"] != initial.energy_account(spec)["accounted"]:
        raise AssertionError("resident CUDA run violated energy account")
    return result


def verify_cuda_resident_every_tick(spec: EnvironmentWorldSpec, ticks: int | None = None) -> GpuParityReport:
    """Keep fields resident but download snapshots solely for per-tick validation."""
    _require_resident_eligible(spec)
    horizon = _horizon(spec, ticks)
    initial = initial_environment_state(spec); cpu_state = initial
    tensors = _dense_state(spec, initial); phases = list(spec.law.phase_order); steps = []
    with torch.no_grad():
        for tick in range(horizon):
            cpu_state = step_environment_world(spec, cpu_state)
            start = tick % len(phases)
            for phase in phases[start:] + phases[:start]: tensors = _gpu_phase(spec, tensors, phase)
            torch.cuda.synchronize()
            gpu_state = _resident_snapshot(spec, initial, tensors, tick + 1)
            steps.append(GpuParityStep(tick + 1, cpu_state.digest, gpu_state.digest))
    return GpuParityReport(spec.digest, torch.cuda.get_device_name(0), "cuda-resident-int64-fields", tuple(steps))


@dataclass(frozen=True)
class GpuBenchmarkResult:
    grid_size: int
    ticks: int
    cpu_seconds: float
    gpu_seconds: float
    speedup: float
    gpu_peak_bytes: int
    final_digest: str
    complete_match: bool

    def canonical(self) -> dict[str, object]:
        return {"complete_match": self.complete_match, "cpu_seconds": self.cpu_seconds,
                "final_digest": self.final_digest, "gpu_peak_bytes": self.gpu_peak_bytes,
                "gpu_seconds": self.gpu_seconds, "grid_size": self.grid_size,
                "speedup": self.speedup, "ticks": self.ticks}


def benchmark_cuda_resident(sizes=(64, 128, 256, 512), ticks: int = 4) -> tuple[GpuBenchmarkResult, ...]:
    """Measure wall time only; timing never enters physical state or its digest."""
    _require_cuda_for_benchmark = cuda_available()
    if not _require_cuda_for_benchmark: raise RuntimeError("CUDA is not available")
    from .physical_environment_scaling import make_physical_channel_spec
    from .physical_scale import RefinementLevel

    results = []
    for size in sizes:
        level = RefinementLevel(size, 1, 1, ticks)
        spec = make_physical_channel_spec(level, "heat")
        started = time.perf_counter(); cpu = run_environment_world(spec).final_state
        cpu_seconds = time.perf_counter() - started
        torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter(); gpu = run_cuda_resident_fields(spec)
        gpu_seconds = time.perf_counter() - started
        peak = int(torch.cuda.max_memory_allocated())
        results.append(GpuBenchmarkResult(size, ticks, cpu_seconds, gpu_seconds,
                                          cpu_seconds / gpu_seconds if gpu_seconds else 0.0,
                                          peak, gpu.digest, cpu.digest == gpu.digest))
    return tuple(results)
