"""v3 state persistence: does a structure still exist one tick later?

Stage 3's gate, before any structure motion is designed. The question is not
"did the structure move" but "did the structure survive at all" -- a tick that
silently drops `port_bonds`, `grid_size` or `named_ports` leaves a world whose
v3 bonds evaporate, and any later motion test would then be measuring three
free particles rather than a structure.

This was a real defect, measured before it was fixed:

    BEFORE  port_bonds=2  grid=(16,16)  named=1
    AFTER   port_bonds=0  grid=None     named=0

The cause was that every phase rebuilt `CausalWorldState` positionally with
six arguments, so every field added after `chains_may_move` was dropped. The
fix was to rebuild with `dataclasses.replace`, which cannot omit a field.
These tests hold that shut: they fail if a future field is dropped the same
way, rather than waiting for a structure to vanish in a later stage.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields

import pytest

from engine.deterministic import causal_kernel as ck
from engine.deterministic.causal_kernel import (
    CausalWorldState, PortBond, step_causal_world)
from engine.deterministic.causal_spec import CausalMaterialSpec, CausalParticleSpec

WIDTH, HEIGHT = 16, 16
NAMED_PORTS = {0: ("N", "E", "S", "W")}


def _particle(pid: int, x: int, y: int, direction: str = "N", energy: int = 0) -> CausalParticleSpec:
    return CausalParticleSpec(pid, 0, x, y, direction, direction, energy)


def _chain_state(*, energy: int = 0, holder: int = 1) -> CausalWorldState:
    """A—B—C bonded through named ports, laid out along x."""
    particles = [_particle(1, 5, 5), _particle(2, 6, 5), _particle(3, 7, 5)]
    if energy:
        particles[holder - 1] = _particle(holder, 4 + holder, 5, "E", energy)
    bonds = (PortBond(1, "E", 2, "W", "r", 0), PortBond(2, "E", 3, "W", "r", 0))
    return CausalWorldState(0, tuple(particles), (), (), {}, True,
                            (WIDTH, HEIGHT), NAMED_PORTS, bonds)


class _Spec:
    """The minimum `_break_existing`/`_stream_free`/`momentum` actually read."""
    class kernel:
        width, height = WIDTH, HEIGHT
    bond_rules = ()
    materials = (CausalMaterialSpec(0, 1, 4, ("N", "E", "S", "W")),)


# --- the gate: v3 state survives each phase ---------------------------------

@pytest.mark.parametrize("phase", ["_break_existing", "_stream_free", "_resolve_collisions"])
def test_each_tick_phase_preserves_v3_state(phase):
    state = _chain_state()
    result = getattr(ck, phase)(_Spec(), state)
    assert result.port_bonds == state.port_bonds, f"{phase} dropped port_bonds"
    assert result.grid_size == state.grid_size, f"{phase} dropped grid_size"
    assert dict(result.named_ports) == dict(state.named_ports), f"{phase} dropped named_ports"


def test_a_structure_at_rest_still_exists_after_a_full_tick():
    """The gate's headline: existence, not motion."""
    state = _chain_state()
    result = step_causal_world(_Spec(), state)
    assert len(result.port_bonds) == 2
    assert result.grid_size == (WIDTH, HEIGHT)
    assert dict(result.named_ports) == NAMED_PORTS
    assert result.tick == 1


def test_a_structure_survives_many_ticks():
    """One tick could pass by luck; a structure must not decay over time."""
    state = _chain_state()
    for _ in range(10):
        state = step_causal_world(_Spec(), state)
    assert len(state.port_bonds) == 2
    assert state.tick == 10


# --- the structural guard: no field may be dropped silently -----------------

def test_no_tick_phase_rebuilds_state_positionally():
    """Why this exists: a positional rebuild silently drops every field added
    after the last argument passed. `replace` cannot, so the phases must use
    it. This fails on the *mechanism*, not on one symptom, so a field added
    tomorrow is covered without a new test."""
    import inspect
    for name in ("_break_existing", "_stream_free", "_resolve_collisions", "step_causal_world"):
        source = inspect.getsource(getattr(ck, name))
        assert "CausalWorldState(" not in source, (
            f"{name} rebuilds CausalWorldState directly; use replace() so that "
            f"fields cannot be dropped")


def test_every_state_field_is_carried_through_a_tick():
    """Enumerates the dataclass rather than naming fields, so a new field is
    covered the moment it exists."""
    state = _chain_state()
    result = step_causal_world(_Spec(), state)
    for item in fields(CausalWorldState):
        if item.name in ("tick", "particles", "heat", "bonds"):
            continue        # these are what a tick is *supposed* to change
        before, after = getattr(state, item.name), getattr(result, item.name)
        if isinstance(before, Mapping):
            before, after = dict(before), dict(after)
        assert before == after, f"a tick dropped or changed {item.name}"


# --- v1/v2 are untouched ----------------------------------------------------

def test_a_v1_state_still_has_no_v3_fields_after_a_tick():
    """The fix must not give v1/v2 worlds v3 state they never declared --
    that would change their digest."""
    state = CausalWorldState(0, (_particle(1, 5, 5, "E", 2),), (), ())
    result = step_causal_world(_Spec(), state)
    assert result.port_bonds == ()
    assert result.grid_size is None
    assert dict(result.named_ports) == {}


def test_a_v1_digest_is_unchanged_by_the_absence_of_port_bonds():
    """`canonical()` omits `port_bonds` when empty, so a v1 state hashes as it
    did before the field existed."""
    state = CausalWorldState(0, (_particle(1, 5, 5, "E", 2),), (), ())
    assert "port_bonds" not in state.canonical()
