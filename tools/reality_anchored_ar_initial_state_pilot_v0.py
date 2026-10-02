"""SURVEY_ONLY: one pinned COD crystal -> incomplete structural prototype.

No dynamics, quantization, sampling, network, or production physics imports.
The restricted parser supports this source only; it is not a general CIF reader.
"""
import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path
import re
import shlex

SOURCE_SHA256 = "aca67f14c014e467887cdd678a1b74872c9c1d73a473e52ecd5a3ed8960142b6"
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/proposals/reality_anchor_ar_v0"


def read_pinned_cif(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("SOURCE_HASH_MISMATCH; no reconstruction performed")
    lines = [line.strip() for line in raw.decode("utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    scalars, loops = {}, []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "loop_":
            i += 1
            tags = []
            while i < len(lines) and lines[i].startswith("_"):
                tags.append(lines[i])
                i += 1
            rows = []
            while i < len(lines) and not lines[i].startswith(("_", "loop_", "data_")):
                row = shlex.split(lines[i])
                if len(row) != len(tags):
                    raise ValueError("unsupported multiline CIF loop")
                rows.append(dict(zip(tags, row)))
                i += 1
            loops.append(rows)
            continue
        if line.startswith("_"):
            tokens = shlex.split(line)
            if len(tokens) == 1 and i + 1 < len(lines) and lines[i + 1] == ";":
                tag = tokens[0]
                i += 2
                text = []
                while i < len(lines) and lines[i] != ";":
                    text.append(lines[i])
                    i += 1
                if i == len(lines):
                    raise ValueError("unterminated CIF text field")
                value = "\n".join(text)
            else:
                tag, value = tokens
            scalars[tag] = value
        i += 1
    return scalars, loops


def symmetry_point(expression, point):
    """Apply only signed axis + optional rational translation; never eval."""
    result = []
    for coordinate in expression.split(","):
        match = re.fullmatch(r"(-?)([xyz])([+-]\d+/\d+)?", coordinate)
        if match is None:
            raise ValueError("unsupported symmetry expression")
        sign, axis, offset = match.groups()
        value = point["xyz".index(axis)] * (-1 if sign else 1)
        result.append((value + F(offset or "0")) % 1)
    if len(result) != 3:
        raise ValueError("symmetry must have three coordinates")
    return tuple(result)


def distance_squared(left, right):
    return sum((a - b) ** 2 for a, b in zip(left, right))


def cut_geometry(basis, cell_length):
    """Repeated geometry for neighbour accounting only; no dynamic PBC."""
    nearest_squared = F(1, 2)
    repeated = [tuple(site[k] + shift[k] for k in range(3))
                for shift in itertools.product((-1, 0, 1), repeat=3)
                for site in basis]
    internal = [sum(distance_squared(site, other) == nearest_squared
                    for other in basis) for site in basis]
    bulk = [sum(distance_squared(site, other) == nearest_squared
                for other in repeated) for site in basis]
    missing = [full - inside for full, inside in zip(bulk, internal)]
    return {
        "interpretation": "ideal mean fcc geometry; not instantaneous measured coordination",
        "nearest_distance_squared_angstrom2": str(cell_length ** 2 / 2),
        "internal_nearest_per_site": internal,
        "bulk_nearest_per_site": bulk,
        "missing_nearest_links_per_site": missing,
        "missing_directed_nearest_links": sum(missing),
        "link_count_is_not_distinct_outside_atom_count": True,
        "further_neighbours_also_omitted": True,
        "forces_or_energy_computed": False,
    }


def build_prototype(source=DATA / "1541541.cif"):
    scalars, loops = read_pinned_cif(source)
    atoms = next(rows for rows in loops if rows and "_atom_site_label" in rows[0])
    ops = next(rows for rows in loops if rows and "_symmetry_equiv_pos_as_xyz" in rows[0])
    atom = atoms[0]
    if len(atoms) != 1 or atom["_atom_site_type_symbol"] != "Ar":
        raise ValueError("unsupported source structure")
    origin = tuple(F(atom[f"_atom_site_fract_{axis}"]) for axis in "xyz")
    basis = sorted({symmetry_point(row["_symmetry_equiv_pos_as_xyz"], origin) for row in ops})
    a = F(scalars["_cell_length_a"])
    if len(basis) != 4 or any(F(scalars[f"_cell_length_{axis}"]) != a for axis in "bc"):
        raise ValueError("unsupported cell")
    volume = a ** 3
    return {
        "schema": "reality_anchored_ar_initial_state_pilot_v0",
        "scope": "SURVEY_ONLY_ISOLATED_STRUCTURAL_PROTOTYPE",
        "verdict": "B_STRUCTURE_REALITY_ANCHORED_BUT_DYNAMIC_STATE_INCOMPLETE",
        "reality_grade": "R2",
        "source_type": "experimental-publication-linked curated crystallographic CIF",
        "structure_interpretation": "EXPERIMENTALLY_ANCHORED_RECONSTRUCTION",
        "source": {
            "cod_id": "1541541", "sha256": SOURCE_SHA256,
            "download_url": "https://qiserver.ugr.es/cod/1541541.cif",
            "original_publication": "https://doi.org/10.1038/178483a0",
            "access_date": "2026-10-02",
            "original_fulltext_reaudited": False,
            "raw_symmetry_operations": len(ops),
        },
        "field_status": {
            "species": "DERIVED_FROM_MEASUREMENT",
            "position": "RECONSTRUCTED", "momentum": "UNAVAILABLE",
            "lattice_structure": "DERIVED_FROM_MEASUREMENT",
            "density": "DERIVED_FROM_MEASUREMENT",
            "temperature": "UNAVAILABLE", "pressure": "UNAVAILABLE",
            "boundary_environment": "UNAVAILABLE",
        },
        "species": {"element": "Ar", "isotope": None, "isotope_status": "UNAVAILABLE"},
        "temperature": None, "pressure": None,
        "crystallographic_cell": {
            "length_angstrom_as_recorded": scalars["_cell_length_a"],
            "angles_degree": [scalars[f"_cell_angle_{name}"] for name in ("alpha", "beta", "gamma")],
            "space_group": scalars["_symmetry_space_group_name_H-M"],
            "purpose": "crystallographic frame only; not a simulation box or wall",
            "measurement_uncertainty": None,
        },
        "density": {
            "bulk_template_number_density_atoms_per_angstrom3_rational": str(F(len(basis)) / volume),
            "basis_count": len(basis), "cell_volume_angstrom3_rational": str(volume),
            "mass_density": None,
            "interpretation": "derived nominal mean bulk template; not isolated fragment density",
        },
        "sites": [
            {"reconstruction_index": i + 1, "measured_atom_identity": None,
             "species": "Ar", "isotope": None,
             "fractional_position": [str(v) for v in site],
             "position_angstrom_rational": [str(a * v) for v in site],
             "position_status": "RECONSTRUCTED", "momentum": None,
             "occupancy_as_recorded": atom["_atom_site_occupancy"]}
            for i, site in enumerate(basis)
        ],
        "source_U_iso_or_equiv": {
            "as_recorded": atom["_atom_site_U_iso_or_equiv"],
            "meaning_validated": False,
            "used_to_infer_zero_momentum_or_absent_vibration": False,
        },
        "reconstruction_rules": [
            "Apply all source symmetry operations to source mean site; deduplicate fractional representatives.",
            "Use source nominal cubic cell for Cartesian angstrom coordinates; rational arithmetic is not measurement exactness.",
            "No thermal displacement, defect, isotope, momentum, or boundary reconstruction.",
            "Fractional modulo chooses crystal basis representatives; it does not define A periodic motion.",
        ],
        "cut_analysis": cut_geometry(basis, a),
        "dynamic_state_status": "MISSING_DYNAMIC_STATE",
        "forward_steps_executed": 0,
        "A_input_created": False, "dynamic_boundary": None,
        "C1C_D5": "PENDING", "Small_A_N_selected": False,
        "missing_fields": ["instantaneous_positions", "individual_momenta", "isotope_composition",
                           "temperature", "pressure", "physical_boundary_and_environment",
                           "thermal_and_zero_point_displacements", "defect_map", "measurement_uncertainties"],
        "forward_blockers": ["MISSING_DYNAMIC_STATE", "NO_APPROVED_FOUR_ATOM_DYNAMIC_CONTRACT",
                             "UNRESOLVED_BOUNDARY", "UNVERIFIED_40Ar_MAPPING"],
    }


def serialize(prototype):
    return json.dumps(prototype, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DATA / "1541541.cif")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = serialize(build_prototype(args.source))
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(result)
    print("R2 / MISSING_DYNAMIC_STATE / forward_steps=0")
