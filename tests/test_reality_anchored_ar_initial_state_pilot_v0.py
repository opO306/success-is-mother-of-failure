"""Offline provenance, incomplete-state, and independent FCC cut checks."""
import ast
from fractions import Fraction as F
import hashlib
import itertools
import json

import pytest

from tools import reality_anchored_ar_initial_state_pilot_v0 as pilot


def test_archive_preserves_download_bytes_and_known_mean_fcc_basis():
    raw = (pilot.DATA / "1541541.cif").read_bytes()
    assert len(raw) == 4438
    assert hashlib.sha256(raw).hexdigest() == pilot.SOURCE_SHA256
    output = pilot.build_prototype()
    assert output["source"]["raw_symmetry_operations"] == 192
    assert [site["position_angstrom_rational"] for site in output["sites"]] == [
        ["0", "0", "0"], ["0", "27/10", "27/10"],
        ["27/10", "0", "27/10"], ["27/10", "27/10", "0"]]


def test_incomplete_mean_structure_is_never_promoted_to_dynamic_state():
    output = pilot.build_prototype()
    assert output["reality_grade"] == "R2"
    assert output["dynamic_state_status"] == "MISSING_DYNAMIC_STATE"
    assert output["forward_steps_executed"] == 0
    assert output["A_input_created"] is False
    assert output["species"]["isotope"] is None
    assert output["temperature"] is output["pressure"] is output["dynamic_boundary"] is None
    assert output["C1C_D5"] == "PENDING"
    assert not output["Small_A_N_selected"]
    assert all(site["momentum"] is None and site["measured_atom_identity"] is None
               for site in output["sites"])
    assert output["source_U_iso_or_equiv"]["as_recorded"] == "0.0"
    assert not output["source_U_iso_or_equiv"]["used_to_infer_zero_momentum_or_absent_vibration"]
    assert "UNVERIFIED_40Ar_MAPPING" in output["forward_blockers"]


def test_cut_counts_against_independent_integer_parity_fcc():
    # Independent representation: FCC = half-grid integer triples with even sum.
    patch = [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)]
    bulk = [v for v in itertools.product(range(-3, 5), repeat=3) if sum(v) % 2 == 0]
    internal, full = [], []
    for site in patch:
        internal.append(sum(sum((x - y) ** 2 for x, y in zip(site, v)) == 2 for v in patch))
        full.append(sum(sum((x - y) ** 2 for x, y in zip(site, v)) == 2 for v in bulk))
    output = pilot.build_prototype()["cut_analysis"]
    assert output["internal_nearest_per_site"] == internal == [3] * 4
    assert output["bulk_nearest_per_site"] == full == [12] * 4
    assert output["missing_directed_nearest_links"] == 36
    assert output["nearest_distance_squared_angstrom2"] == "729/50"
    assert not output["forces_or_energy_computed"]


@pytest.mark.parametrize("replacement", [b"5.4", b"_diffrn_ambient_temperature 4.2\n"])
def test_source_mutation_refuses_instead_of_silently_filling_missing_fields(tmp_path, replacement):
    raw = (pilot.DATA / "1541541.cif").read_bytes()
    changed = raw.replace(b"5.4", b"5.5", 1) if replacement == b"5.4" else raw + replacement
    source = tmp_path / "changed.cif"
    source.write_bytes(changed)
    with pytest.raises(ValueError, match="SOURCE_HASH_MISMATCH"):
        pilot.build_prototype(source)


@pytest.mark.parametrize("expression", ["__import__('os'),y,z", "x*x,y,z", "x,y", "x+0.5,y,z"])
def test_symmetry_grammar_rejects_code_or_unsupported_notation(expression):
    with pytest.raises(ValueError):
        pilot.symmetry_point(expression, (F(0), F(0), F(0)))


def test_stored_artifact_is_offline_reproducible_and_nominal_density_consistent():
    stored = (pilot.DATA / "initial_state_prototype_v0.json").read_text(encoding="utf-8")
    assert stored == pilot.serialize(pilot.build_prototype())
    output = json.loads(stored)
    density = output["density"]
    assert F(density["bulk_template_number_density_atoms_per_angstrom3_rational"]) == F(4) / F("157.464")
    assert density["mass_density"] is None
    assert set(output["field_status"]) == {
        "species", "position", "momentum", "lattice_structure", "density", "temperature", "pressure", "boundary_environment"}


def test_script_has_only_a_small_standard_library_import_allowlist():
    tree = ast.parse((pilot.ROOT / "tools/reality_anchored_ar_initial_state_pilot_v0.py").read_text(encoding="utf-8"))
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports <= {"argparse", "fractions", "hashlib", "itertools", "json", "pathlib", "re", "shlex"}
