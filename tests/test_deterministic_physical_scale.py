import inspect
from dataclasses import replace
from fractions import Fraction

import pytest

from engine.deterministic import (
    DiffusiveFluxLaw,
    PhysicalScaleFamily,
    reference_scale_family,
    run_physical_scale_audit,
    scaled_diffusive_transfer,
)
import engine.deterministic.physical_scale as physical_scale_module


def test_reference_family_seals_same_domain_duration_and_diffusion_fraction() -> None:
    family = reference_scale_family()

    assert family.domain_length_pm == 64
    assert family.observed_duration_fs == 16
    assert tuple(x.grid_size for x in family.levels) == (16, 32, 64)
    for law in family.flux_laws:
        assert {law.tick_fraction(level) for level in family.levels} == {Fraction(1, 4)}


def test_scale_family_rejects_mismatched_domain_or_duration() -> None:
    family = reference_scale_family()
    bad_domain = replace(family.levels[-1], cell_length_pm=2)
    with pytest.raises(ValueError, match="same physical domain"):
        PhysicalScaleFamily(family.units, family.levels[:-1] + (bad_domain,), family.flux_laws)

    bad_duration = replace(family.levels[-1], ticks=15)
    with pytest.raises(ValueError, match="same physical duration"):
        PhysicalScaleFamily(family.units, family.levels[:-1] + (bad_duration,), family.flux_laws)


def test_scale_family_rejects_unstable_explicit_diffusion() -> None:
    family = reference_scale_family()
    unstable = (DiffusiveFluxLaw("heat", 1, 2),)

    with pytest.raises(ValueError, match="stability bound"):
        PhysicalScaleFamily(family.units, family.levels, unstable)


def test_scaled_flux_uses_exact_dt_over_dx_squared() -> None:
    family = reference_scale_family(); law = family.flux_laws[0]

    assert [scaled_diffusive_transfer(64, law, level) for level in family.levels] == [16, 16, 16]
    assert [scaled_diffusive_transfer(-64, law, level) for level in family.levels] == [-16, -16, -16]


def test_heat_refinement_keeps_physical_energy_equal() -> None:
    audit = run_physical_scale_audit()

    assert {x.initial_energy for x in audit.observations} == {65536}
    assert {x.final_energy for x in audit.observations} == {65536}
    assert audit.differences_decrease is True
    assert audit.heat_reference_status == "candidate-converging"
    assert audit.rejected_low_density_status.startswith("rejected-low-density")
    assert audit.rejected_low_density_differences[1] > audit.rejected_low_density_differences[0]


def test_audit_does_not_claim_full_environment_integration() -> None:
    audit = run_physical_scale_audit()

    assert audit.full_environment_status.startswith("not-integrated")
    assert "lattice transfer limits" in audit.full_environment_status


def test_physical_scale_audit_is_deterministic() -> None:
    first = run_physical_scale_audit(); second = run_physical_scale_audit()

    assert first == second
    assert first.digest == second.digest


def test_physical_scale_contract_uses_no_random_or_floating_point() -> None:
    source = inspect.getsource(physical_scale_module)

    assert "import random" not in source
    assert "SeededEventSource" not in source
    assert "float(" not in source
    assert "Fraction" in source
