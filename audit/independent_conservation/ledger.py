"""Independently recount what a world snapshot contains.

`EnvironmentState.conserved_resources()` and `.total_energy()` are methods on
the same object the kernel mutates, and `step_environment_world` checks its
own output by calling them before and after. If one of those tallies is
wrong — a cell skipped, a pool counted twice, a term omitted — it is wrong by
the same amount on both sides and the tick still reports "conserved".

This module recounts from the recorded snapshot instead. It reads the plain
numbers a trace already stores and the parameters a world spec declares, and
sums them here. It never imports the kernel, so a miscount in the kernel's
own tally does not propagate into this one.

What is counted, and why each term belongs:

    energy    kinetic energy of particles
            + heat held in cells
            + energy stored in bonds
            + dissolved mineral   x mineral_conversion_energy
            + vapor               x vaporization_energy

      Dissolved mineral and vapor carry latent energy: dissolving or
      evaporating stores energy that reappears on precipitation or
      condensation, so both must be counted or a phase change would look
      like energy appearing from nowhere.

    water     liquid water + vapor, since a phase change moves matter between
              the two without creating or destroying any

    inventory solute totals per kind, with solid mineral folded into the
              solute kind it dissolves into, for the same reason

    particles count per material kind

    momentum  mass x kinetic energy x direction, summed over UNBONDED
              particles only, matching the rule that bonded particles are
              held in place
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

# Direction codes as a snapshot records them, mapped to unit vectors with y
# increasing southward. Restated here rather than imported, so a wrong vector
# in one place cannot silently agree with a wrong vector in the other — which
# is also why an unrecognised code is an error rather than a skipped particle.
_VELOCITY: dict[str, tuple[int, int]] = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}

_V2_FORMATS = (
    "deterministic-environment-world-spec-v2",
    "deterministic-environment-world-spec-v3",
    "deterministic-environment-world-spec-v4",
)
_VAPOR_FORMATS = (
    "deterministic-environment-world-spec-v3",
    "deterministic-environment-world-spec-v4",
)


class LedgerError(ValueError):
    """A snapshot or spec cannot be read as an integer world."""


def _integer(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LedgerError(f"{what} must be an integer, found {value!r}")
    return value


@dataclass(frozen=True)
class WorldParameters:
    """The handful of spec numbers a recount needs."""

    format: str
    solute_kinds: int
    mineral_solute_kind: int
    mineral_conversion_energy: int
    vaporization_energy: int
    masses: Mapping[int, int]

    @property
    def counts_vapor(self) -> bool:
        return self.format in _VAPOR_FORMATS

    @property
    def folds_mineral_into_inventory(self) -> bool:
        return self.format in _V2_FORMATS


def read_parameters(spec: Mapping[str, Any]) -> WorldParameters:
    """Pull the recount parameters straight out of a world spec document."""
    if not isinstance(spec, Mapping):
        raise LedgerError("world spec must be a mapping")
    law = spec.get("law") or {}
    causal = spec.get("causal_world") or {}
    masses = {}
    for material in causal.get("materials") or ():
        kind = _integer(material.get("kind"), "material kind")
        masses[kind] = _integer(material.get("mass"), f"mass of kind {kind}")
    return WorldParameters(
        format=str(spec.get("format")),
        solute_kinds=_integer(spec.get("solute_kinds", 0), "solute_kinds"),
        mineral_solute_kind=_integer(law.get("mineral_solute_kind", 0), "mineral_solute_kind"),
        mineral_conversion_energy=_integer(
            law.get("mineral_conversion_energy", 0), "mineral_conversion_energy"),
        vaporization_energy=_integer(law.get("vaporization_energy", 0), "vaporization_energy"),
        masses=masses,
    )


@dataclass(frozen=True)
class Ledger:
    """One independent recount of a snapshot."""

    energy_internal: int
    energy_supplied: int
    energy_removed: int
    water_total: int
    material_inventory: tuple[int, ...]
    particle_counts: tuple[tuple[int, int], ...]
    momentum: tuple[int, int]

    @property
    def energy_accounted(self) -> int:
        """Internal energy adjusted for what crossed the boundary.

        Energy supplied from outside should not read as creation, and energy
        removed should not read as loss, so both are folded back out.
        """
        return self.energy_internal + self.energy_removed - self.energy_supplied

    def canonical(self) -> dict[str, Any]:
        return {
            "energy_accounted": self.energy_accounted,
            "energy_internal": self.energy_internal,
            "energy_removed": self.energy_removed,
            "energy_supplied": self.energy_supplied,
            "material_inventory": list(self.material_inventory),
            "momentum": list(self.momentum),
            "particle_counts": {str(kind): count for kind, count in self.particle_counts},
            "water_total": self.water_total,
        }

    def conserved_part(self) -> dict[str, Any]:
        """The quantities a tick must leave untouched."""
        return {
            "energy_accounted": self.energy_accounted,
            "material_inventory": list(self.material_inventory),
            "particle_counts": {str(kind): count for kind, count in self.particle_counts},
            "water_total": self.water_total,
        }


def recount(snapshot: Mapping[str, Any], parameters: WorldParameters) -> Ledger:
    """Total up a recorded snapshot from its raw numbers."""
    if not isinstance(snapshot, Mapping):
        raise LedgerError("snapshot must be a mapping")
    causal = snapshot.get("causal")
    if not isinstance(causal, Mapping):
        raise LedgerError("snapshot has no causal section")

    particles = causal.get("particles") or ()
    heat_cells = causal.get("heat") or ()
    bonds = causal.get("bonds") or ()
    cells = snapshot.get("cells") or ()

    energy = 0
    counts: dict[int, int] = {}
    bonded: set[Any] = set()
    for bond in bonds:
        energy += _integer(bond.get("stored_energy", 0), "bond stored_energy")
        bonded.add(bond.get("left_id"))
        bonded.add(bond.get("right_id"))

    momentum_x = momentum_y = 0
    for particle in particles:
        kinetic = _integer(particle.get("kinetic_energy", 0), "particle kinetic_energy")
        kind = _integer(particle.get("kind"), "particle kind")
        energy += kinetic
        counts[kind] = counts.get(kind, 0) + 1
        if particle.get("particle_id") in bonded:
            continue
        direction = particle.get("direction")
        if direction not in _VELOCITY:
            raise LedgerError(f"unknown particle direction {direction!r}")
        mass = parameters.masses.get(kind)
        if mass is None:
            raise LedgerError(f"spec declares no mass for particle kind {kind}")
        step_x, step_y = _VELOCITY[direction]
        momentum_x += mass * kinetic * step_x
        momentum_y += mass * kinetic * step_y

    for cell in heat_cells:
        energy += _integer(cell.get("energy", 0), "heat cell energy")

    water = vapor = 0
    solutes = [0] * parameters.solute_kinds
    mineral = 0
    for cell in cells:
        water += _integer(cell.get("water", 0), "cell water")
        mineral += _integer(cell.get("mineral", 0), "cell mineral")
        if parameters.counts_vapor:
            vapor += _integer(cell.get("vapor", 0), "cell vapor")
        recorded = cell.get("solutes") or ()
        for index in range(parameters.solute_kinds):
            if index < len(recorded):
                solutes[index] += _integer(recorded[index], f"cell solute {index}")

    if parameters.folds_mineral_into_inventory:
        dissolved = solutes[parameters.mineral_solute_kind] if solutes else 0
        energy += dissolved * parameters.mineral_conversion_energy
        inventory = list(solutes)
        inventory[parameters.mineral_solute_kind] += mineral
    else:
        inventory = list(solutes)

    if parameters.counts_vapor:
        energy += vapor * parameters.vaporization_energy

    return Ledger(
        energy_internal=energy,
        energy_supplied=_integer(snapshot.get("energy_supplied", 0), "energy_supplied"),
        energy_removed=_integer(snapshot.get("energy_removed", 0), "energy_removed"),
        water_total=water + vapor,
        material_inventory=tuple(inventory),
        particle_counts=tuple(sorted(counts.items())),
        momentum=(momentum_x, momentum_y),
    )
