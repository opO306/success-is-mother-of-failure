"""v3 gives ports names, so the state can say which face a bond uses.

Under v1/v2 a material could declare four ports while carrying a single
`orientation`. The four were then indistinguishable: when more than one would
accept the same arrival, nothing physical chose between them and the kernel
fell back on particle ids. These tests pin the naming that removes that, and
pin the refusals that stop a world declaring geometry it does not have.

See `docs/current/MINIMAL_LOCAL_GEOMETRY_V1.md`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.deterministic import load_causal_world_spec
from engine.deterministic.causal_spec import FORMAT_V2, FORMAT_V3, OPPOSITE_PORT


def _particle(pid: int, x: int, y: int, direction: str, energy: int) -> dict:
    return {"particle_id": pid, "kind": 0, "x": x, "y": y, "direction": direction,
            "orientation": direction, "kinetic_energy": energy}


def _rule(left_port: str, right_port: str, *, rule_id: str = "r1") -> dict:
    return {"rule_id": rule_id, "event": "local_reversible_bond",
            "locality": "adjacent_cells",
            "conserves": ["material", "energy", "momentum"],
            "left_kind": 0, "right_kind": 0,
            "left_port": left_port, "right_port": right_port,
            "minimum_collision_energy": 3, "break_heat": 2,
            "release_left": "W", "release_right": "E"}


def _world(*, ports=("N", "E", "S", "W"), rules=None, fmt: str = FORMAT_V3) -> dict:
    return {
        "format": fmt, "world_id": "v3-fixture",
        "kernel": {"width": 16, "height": 16, "boundary": "wrap",
                   "arithmetic": "integer", "deterministic": True,
                   "tick_order": ["break_existing_bonds", "stream_free_particles",
                                  "resolve_local_collisions"]},
        "materials": [{"kind": 0, "mass": 1, "ports": list(ports)}],
        "particles": [_particle(1, 9, 10, "E", 2), _particle(2, 11, 10, "W", 2)],
        "heat": [], "bond_rules": list(rules if rules is not None else [_rule("E", "W")]),
        "execution": {"ticks": 4}, "observer": {"hash_interval": 1}}


def _load(tmp_path: Path, world: dict):
    path = tmp_path / "world.json"
    path.write_text(json.dumps(world), encoding="utf-8")
    return load_causal_world_spec(path)


def test_v3_material_names_its_ports(tmp_path):
    spec = _load(tmp_path, _world())
    material = spec.materials[0]
    assert material.port_names == ("N", "E", "S", "W")
    assert material.ports == 4          # the count still follows from the names


def test_a_material_may_declare_fewer_faces(tmp_path):
    """Declaring only E and W is a physical statement: this material makes
    straight chains and cannot branch. The limit is geometry, not a ceiling."""
    spec = _load(tmp_path, _world(ports=("E", "W")))
    assert spec.materials[0].port_names == ("E", "W")
    assert spec.materials[0].ports == 2


def test_v3_bond_rules_join_adjacent_cells(tmp_path):
    spec = _load(tmp_path, _world())
    rule = spec.bond_rules[0]
    assert rule.locality == "adjacent_cells"
    assert (rule.left_port, rule.right_port) == ("E", "W")


def test_a_rule_may_not_use_a_port_its_material_lacks(tmp_path):
    with pytest.raises(ValueError, match="material 0 does not declare"):
        _load(tmp_path, _world(ports=("E", "W"), rules=[_rule("N", "S")]))


def test_a_rule_must_join_ports_that_face_each_other(tmp_path):
    """A bond is one contact seen from both ends, so E must meet W."""
    with pytest.raises(ValueError, match="do not face each other"):
        _load(tmp_path, _world(rules=[_rule("E", "N")]))


@pytest.mark.parametrize("ports,message", [
    (("E", "E"), "unique"),
    (("UP",), "cardinal directions"),
    ((), "non-empty list"),
])
def test_bad_port_declarations_are_refused(tmp_path, ports, message):
    with pytest.raises(ValueError, match=message):
        _load(tmp_path, _world(ports=ports))


def test_named_ports_require_v3(tmp_path):
    """A v2 world counts its ports; it has no way to mean a named one."""
    with pytest.raises(ValueError, match="named ports require the v3 format"):
        _load(tmp_path, _world(fmt=FORMAT_V2))


def test_v3_refuses_the_v2_orientation_keys(tmp_path):
    """v3 separates `orientation` (which way a particle faces) from `port`
    (which face it bonds with). A rule must say which it means."""
    world = _world()
    world["bond_rules"][0]["left_orientation"] = world["bond_rules"][0].pop("left_port")
    with pytest.raises(ValueError, match="left_port"):
        _load(tmp_path, world)


def test_opposite_port_is_symmetric():
    for port, facing in OPPOSITE_PORT.items():
        assert OPPOSITE_PORT[facing] == port


def test_v3_canonical_form_records_ports_by_name(tmp_path):
    spec = _load(tmp_path, _world())
    canonical = spec.canonical()
    assert canonical["materials"][0]["ports"] == ["N", "E", "S", "W"]
    assert canonical["bond_rules"][0]["left_port"] == "E"
    assert "left_orientation" not in canonical["bond_rules"][0]


def test_v1_and_v2_specs_are_unchanged(tmp_path):
    """The older formats keep counting their ports, digests included.

    v3 is a new format precisely so the frozen worlds keep reproducing; if
    this fails, the existing run digests have moved.
    """
    spec = load_causal_world_spec(Path("worlds") / "deterministic_polymer_chain_v2.json")
    assert spec.materials[0].port_names == ()
    assert spec.materials[0].ports == 4
    assert spec.canonical()["materials"][0]["ports"] == 4
    assert spec.bond_rules[0].locality == "same_cell"
    assert spec.digest == "472958da5fd5cae928b4de0ce63a2e4d7db6b208852e3005d1852fb24210d549"


def test_v3_falls_through_to_v1s_port_limits_and_chains_may_move(tmp_path):
    """`port_limits` and `chains_may_move` gate `PhysicalBond` (v1/v2) only --
    `PortBond` (v3) occupancy is checked per named port, never through these.

    Both are decided by format equality: `port_limits()` special-cases
    `FORMAT_V2`, and `initial_causal_state()` turns `chains_may_move` on only
    for `FORMAT_V2`. v3 matches neither check, so it falls through to v1's
    values -- not because v3 was designed to behave like v1, but because
    nothing has taught these two functions about v3 yet.

    `chains_may_move=False` is correct for the current stage regardless: v3
    structures cannot move yet (`chains()` does not read `port_bonds`, nothing
    builds a `PortBond` at runtime, and structure motion is stage 4+), so
    turning this on now would pre-implement a motion meaning that has not been
    designed. It gets redefined once `StructureState`/structure motion exists
    -- see `STRUCTURE_STATE_V1.md` 9.1.
    """
    from engine.deterministic.causal_kernel import initial_causal_state, port_limits

    spec = _load(tmp_path, _world())
    assert port_limits(spec) == {0: 1}

    state = initial_causal_state(spec)
    assert state.chains_may_move is False
    assert dict(state.port_limits) == {0: 1}
