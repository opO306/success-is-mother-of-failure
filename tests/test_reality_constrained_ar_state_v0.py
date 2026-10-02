"""Input faults, independent arithmetic checks, and honest proxy classification."""
import ast
from copy import deepcopy
from decimal import getcontext, ROUND_DOWN
from fractions import Fraction as F
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools import reality_constrained_ar_state_v0 as g


@pytest.fixture(scope="module")
def stored():
    return json.loads((g.DATA / "generated_state_examples.json").read_text(encoding="utf-8"))


def test_source_protocol_and_original_execution_seal_bind():
    source, protocol = g.inputs()
    assert source["number_density_m3"]["status"] == "UNAVAILABLE"
    assert source["structure_statistics"]["status"] == "UNAVAILABLE"
    assert source["species"]["isotope_composition"] is None
    assert protocol["N_candidates"] == [4, 8, 16, 32, 64]
    seal = json.loads((g.DATA / "execution_seal_v0.json").read_text(encoding="utf-8"))
    assert seal["source_sha256"] == g.SOURCE_SHA
    assert seal["protocol_sha256"] == g.PROTOCOL_SHA


def test_reality_only_path_refuses_before_assumed_state_is_built():
    with pytest.raises(g.Refused, match="REALITY_DATA_INSUFFICIENT"):
        g.generate(4, "Q1_GRID", "P1_CARTESIAN_QUANTILES")
    with pytest.raises(g.Refused, match="STRUCTURE_STATISTICS_UNAVAILABLE"):
        g.positions(4, "Q3_EXPERIMENTAL_RECONSTRUCTION")


@pytest.mark.parametrize("mutation", ["one_byte", "temperature", "density"])
def test_input_mutations_are_refused_without_extrapolation(tmp_path, mutation):
    raw = (g.DATA / "source_manifest.json").read_bytes()
    if mutation == "one_byte":
        changed = raw + b" "
    else:
        data = json.loads(raw)
        if mutation == "temperature":
            data["temperature_K"]["value"] = "300"
        else:
            data["number_density_m3"]["value"] = "-1"
        changed = json.dumps(data).encode("utf-8")
    path = tmp_path / "bad.json"
    path.write_bytes(changed)
    with pytest.raises(g.Refused, match="INPUT_BYTES_CHANGED"):
        g.generate(4, "Q1_GRID", "P1_CARTESIAN_QUANTILES", source=path, conditional_proxy=True)


@pytest.mark.parametrize("n", [0, 3, 65, True, 4.0])
def test_unsupported_particle_counts_refuse(n):
    with pytest.raises(g.Refused, match="UNSUPPORTED_N"):
        g.positions(n, "Q2_HALTON")


@pytest.mark.parametrize("n", g.NS)
def test_changing_N_changes_state_and_volume_without_official_N_selection(n, stored):
    examples = [x for x in stored["examples"] if x["N_survey_only"] == n]
    assert len(examples) == 6
    for state in examples:
        assert len(state["records"]) == n
        expected_density = F(80900) / (g.KB_SI * F("273.16"))
        assert F(state["number_density_proxy_m3_exact"]) == expected_density
        assert F(state["box_cube_volume_bohr3_exact"]) == F(n) / expected_density / g.A0_M ** 3
        assert state["N_survey_only"] == n and state["C1C_D5"] == "PENDING"


@pytest.mark.parametrize("index", range(30))
def test_all_stored_states_have_exact_P_K_and_label_independent_physical_records(index, stored):
    state = stored["examples"][index]
    n = state["N_survey_only"]
    records = deepcopy(state["records"])
    coeffs = [tuple(map(F, r["p_coefficient"])) for r in records]
    assert [sum(v[a] for v in coeffs) for a in range(3)] == [0, 0, 0]
    energy = sum(sum(x*x for x in v) for v in coeffs) * g.KB_AU * F("273.16") / 2
    assert energy == F(state["statistics"]["K_hartree_exact"])
    canonical = g.canonical_physical_records(records)
    # Rename every storage label and permute record order, retaining each q,p pair.
    for i, row in enumerate(records):
        row["storage_index"] = "renamed_" + str(n - i)
    records.reverse()
    assert g.canonical_physical_records(records) == canonical
    assert state["reality_only_eligible"] is False
    assert state["production_A_input"] is False
    assert state["field_status"]["number_density"] == "ASSUMED"
    assert state["forward_steps"] == 0


def test_known_artificial_structures_are_exposed_not_repaired(stored):
    grid = g.positions(4, "Q1_GRID")
    rank = g.positions(4, "Q4_RANK1")
    assert len({v[0] for v in grid}) == 1  # literal planar slab
    assert all(v[0] == v[2] for v in rank)
    for state in stored["examples"]:
        if state["P_method"] == "P1_CARTESIAN_QUANTILES":
            assert state["statistics"]["octant_counts"] == {"+++": state["N_survey_only"]//2,
                                                              "---": state["N_survey_only"]//2}
    small = next(x for x in stored["examples"] if x["N_survey_only"] == 4)
    assert F(small["statistics"]["Tkin_over_targetT_COM_removed"]) != 1
    assert stored["winner"] is None
    assert stored["verdict"] == "E_REALITY_DATA_INSUFFICIENT"


def test_antipodal_diagnostic_detects_a_mutated_vector():
    q = g.positions(4, "Q2_HALTON")
    p = list(g.momenta_coefficients(4, "P1_CARTESIAN_QUANTILES"))
    assert g.statistics(q, p, F("273.16"))["exact_antipodal_pairs"] == 2
    p[0] = (p[0][0] + 1, p[0][1], p[0][2])
    measured = g.statistics(q, p, F("273.16"))
    assert measured["exact_antipodal_pairs"] == 1
    assert measured["total_momentum_coefficient_exact"] != [0, 0, 0]


def test_quantile_proxies_against_independent_binary_libm_CDF():
    # Independent numerical check only; libm is absent from the generator.
    for probability, kind in [(F(7, 8), "normal"), (F(3, 4), "maxwell")]:
        value = float(g.quantile(probability, kind))
        check = (1 + math.erf(value / math.sqrt(2))) / 2 if kind == "normal" else (
            math.erf(value / math.sqrt(2)) - math.sqrt(2/math.pi)*value*math.exp(-value*value/2))
        assert abs(check - float(probability)) < 2e-15
    with pytest.raises(g.Refused, match="UNSUPPORTED_QUANTILE"):
        g.quantile(F(1)-F(1,10**60), "maxwell")


@pytest.mark.parametrize("j", [0, 1, 5, 31])
def test_rational_sphere_has_exact_unit_norm(j):
    point = g.rational_sphere_direction(j, 32)
    assert sum(x*x for x in point) == 1


@pytest.mark.parametrize("degree,value,expected", [(2,F(9,4),2),(2,F(25,4),2),
                                                   (3,F(27,8),2),(3,F(125,8),2)])
def test_exact_root_half_ties_and_sign(degree,value,expected):
    assert g.round_algebraic(1,value,degree,0) == expected
    assert g.round_algebraic(-1,value,degree,0) == -expected


def test_fx_projection_independent_midpoint_bounds_and_exact_energy(stored):
    for state in stored["examples"]:
        fx = state["FX_observation"]
        total_p = [sum(F(row[a],1<<80) for row in fx["p_raw"]) for a in range(3)]
        assert total_p == [0,0,0]
        after_K = sum(sum(F(x,1<<80)**2 for x in row) for row in fx["p_raw"])/(2*g.MASS_AU)
        assert after_K == F(fx["K_after_exact_hartree"])
        assert after_K - F(fx["K_before_exact_hartree"]) == F(fx["K_change_exact_hartree"])
        for kind, degree, bits, scale in [("q",3,48,F(state["box_cube_volume_bohr3_exact"])),
                                         ("p",2,80,F(state["momentum_scale_squared_exact"]))]:
            for record, raw in zip(state["records"],fx[kind+"_raw"]):
                for c, r in zip(record[kind+"_coefficient"],raw):
                    value_power = abs(F(c))**degree * scale
                    lower = max(F(0),F(2*abs(r)-1,2*(1<<bits)))
                    upper = F(2*abs(r)+1,2*(1<<bits))
                    assert lower**degree <= value_power <= upper**degree
        assert F(fx["max_abs_q_change_upper_bohr"]) <= F(1,1<<49)+F(1,1<<150)
        assert not fx["initial_state_changed_to_help_quantization"]


def test_impossible_separation_and_unsealed_override_are_refused_without_repair():
    q = g.positions(4,"Q2_HALTON")
    saved = deepcopy(q)
    with pytest.raises(g.Refused,match="MINIMUM_SEPARATION_FAILED"):
        g.check_minimum_separation(q,F(1),F(100))
    assert q == saved
    with pytest.raises(g.Refused,match="UNSUPPORTED_MINIMUM_SEPARATION"):
        g.generate(4,"Q1_GRID","P1_CARTESIAN_QUANTILES",conditional_proxy=True,minimum_separation_angstrom=0)


def test_uniform_cube_reference_is_a_normalized_proxy():
    bins = g.uniform_cube_proxy()
    assert bins[-1] == 1
    assert list(bins) == sorted(bins)
    # Same independent cube is symmetric in each coordinate; triangle weights sum1.
    assert sum(F(63-2*j,1024) for j in range(32)) == 1


def test_fresh_processes_numeric_context_and_locale_environment_produce_same_bytes():
    code = "from decimal import getcontext, ROUND_DOWN; getcontext().prec={prec}; getcontext().rounding=ROUND_DOWN; from tools import reality_constrained_ar_state_v0 as g; print(g.serialize(g.generate(8,'Q2_HALTON','P2_RADIAL_SPHERE_ANTIPODAL',conditional_proxy=True)),end='')"
    outputs=[]
    for precision,locale_env,hash_seed in [(8,"C","0"),(50,"C.UTF-8","987")]:
        env=dict(os.environ,LC_ALL=locale_env,PYTHONHASHSEED=hash_seed,PYTHONIOENCODING="utf-8")
        outputs.append(subprocess.check_output([sys.executable,"-c",code.format(prec=precision)],cwd=g.ROOT,env=env))
    assert outputs[0] == outputs[1]


def test_known_candidate_refusal_is_preserved_and_global_source_failure_stops(monkeypatch):
    g.inputs()
    def fake(n,q,p,**kwargs):
        if n == 4 and q == "Q1_GRID":
            raise g.Refused("injected_case_failure")
        return {"N":n,"Q":q,"P":p}
    monkeypatch.setattr(g,"generate",fake)
    result=g.campaign()
    assert len(result["examples"]) == 30
    assert sum(row.get("status")=="REFUSED" for row in result["examples"]) == 2
    assert all(row["state_repaired"] is False for row in result["examples"] if row.get("status")=="REFUSED")


def test_generator_has_no_binary_floats_or_physics_random_network_imports():
    tree=ast.parse(Path(g.__file__).read_text(encoding="utf-8"))
    assert not any(isinstance(node,ast.Constant) and isinstance(node.value,float) for node in ast.walk(tree))
    modules={alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names}
    modules|={node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)}
    assert modules <= {"argparse","collections","decimal","fractions","functools","hashlib","itertools","json","pathlib"}
