"""causal v5 benchmark worlds (designer decision, 2026-09-24). Not physics -- world designs for measurement.

Two measurements, never mixed:

A. merge-depth stress (`merge_chain_world`) -- does exact rational dynamics
   blow up its denominators when ONE lineage grows by 10..500 merges?
   Built so nothing undefined can happen:
     * every element on y = 0  -> only E/W face contacts, never a corner;
     * one growing structure meets one target at a time -> never contested;
     * threshold 0 and an E-W rule for every kind pair -> every contact bonds;
     * depth is guaranteed, not hoped for: the growing structure's velocity is
       a mass-weighted average of values all greater than the targets' common
       velocity, so it always closes on the next target, and targets sharing one
       velocity never meet each other.
   Masses, spacings and velocities are deliberately varied fractions so that
   denominators have a chance to grow.

B. general census (`random_world`) -- how often does v5-v1's undefined physics
   (corners, contests, non-binding contacts) stop an ordinary world? Corners
   are NOT avoided here; that is the point.
"""
from __future__ import annotations

import random
from fractions import Fraction

from .v5_spec import FORMAT, WorldSpecV5

UNITS = {"mass": {"name": "dalton", "si": "166053906660/100000000000000000000000000000000000000"},
         "length": {"name": "picometer", "si": "1/1000000000000"},
         "time": {"name": "femtosecond", "si": "1/1000000000000000"}}

STRESS_MASSES = ("1", "3/2", "5/3", "7/4", "2/5", "11/6")


def _pair_rules(kinds: list[int], faces: tuple[tuple[str, str], ...]) -> list[dict]:
    rules = []
    seen = set()
    for i in kinds:
        for j in kinds:
            for fa, fb in faces:
                key = frozenset([(i, fa), (j, fb)])
                if key in seen:
                    continue
                seen.add(key)
                rules.append({"rule_id": f"{i}{fa}-{j}{fb}", "a": {"kind": i, "port": fa},
                              "b": {"kind": j, "port": fb}, "threshold": "0"})
    return rules


def merge_chain_world(depth: int, drift: Fraction = Fraction(0)) -> WorldSpecV5:
    """One structure at x = 0 moving east eats `depth` targets lying east of it.
    `drift` > 0 makes every target move west at that common speed."""
    kinds = list(range(len(STRESS_MASSES)))
    materials = [{"kind": k, "mass": m, "contact_half_width": "1/2", "ports": ["E", "W"]}
                 for k, m in enumerate(STRESS_MASSES)]
    elements = [{"label": "g000", "kind": 0, "position": ["0", "0"]}]
    structures = [{"members": ["g000"], "momentum": ["7/3", "0"]}]
    x = Fraction(0)
    for k in range(1, depth + 1):
        x += 1 + Fraction(k % 7 + 1, k % 5 + 2)                  # always > 1: never touching at the start
        kind = k % len(STRESS_MASSES)
        mass = Fraction(STRESS_MASSES[kind])
        label = f"t{k:04d}"
        elements.append({"label": label, "kind": kind, "position": [str(x), "0"]})
        structures.append({"members": [label], "momentum": [str(-drift * mass), "0"]})
    return WorldSpecV5.from_mapping({"format": FORMAT, "world_id": f"merge-chain-{depth}-drift-{drift}",
                                     "units": UNITS, "materials": materials,
                                     "bond_rules": _pair_rules(kinds, (("E", "W"),)),
                                     "elements": elements, "structures": structures})


def random_world(n: int, seed: int, box: int = 40, masses: tuple[str, ...] = ("1",)) -> WorldSpecV5:
    """Integer grid starts, small fractional velocities, all four faces bondable.
    Uses `random` only to design the initial picture -- the world itself stays deterministic."""
    rng = random.Random(seed)
    cells = rng.sample([(x, y) for x in range(0, box, 2) for y in range(0, box, 2)], n)
    kinds = list(range(len(masses)))
    materials = [{"kind": k, "mass": m, "contact_half_width": "1/2", "ports": ["E", "N", "S", "W"]}
                 for k, m in enumerate(masses)]
    elements, structures = [], []
    for index, (x, y) in enumerate(cells):
        kind = index % len(masses)
        label = f"p{index:03d}"
        mass = Fraction(masses[kind])
        vx = Fraction(rng.randint(-3, 3), rng.randint(1, 4))
        vy = Fraction(rng.randint(-3, 3), rng.randint(1, 4))
        elements.append({"label": label, "kind": kind, "position": [str(x), str(y)]})
        structures.append({"members": [label], "momentum": [str(vx * mass), str(vy * mass)]})
    return WorldSpecV5.from_mapping({"format": FORMAT, "world_id": f"census-{n}-{seed}-{len(masses)}",
                                     "units": UNITS, "materials": materials,
                                     "bond_rules": _pair_rules(kinds, (("E", "W"), ("N", "S"))),
                                     "elements": elements, "structures": structures})
