"""Record cleavage and cross-origin joining without predefined gene blocks."""

from __future__ import annotations

import json
from pathlib import Path

from engine.sequence import (
    DevelopmentSeed,
    Encounter,
    InheritedBond,
    InheritedContribution,
    apply_encounter,
    assemble_inherited_world,
    connected_materials,
)


OUTPUT = Path("runs/physical_recombination_v1_probe.json")


def _encounter(first_id: int, first_port: int, second_id: int, second_port: int) -> Encounter:
    left, right = sorted(((first_id, first_port), (second_id, second_port)))
    return Encounter(left[0], left[1], right[0], right[1])


def _materials(seed: DevelopmentSeed) -> list[dict[str, object]]:
    return [
        {
            "physics": material.physical_canonical(),
            "observer_only_ancestry": [
                {
                    "local_index": mark.local_index,
                    "observer_tag": mark.observer_tag,
                    "source_local_index": mark.source_local_index,
                }
                for mark in material.ancestry
            ],
        }
        for material in connected_materials(seed)
    ]


def main() -> None:
    source_chain = InheritedContribution(
        "source_chain",
        (0, 3, 0),
        (InheritedBond(0, 0, 1, 0), InheritedBond(1, 1, 2, 0)),
    )
    other_source = InheritedContribution("other_source", (3,))
    seed = assemble_inherited_world((source_chain, other_source), thermal_energy=4)

    middle_id = seed.unit_id("source_chain", 1)
    end_id = seed.unit_id("source_chain", 2)
    other_id = seed.unit_id("other_source", 0)
    break_result = apply_encounter(seed.state, _encounter(middle_id, 1, end_id, 0))
    after_break = DevelopmentSeed(break_result.state, seed.origins)
    join_result = apply_encounter(after_break.state, _encounter(end_id, 0, other_id, 0))
    after_join = DevelopmentSeed(join_result.state, seed.origins)

    record = {
        "format": "physical-recombination-probe-v1",
        "initial": {"state": seed.state.canonical(), "materials": _materials(seed)},
        "after_break": {
            "event": break_result.event.canonical(),
            "state": after_break.state.canonical(),
            "materials": _materials(after_break),
        },
        "after_cross_origin_join": {
            "event": join_result.event.canonical(),
            "state": after_join.state.canonical(),
            "materials": _materials(after_join),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "outcomes": [
                    break_result.event.payload()["outcome"],
                    join_result.event.payload()["outcome"],
                ],
                "final_material_ancestry": [
                    sorted(material.observer_tags) for material in connected_materials(after_join)
                ],
                "output": str(OUTPUT.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
