"""Independent audit of a causal v5 run (plan section 8).

Reads only JSON-shaped data: the world spec's canonical form and the run's
canonical form. Imports nothing from `engine` (enforced by
`tests/test_v5_audit.py`) and parses numbers itself.

It does not trust the executor's arithmetic. For every merge event it takes
the recorded pre-event structures (members, momentum, internal energy,
positions), recomputes each mass from the spec's materials, and checks:

    members(post)   == union of members(pre)
    positions(post) == union of positions(pre)          (a bond moves nothing)
    P'              == sum P_i                           (momentum)
    U'              == sum U_i + sum K_i - K'            (merge conservation law, E3)
    claimed absorption == sum K_i - K'                   (the claim is checked, not used)
    residual        == sum (R_cm x P)_i - (R'_cm x P')   (E7 angular-momentum residual, recounted)

and over the whole run: element counts per kind, total momentum and total
K + U are the same at the start (spec) and the end (final state).
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping


def _num(pair: Any) -> Fraction:
    numerator, denominator = pair
    if type(numerator) is not int or type(denominator) is not int:        # bool is an int subclass: refused
        raise ValueError("a number is two ints")
    if denominator <= 0:
        raise ValueError("a denominator is positive")
    return Fraction(numerator, denominator)


def _vec(pair: Any) -> tuple[Fraction, Fraction]:
    return _num(pair[0]), _num(pair[1])


class _World:
    def __init__(self, spec: Mapping[str, Any]) -> None:
        self.mass_of_kind = {m["kind"]: _num(m["mass"]) for m in spec["materials"]}
        self.kind_of = {e["label"]: e["kind"] for e in spec["elements"]}

    def mass(self, members) -> Fraction:
        return sum((self.mass_of_kind[self.kind_of[m]] for m in members), Fraction(0))

    def kinetic(self, members, momentum) -> Fraction:
        px, py = momentum
        return (px * px + py * py) / (2 * self.mass(members))

    def angular_momentum(self, snapshot) -> Fraction:
        """z component about the origin of a rigid, non-rotating body: R_cm x P,
        R_cm recomputed from the recorded member positions and the spec's masses."""
        total_mass = self.mass(snapshot["members"])
        cx = cy = Fraction(0)
        for label, position in snapshot["positions"]:
            x, y = _vec(position)
            m = self.mass_of_kind[self.kind_of[label]]
            cx, cy = cx + m * x, cy + m * y
        cx, cy = cx / total_mass, cy / total_mass
        px, py = _vec(snapshot["momentum"])
        return cx * py - cy * px


def _totals(world: _World, structures) -> tuple[tuple[Fraction, Fraction], Fraction]:
    px = py = energy = Fraction(0)
    for s in structures:
        p = _vec(s["momentum"])
        px, py = px + p[0], py + p[1]
        energy += world.kinetic(s["members"], p) + _num(s["internal_energy"])
    return (px, py), energy


def audit_run(spec: Mapping[str, Any], run: Mapping[str, Any]) -> list[str]:
    """Problems found; empty means the run passed."""
    world = _World(spec)
    problems: list[str] = []
    for index, event in enumerate(run["events"]):
        where = f"event {index} at t={event['time']}"
        pre, post = event["pre"], event["post"]
        members = [m for s in pre for m in s["members"]]
        if sorted(members) != sorted(post["members"]) or len(set(members)) != len(members):
            problems.append(f"{where}: post members are not the union of pre members")
        pre_positions = sorted((q[0], _vec(q[1])) for s in pre for q in s["positions"])
        post_positions = sorted((q[0], _vec(q[1])) for q in post["positions"])
        if pre_positions != post_positions:
            problems.append(f"{where}: a bond moved an element")
        momentum = (sum((_vec(s["momentum"])[0] for s in pre), Fraction(0)),
                    sum((_vec(s["momentum"])[1] for s in pre), Fraction(0)))
        if momentum != _vec(post["momentum"]):
            problems.append(f"{where}: momentum not conserved")
        kinetic_before = sum((world.kinetic(s["members"], _vec(s["momentum"])) for s in pre), Fraction(0))
        kinetic_after = world.kinetic(post["members"], _vec(post["momentum"]))
        internal_before = sum((_num(s["internal_energy"]) for s in pre), Fraction(0))
        expected_internal = internal_before + kinetic_before - kinetic_after
        if _num(post["internal_energy"]) != expected_internal:
            problems.append(f"{where}: U' != sum U + sum K - K'")
        if _num(event["kinetic_energy_absorbed"]) != kinetic_before - kinetic_after:
            problems.append(f"{where}: claimed absorption disagrees with the recount")
        if kinetic_before - kinetic_after < 0:
            problems.append(f"{where}: a bond created energy")
        residual = sum((world.angular_momentum(s) for s in pre), Fraction(0)) - world.angular_momentum(post)
        if _num(event["angular_momentum_residual"]) != residual:
            problems.append(f"{where}: recorded angular-momentum residual disagrees with the recount (E7)")
    start = [{"members": s["members"], "momentum": s["momentum"], "internal_energy": s["internal_energy"]}
             for s in spec["structures"]]
    end = run["final_state"]["structures"]
    counts_start = sorted(world.kind_of[e["label"]] for e in spec["elements"])
    counts_end = sorted(e["kind"] for e in run["final_state"]["elements"])
    if counts_start != counts_end:
        problems.append("material counts changed")
    (p0, e0), (p1, e1) = _totals(world, start), _totals(world, end)
    if p0 != p1:
        problems.append("total momentum changed over the run")
    if e0 != e1:
        problems.append("total K + U changed over the run")
    return problems
