"""B0.2 exact physical scale and diffusive-flux contract.

The contract uses integer SI sub-units and exact rational coefficients. It does
not claim that the example values match early Earth; they are calibration-free
reference values for resolution equivalence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _positive(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class PhysicalUnitContract:
    height_quantum_pm: int
    matter_quantum_yoctomol: int
    energy_quantum_zj: int

    def __post_init__(self) -> None:
        _positive(self.height_quantum_pm, "height_quantum_pm")
        _positive(self.matter_quantum_yoctomol, "matter_quantum_yoctomol")
        _positive(self.energy_quantum_zj, "energy_quantum_zj")

    def canonical(self) -> dict[str, object]:
        return {
            "cell_length_unit": "picometer",
            "energy_quantum_unit": "zeptojoule",
            "energy_quantum_zj": self.energy_quantum_zj,
            "height_quantum_pm": self.height_quantum_pm,
            "matter_quantum_unit": "yoctomole",
            "matter_quantum_yoctomol": self.matter_quantum_yoctomol,
            "tick_duration_unit": "femtosecond",
        }


@dataclass(frozen=True, order=True)
class RefinementLevel:
    grid_size: int
    cell_length_pm: int
    tick_duration_fs: int
    ticks: int

    def __post_init__(self) -> None:
        if self.grid_size < 4 or self.grid_size % 2:
            raise ValueError("grid_size must be an even integer of at least 4")
        _positive(self.cell_length_pm, "cell_length_pm")
        _positive(self.tick_duration_fs, "tick_duration_fs")
        _positive(self.ticks, "ticks")

    @property
    def domain_length_pm(self) -> int: return self.grid_size * self.cell_length_pm

    @property
    def observed_duration_fs(self) -> int: return self.ticks * self.tick_duration_fs

    def canonical(self) -> dict[str, int]:
        return {"cell_length_pm": self.cell_length_pm, "grid_size": self.grid_size,
                "tick_duration_fs": self.tick_duration_fs, "ticks": self.ticks}


@dataclass(frozen=True, order=True)
class DiffusiveFluxLaw:
    channel: str
    diffusivity_numerator_pm2: int
    diffusivity_denominator_fs: int

    def __post_init__(self) -> None:
        if self.channel not in ("heat", "solute", "vapor", "water_surface"):
            raise ValueError("unsupported diffusive channel")
        _positive(self.diffusivity_numerator_pm2, "diffusivity_numerator_pm2")
        _positive(self.diffusivity_denominator_fs, "diffusivity_denominator_fs")

    @property
    def diffusivity(self) -> Fraction:
        return Fraction(self.diffusivity_numerator_pm2, self.diffusivity_denominator_fs)

    def tick_fraction(self, level: RefinementLevel) -> Fraction:
        return self.diffusivity * level.tick_duration_fs / (level.cell_length_pm ** 2)

    def canonical(self) -> dict[str, object]:
        return {"channel": self.channel, "diffusivity": {
            "denominator_fs": self.diffusivity_denominator_fs,
            "numerator_pm2": self.diffusivity_numerator_pm2,
        }}


@dataclass(frozen=True)
class PhysicalScaleFamily:
    units: PhysicalUnitContract
    levels: tuple[RefinementLevel, ...]
    flux_laws: tuple[DiffusiveFluxLaw, ...]

    def __post_init__(self) -> None:
        if len(self.levels) < 2: raise ValueError("a scale family needs at least two refinement levels")
        if len({x.grid_size for x in self.levels}) != len(self.levels): raise ValueError("grid sizes must be unique")
        if len({x.channel for x in self.flux_laws}) != len(self.flux_laws): raise ValueError("flux channels must be unique")
        domains = {x.domain_length_pm for x in self.levels}
        durations = {x.observed_duration_fs for x in self.levels}
        if len(domains) != 1: raise ValueError("all refinement levels must cover the same physical domain")
        if len(durations) != 1: raise ValueError("all refinement levels must cover the same physical duration")
        for law in self.flux_laws:
            fractions = {law.tick_fraction(level) for level in self.levels}
            if len(fractions) != 1:
                raise ValueError(f"{law.channel} must keep D*dt/dx^2 identical across refinement levels")
            if next(iter(fractions)) > Fraction(1, 4):
                raise ValueError(f"{law.channel} explicit diffusion fraction exceeds the 1/4 stability bound")

    @property
    def domain_length_pm(self) -> int: return self.levels[0].domain_length_pm

    @property
    def observed_duration_fs(self) -> int: return self.levels[0].observed_duration_fs

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"flux_laws": [x.canonical() for x in self.flux_laws], "format": "physical-scale-contract-v1",
                "levels": [x.canonical() for x in self.levels], "units": self.units.canonical()}


def scaled_diffusive_transfer(difference: int, law: DiffusiveFluxLaw, level: RefinementLevel) -> int:
    if isinstance(difference, bool) or not isinstance(difference, int):
        raise ValueError("field difference must be an integer")
    if abs(difference) < 2: return 0
    fraction = law.tick_fraction(level)
    amount = abs(difference) * fraction.numerator // fraction.denominator
    amount = min(amount, abs(difference) // 2)
    return amount if difference > 0 else -amount


def reference_scale_family() -> PhysicalScaleFamily:
    levels = (
        RefinementLevel(16, 4, 16, 1),
        RefinementLevel(32, 2, 4, 4),
        RefinementLevel(64, 1, 1, 16),
    )
    laws = tuple(DiffusiveFluxLaw(channel, 1, 4)
                 for channel in ("heat", "solute", "vapor", "water_surface"))
    return PhysicalScaleFamily(PhysicalUnitContract(1, 1, 1), levels, laws)


def _edges(size: int, phase: int):
    if phase < 2:
        parity = phase
        for y in range(size):
            for x in range(parity, size, 2): yield (x, y), ((x + 1) % size, y)
    else:
        parity = phase - 2
        for x in range(size):
            for y in range(parity, size, 2): yield (x, y), (x, (y + 1) % size)


def _initial_heat(level: RefinementLevel, energy_density_quanta_per_pm2: int = 256) -> dict[tuple[int, int], int]:
    _positive(energy_density_quanta_per_pm2, "energy_density_quanta_per_pm2")
    physical_patch_side_pm = 16
    if physical_patch_side_pm % level.cell_length_pm:
        raise ValueError("reference heat patch must align to every refinement level")
    side = physical_patch_side_pm // level.cell_length_pm
    start = level.grid_size // 2 - side // 2
    energy_per_cell = energy_density_quanta_per_pm2 * level.cell_length_pm ** 2
    return {(x, y): energy_per_cell for y in range(start, start + side) for x in range(start, start + side)}


def _step_heat(values: dict[tuple[int, int], int], law: DiffusiveFluxLaw,
               level: RefinementLevel, tick: int) -> dict[tuple[int, int], int]:
    result = dict(values)
    phases = tuple((tick + offset) % 4 for offset in range(4))
    for phase in phases:
        before = dict(result); after = dict(result)
        for first, second in _edges(level.grid_size, phase):
            transfer = scaled_diffusive_transfer(before.get(first, 0) - before.get(second, 0), law, level)
            if transfer:
                after[first] = after.get(first, 0) - transfer
                after[second] = after.get(second, 0) + transfer
        result = {point: amount for point, amount in after.items() if amount}
    return result


def _heat_moment(values: dict[tuple[int, int], int], level: RefinementLevel) -> Fraction:
    domain = level.domain_length_pm
    center2 = domain
    weighted = 0
    total = sum(values.values())
    for (x, y), energy in values.items():
        x2 = (2 * x + 1) * level.cell_length_pm
        y2 = (2 * y + 1) * level.cell_length_pm
        dx2 = min((x2 - center2) % (2 * domain), (center2 - x2) % (2 * domain))
        dy2 = min((y2 - center2) % (2 * domain), (center2 - y2) % (2 * domain))
        weighted += energy * (dx2 * dx2 + dy2 * dy2)
    return Fraction(weighted, total * (2 * domain) ** 2)


@dataclass(frozen=True)
class PhysicalHeatObservation:
    level: RefinementLevel
    initial_energy: int
    final_energy: int
    normalized_second_moment: Fraction
    final_field_digest: str

    def canonical(self) -> dict[str, object]:
        moment = self.normalized_second_moment
        return {"final_energy": self.final_energy, "final_field_digest": self.final_field_digest,
                "initial_energy": self.initial_energy, "level": self.level.canonical(),
                "normalized_second_moment": {"numerator": moment.numerator, "denominator": moment.denominator}}


@dataclass(frozen=True)
class PhysicalScaleAudit:
    contract_digest: str
    observations: tuple[PhysicalHeatObservation, ...]
    successive_differences: tuple[Fraction, ...]
    differences_decrease: bool
    heat_reference_status: str
    full_environment_status: str
    rejected_low_density_status: str
    rejected_low_density_differences: tuple[Fraction, ...]

    @property
    def digest(self) -> str: return _digest(self.canonical())

    def canonical(self) -> dict[str, object]:
        return {"contract_digest": self.contract_digest, "differences_decrease": self.differences_decrease,
                "format": "physical-scale-audit-v1", "full_environment_status": self.full_environment_status,
                "heat_reference_status": self.heat_reference_status,
                "observations": [x.canonical() for x in self.observations],
                "rejected_low_density_differences": [
                    {"numerator": x.numerator, "denominator": x.denominator}
                    for x in self.rejected_low_density_differences],
                "rejected_low_density_status": self.rejected_low_density_status,
                "successive_differences": [{"numerator": x.numerator, "denominator": x.denominator}
                                           for x in self.successive_differences]}


def _heat_observations(family: PhysicalScaleFamily, law: DiffusiveFluxLaw,
                       density: int) -> tuple[PhysicalHeatObservation, ...]:
    observations = []
    for level in family.levels:
        values = _initial_heat(level, density); initial = sum(values.values())
        for tick in range(level.ticks): values = _step_heat(values, law, level, tick)
        observations.append(PhysicalHeatObservation(level, initial, sum(values.values()),
                            _heat_moment(values, level), _digest([[*point, value] for point, value in sorted(values.items())])))
    return tuple(observations)


def _successive_differences(observations: tuple[PhysicalHeatObservation, ...]) -> tuple[Fraction, ...]:
    return tuple(abs(observations[index + 1].normalized_second_moment -
                     observations[index].normalized_second_moment)
                 for index in range(len(observations) - 1))


def run_physical_scale_audit() -> PhysicalScaleAudit:
    family = reference_scale_family()
    law = next(x for x in family.flux_laws if x.channel == "heat")
    observations = _heat_observations(family, law, 256)
    differences = _successive_differences(observations)
    decreasing = bool(differences) and all(b <= a for a, b in zip(differences, differences[1:]))
    low_density = _heat_observations(family, law, 16)
    low_differences = _successive_differences(low_density)
    low_decreasing = bool(low_differences) and all(b <= a for a, b in zip(low_differences, low_differences[1:]))
    return PhysicalScaleAudit(
        family.digest, observations, differences, decreasing,
        "candidate-converging" if decreasing else "not-converging",
        "not-integrated: A2.2 still uses lattice transfer limits rather than this physical flux contract",
        ("unexpected-pass" if low_decreasing else
         "rejected-low-density: integer truncation stalls fine-grid diffusion"),
        low_differences,
    )



@dataclass(frozen=True)
class PhysicalWorldScale:
    units: PhysicalUnitContract
    cell_length_pm: int
    tick_duration_fs: int
    flux_laws: tuple[DiffusiveFluxLaw, ...]

    def __post_init__(self) -> None:
        _positive(self.cell_length_pm, "cell_length_pm")
        _positive(self.tick_duration_fs, "tick_duration_fs")
        if {x.channel for x in self.flux_laws} != {"heat", "solute", "vapor", "water_surface"}:
            raise ValueError("physical world scale needs exactly the four transport channels")
        probe = RefinementLevel(4, self.cell_length_pm, self.tick_duration_fs, 1)
        for law in self.flux_laws:
            if law.tick_fraction(probe) > Fraction(1, 4):
                raise ValueError(f"{law.channel} explicit diffusion fraction exceeds the 1/4 stability bound")

    def law(self, channel: str) -> DiffusiveFluxLaw:
        try:
            return next(x for x in self.flux_laws if x.channel == channel)
        except StopIteration as exc:
            raise ValueError(f"missing physical flux law for {channel}") from exc

    def tick_fraction(self, channel: str) -> Fraction:
        level = RefinementLevel(4, self.cell_length_pm, self.tick_duration_fs, 1)
        return self.law(channel).tick_fraction(level)

    def transfer(self, difference: int, channel: str, limit: int) -> int:
        level = RefinementLevel(4, self.cell_length_pm, self.tick_duration_fs, 1)
        scaled = scaled_diffusive_transfer(difference, self.law(channel), level)
        if limit == 0:
            return 0
        return max(-limit, min(limit, scaled))

    def canonical(self) -> dict[str, object]:
        return {"cell_length_pm": self.cell_length_pm, "flux_laws": [x.canonical() for x in self.flux_laws],
                "tick_duration_fs": self.tick_duration_fs, "units": self.units.canonical()}
