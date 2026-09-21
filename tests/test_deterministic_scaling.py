import inspect

from engine.deterministic import (
    benchmark_environment_sizes,
    make_locality_probe_spec,
    run_environment_world,
    run_scaling_audit,
)
import engine.deterministic.scaling as scaling_module


def test_same_local_patch_is_unchanged_by_empty_world_size() -> None:
    audit = run_scaling_audit()

    assert audit.locality_sizes == (32, 64, 128)
    assert audit.locality_equivalent is True
    assert len(set(audit.locality_signatures)) == 1


def test_resolution_audit_keeps_alternative_tick_scalings_separate() -> None:
    audit = run_scaling_audit()

    assert tuple(x.mapping for x in audit.tick_scaling_audits) == (
        "ticks_proportional_to_grid_width",
        "ticks_proportional_to_grid_width_squared",
    )
    assert all(tuple(item.grid_size for item in x.observations) == (16, 32, 64)
               for x in audit.tick_scaling_audits)
    assert all(len(x.successive_differences) == 2 for x in audit.tick_scaling_audits)


def test_resolution_audit_does_not_claim_unjustified_convergence() -> None:
    audit = run_scaling_audit()

    assert audit.convergence_status == "not-established"
    assert "no declared physical-unit mapping" in audit.convergence_reason


def test_scaling_audit_is_deterministic() -> None:
    first = run_scaling_audit(); second = run_scaling_audit()

    assert first == second
    assert first.digest == second.digest


def test_large_cpu_grid_preserves_resources_and_energy() -> None:
    spec = make_locality_probe_spec(256, 3)
    initial = run_environment_world(make_locality_probe_spec(256, 0)).final_state
    run = run_environment_world(spec)

    assert run.final_state.conserved_resources(spec) == initial.conserved_resources(spec)
    assert run.final_state.total_energy(spec) == initial.total_energy(spec)


def test_benchmark_keeps_timing_out_of_deterministic_state() -> None:
    first = benchmark_environment_sizes((64,), 2)[0]
    second = benchmark_environment_sizes((64,), 2)[0]

    assert first["elapsed_seconds"] > 0
    assert first["cell_ticks_per_second"] > 0
    assert first["final_state_digest"] == second["final_state_digest"]
    assert first["conserved_resources"] == second["conserved_resources"]


def test_scaling_audit_has_no_random_interface() -> None:
    source = inspect.getsource(scaling_module)

    assert "import random" not in source
    assert "SeededEventSource" not in source
    assert "choice_index" not in source
