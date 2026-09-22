"""v3 PortBond: is a given bond spatially and physically legal, from state alone?

Stage 2 of `MINIMAL_LOCAL_GEOMETRY_V1.md`. The question this stage answers is
narrow on purpose: given a set of `port_bonds`, does each one hold up against
the particles' actual positions and declared ports? It does not yet move
structures (stage 3+) -- only judges legality of a snapshot.

The ten checks below were specified by the project owner as this stage's
success criteria; each has a test. Adjacency is judged with `neighbour()`,
the exact formula `_stream_free` uses to move a particle, so a wrapped
world cannot have bonds reach across a seam that movement does not.
"""
from __future__ import annotations

import pytest

from pathlib import Path

from engine.deterministic.causal_kernel import CausalWorldState, PortBond, neighbour
from engine.deterministic.causal_spec import CausalParticleSpec, OPPOSITE_PORT

WIDTH, HEIGHT = 16, 16
NAMED_PORTS = {0: ("N", "E", "S", "W")}


def _particle(pid: int, x: int, y: int, direction: str = "N", energy: int = 0) -> CausalParticleSpec:
    return CausalParticleSpec(pid, 0, x, y, direction, direction, energy)


def _state(particles, port_bonds, *, named_ports=NAMED_PORTS, grid=(WIDTH, HEIGHT)) -> CausalWorldState:
    return CausalWorldState(0, tuple(particles), (), (), (), False, grid, named_ports, tuple(port_bonds))


# --- 1/2: facing ports at real adjacent coordinates ------------------------

def test_east_west_bond_requires_the_real_east_neighbour():
    a = _particle(1, 5, 5)
    b = _particle(2, 6, 5)          # a's real E neighbour
    _state([a, b], [PortBond(1, "E", 2, "W", "r", 0)])   # must not raise


def test_north_south_bond_requires_the_real_north_neighbour():
    a = _particle(1, 5, 5)
    b = _particle(2, 5, 4)          # a's real N neighbour (N decreases y)
    _state([a, b], [PortBond(1, "N", 2, "S", "r", 0)])   # must not raise


# --- 3: distant particles cannot bond ---------------------------------------

def test_distant_particles_cannot_bond():
    a = _particle(1, 5, 5)
    b = _particle(2, 9, 9)
    with pytest.raises(ValueError, match="not.*neighbour"):
        _state([a, b], [PortBond(1, "E", 2, "W", "r", 0)])


# --- 4: diagonal adjacency is not adjacency ---------------------------------

def test_diagonal_neighbours_cannot_bond():
    a = _particle(1, 5, 5)
    b = _particle(2, 6, 4)           # diagonal, not a cardinal neighbour
    with pytest.raises(ValueError, match="not.*neighbour"):
        _state([a, b], [PortBond(1, "E", 2, "W", "r", 0)])


# --- 5: non-facing ports are refused -----------------------------------------

def test_non_facing_ports_are_refused_even_when_adjacent():
    """Two ports that do not face each other are refused before adjacency is
    even checked -- 'E' and 'N' cannot describe one contact seen from both
    ends, regardless of where the particles happen to sit."""
    a = _particle(1, 5, 5)
    b = _particle(2, 6, 5)            # really is a's E neighbour
    with pytest.raises(ValueError, match="do not face each other"):
        _state([a, b], [PortBond(1, "E", 2, "N", "r", 0)])


def test_opposite_port_table_is_exactly_the_four_facings():
    assert OPPOSITE_PORT == {"N": "S", "S": "N", "E": "W", "W": "E"}


# --- 6: undeclared ports are refused -----------------------------------------

def test_a_bond_cannot_use_a_port_the_material_never_declared():
    a = _particle(1, 5, 5)
    b = _particle(2, 6, 5)
    with pytest.raises(ValueError, match="no 'E' port"):
        _state([a, b], [PortBond(1, "E", 2, "W", "r", 0)],
               named_ports={0: ("N", "S")})   # material only has N/S


# --- 7: a port cannot be claimed by two bonds at once -----------------------

def test_the_same_port_cannot_be_claimed_by_two_bonds():
    """Named ports without occupancy checking would be ports in name only.

    b's W port faces (5,5). Two different particles, a and d, both actually
    sitting at (5,5) each pass adjacency to b individually -- geometry alone
    allows both. Only an occupancy check catches that b's single W port
    cannot be given to both at once.
    """
    a = _particle(1, 5, 5)
    b = _particle(2, 6, 5)     # a's (and d's) real E neighbour
    d = _particle(4, 5, 5)     # occupies the same cell as a
    with pytest.raises(ValueError, match="claimed by 2 bonds"):
        _state([a, b, d], [
            PortBond(1, "E", 2, "W", "r1", 0),
            PortBond(4, "E", 2, "W", "r2", 0),   # b's W port again
        ])


def test_two_different_ports_on_the_same_particle_may_both_bond():
    """A -- B -- C through A's separate N and E ports is not a conflict."""
    a = _particle(1, 5, 5)
    b = _particle(2, 6, 5)     # a's E neighbour
    c = _particle(3, 5, 4)     # a's N neighbour
    _state([a, b, c], [
        PortBond(1, "E", 2, "W", "r", 0),
        PortBond(1, "N", 3, "S", "r", 0),
    ])   # must not raise


# --- 8: self-bond is refused --------------------------------------------------

def test_a_particle_cannot_bond_to_itself():
    a = _particle(1, 5, 5)
    with pytest.raises(ValueError, match="cannot join a particle to itself"):
        _state([a], [PortBond(1, "E", 1, "W", "r", 0)])


# --- 9: dangling references are refused --------------------------------------

def test_a_bond_to_a_missing_particle_is_refused():
    a = _particle(1, 5, 5)
    with pytest.raises(ValueError, match="missing particle"):
        _state([a], [PortBond(1, "E", 99, "W", "r", 0)])


# --- 10: v1/v2 states are completely unaffected ------------------------------

def test_v1_v2_states_ignore_port_bonds_entirely():
    """A state with no port_bonds behaves exactly as before this stage."""
    from engine.deterministic import load_causal_world_spec, initial_causal_state
    spec = load_causal_world_spec(Path("worlds") / "deterministic_polymer_chain_v2.json")
    state = initial_causal_state(spec)
    assert state.port_bonds == ()
    assert "port_bonds" not in state.canonical()


def test_frozen_v2_run_digest_is_unchanged():
    """The success criterion stated for this stage: v1/v2 digests survive."""
    from engine.deterministic import load_causal_world_spec, run_causal_world
    spec = load_causal_world_spec(Path("worlds") / "deterministic_polymer_chain_v2.json")
    run = run_causal_world(spec)
    assert run.digest == "0c45ac9942550f8db45d0ec162e18b4884c0be9ea471de5588998020d2303cf3"


# --- wrap adjacency: bonds must agree with how particles actually move -----

def test_neighbour_matches_the_streaming_formula_across_a_wrapped_seam():
    """A width-16 world wraps at the edge for movement; a bond must too."""
    assert neighbour(15, 5, "E", 16, 16) == (0, 5)
    assert neighbour(0, 5, "W", 16, 16) == (15, 5)


def test_a_bond_may_cross_the_wrapped_seam():
    a = _particle(1, 15, 5)
    b = _particle(2, 0, 5)     # a's wrapped E neighbour
    _state([a, b], [PortBond(1, "E", 2, "W", "r", 0)])   # must not raise


# --- left/right ordering carries no physics (relabelling invariance) -------

def test_bond_endpoint_order_is_not_physical():
    """Building the same contact with endpoints swapped must canonicalize
    identically -- `left`/`right` are record labels, not a processing order."""
    a_first = PortBond(1, "E", 2, "W", "r", 3)
    b_first = PortBond(2, "W", 1, "E", "r", 3)
    assert a_first.canonical() == b_first.canonical()
    assert a_first == b_first


def test_bond_canonical_form_puts_the_lower_id_first_regardless_of_construction_order():
    for left, right in [(1, 2), (2, 1), (9, 4), (4, 9)]:
        bond = PortBond(left, "E" if left < right else "W",
                        right, "W" if left < right else "E", "r", 0)
        assert bond.left_id == min(left, right)
        assert bond.right_id == max(left, right)


# --- energy accounting includes port_bonds ----------------------------------

def test_stored_energy_in_port_bonds_counts_toward_total_energy():
    a = _particle(1, 5, 5)
    b = _particle(2, 6, 5)
    state = _state([a, b], [PortBond(1, "E", 2, "W", "r", 7)])
    assert state.total_energy() == 7
