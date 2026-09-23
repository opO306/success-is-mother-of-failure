"""The independent v5 audit recounts runs from JSON and does not trust the executor."""
from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from audit.independent_v5 import audit_run
from tests.test_v5_reference import _chain, _mixed, free, run, world

ROOT = Path(__file__).resolve().parents[1]


def test_v5_audit_imports_nothing_from_engine() -> None:
    offenders = []
    for path in sorted((ROOT / "audit" / "independent_v5").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            offenders += [f"{path.name}:{node.lineno} {n}" for n in names if n == "engine" or n.startswith("engine.")]
    assert offenders == []


def _grow_with_energy():
    return world([("a", 0, 0, 0), ("b", 0, 1, 0), ("c", 0, 5, 0)],
                 [{"members": ["a", "b"], "bonds": [["a", "E", "b", "W"]], "internal_energy": 5}, free("c", (-2, 0))])


def _off_axis():
    """A face contact off the line of centres: angular-momentum residual 1/2."""
    return world([("a", 0, 0, 0), ("b", 0, 3, "1/2")], [free("a", (1, 0)), free("b", (-1, 0))])


def test_off_axis_merge_has_a_nonzero_residual() -> None:
    from fractions import Fraction
    assert run(_off_axis()).events[0].angular_momentum_residual == Fraction(1, 2)


def test_a_wrong_angular_momentum_residual_is_caught() -> None:
    spec = _off_axis()
    document = copy.deepcopy(run(spec).canonical())
    document["events"][0]["angular_momentum_residual"] = [0, 1]
    assert any("angular-momentum residual" in p for p in audit_run(spec.canonical(), document))


def test_the_audit_refuses_bool_numbers() -> None:
    spec = _chain()
    document = copy.deepcopy(run(spec).canonical())
    document["events"][0]["kinetic_energy_absorbed"] = [1, True]
    with pytest.raises(ValueError):
        audit_run(spec.canonical(), document)


@pytest.mark.parametrize("make", [_chain, _mixed, _grow_with_energy, _off_axis])
def test_honest_runs_pass(make) -> None:
    spec = make()
    assert audit_run(spec.canonical(), run(spec).canonical()) == []


def _tampered(field_path, value):
    spec = _grow_with_energy()
    document = copy.deepcopy(run(spec).canonical())
    target = document
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = value
    return audit_run(spec.canonical(), document)


def test_a_wrong_absorption_claim_is_caught() -> None:
    assert any("claimed absorption" in p for p in _tampered(("events", 0, "kinetic_energy_absorbed"), [1, 1]))


def test_dropping_the_old_internal_energy_is_caught() -> None:
    """U' written as only the new absorption (4/3), losing the structure's earlier 5."""
    problems = _tampered(("events", 0, "post", "internal_energy"), [4, 3])
    assert any("U' != sum U" in p for p in problems)


def test_a_momentum_change_is_caught() -> None:
    assert any("momentum not conserved" in p for p in _tampered(("events", 0, "post", "momentum"), [[-1, 1], [0, 1]]))


def test_a_bond_that_moves_an_element_is_caught() -> None:
    spec = _grow_with_energy()
    document = copy.deepcopy(run(spec).canonical())
    document["events"][0]["post"]["positions"][0][1] = [[7, 1], [0, 1]]
    assert any("moved an element" in p for p in audit_run(spec.canonical(), document))


def test_a_final_state_that_lost_energy_is_caught() -> None:
    problems = _tampered(("final_state", "structures", 0, "internal_energy"), [0, 1])
    assert any("K + U changed" in p for p in problems)
