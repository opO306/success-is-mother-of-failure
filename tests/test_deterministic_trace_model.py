import json
from pathlib import Path

import pytest

from engine.deterministic import (
    BondTraceSubject,
    CausalWorldSpec,
    HeatCellTraceSubject,
    KernelPhase,
    ParticleTraceSubject,
    TraceSpec,
    bind_trace_spec,
    load_causal_world_spec,
    run_traced,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "worlds" / "deterministic_bond_cycle_v1.json"


def test_particle_trace_subject_rejects_unsupported_field() -> None:
    with pytest.raises(ValueError, match="unsupported particle trace fields"):
        ParticleTraceSubject("a", 9, 10, "E", ("mass",))


def test_trace_spec_rejects_duplicate_roles() -> None:
    with pytest.raises(ValueError, match="unique"):
        TraceSpec("T-1", (
            HeatCellTraceSubject("dup", 10, 10, ("energy",)),
            ParticleTraceSubject("dup", 9, 10, "E", ("x",)),
        ), 0, 1)


def test_bind_trace_spec_resolves_particle_and_heat_roles_once() -> None:
    spec = load_causal_world_spec(EXAMPLE)
    trace_spec = TraceSpec("T-1", (
        ParticleTraceSubject("particle_a", 9, 10, "E", ("kinetic_energy",)),
        HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),
    ), 0, 1)
    bindings = bind_trace_spec(trace_spec, spec)

    assert bindings["particle_a"].resolved_identity == "1"
    assert bindings["heated_cell"].resolved_identity == "10,10"


def test_run_traced_reports_no_bond_as_a_fact_not_a_gap() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec = CausalWorldSpec.from_mapping(raw)
    trace_spec = TraceSpec("T-1", (
        ParticleTraceSubject("particle_a", 9, 10, "E", ("x",)),
        ParticleTraceSubject("particle_b", 11, 10, "W", ("x",)),
        BondTraceSubject("target_bond", "particle_a", "particle_b", ("exists", "stored_energy")),
    ), 0, 0)
    snapshots = run_traced(spec, trace_spec)

    initial = next(s for s in snapshots if s.tick == 0 and s.phase == KernelPhase.PRE_TICK)
    assert initial.values["target_bond"] == {"exists": False, "stored_energy": None}


def test_run_traced_respects_start_tick() -> None:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec = CausalWorldSpec.from_mapping(raw)
    trace_spec = TraceSpec("T-1", (HeatCellTraceSubject("heated_cell", 10, 10, ("energy",)),), 1, 2)
    snapshots = run_traced(spec, trace_spec)

    assert all(s.tick >= 1 for s in snapshots)
    assert any(s.tick == 1 for s in snapshots)
    assert any(s.tick == 2 for s in snapshots)
