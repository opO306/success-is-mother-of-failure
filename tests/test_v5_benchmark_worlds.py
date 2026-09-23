"""The v5 benchmark worlds do what they claim (A: guaranteed corner-free depth; B: ordinary worlds)."""
from __future__ import annotations

from fractions import Fraction

import pytest

from audit.independent_v5 import audit_run
from engine.deterministic.v5_benchmark_worlds import merge_chain_world, random_world
from engine.deterministic.v5_reference import run_v5
from engine.deterministic.v5_spec import RunRequest

FOREVER = RunRequest(10 ** 15, 10 ** 15)


@pytest.mark.parametrize("drift", [Fraction(0), Fraction(1, 7)])
def test_the_stress_world_reaches_its_depth_along_one_lineage(drift) -> None:
    spec = merge_chain_world(12, drift)
    result = run_v5(spec, FOREVER)
    assert result.outcome == "completed" and result.unresolved == ()
    assert len(result.events) == 12
    assert all(len(e.pre) == 2 and "g000" in e.post.members for e in result.events)   # one lineage, one target each
    assert [len(e.post.members) for e in result.events] == list(range(2, 14))
    assert audit_run(spec.canonical(), result.canonical()) == []


def test_the_stress_world_never_needs_undefined_physics() -> None:
    spec = merge_chain_world(12, Fraction(1, 7))
    assert {e.position[1] for e in spec.elements} == {Fraction(0)}            # one row: no corner can form
    assert {s.momentum for s in spec.structures[1:]} <= {(-Fraction(1, 7) * m, Fraction(0))
                                                         for m in (spec.material(k).mass for k in range(6))}


def test_census_worlds_are_ordinary_and_audited() -> None:
    spec = random_world(12, 0)
    result = run_v5(spec, RunRequest(50, 50))
    assert audit_run(spec.canonical(), result.canonical()) == []
