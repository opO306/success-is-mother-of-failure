"""Run the independent sparse Cognitive Map query benchmark."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    CognitiveMapAdapter,
    build_cognitive_map,
    evaluate_cognitive_map_claims,
    initial_environment_state,
    load_environment_world_spec,
    make_cognitive_map_challenge,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = load_environment_world_spec(args.spec)
    queries = (
        {"query_id": "local-source", "kind": "local_state", "point": [4, 4]},
        {"query_id": "blocked-shortest", "kind": "shortest_path", "start": [20, 20], "goal": [21, 20]},
        {"query_id": "blocked-two", "kind": "reachable_within", "start": [20, 20], "goal": [21, 20], "max_steps": 2},
        {"query_id": "blocked-three", "kind": "reachable_within", "start": [20, 20], "goal": [21, 20], "max_steps": 3},
        {"query_id": "wrapped-neighbor", "kind": "shortest_path", "start": [0, 0], "goal": [31, 0]},
    )
    state = initial_environment_state(spec); cognitive_map = build_cognitive_map(spec, state)
    challenge = make_cognitive_map_challenge(spec, queries); adapter = CognitiveMapAdapter()
    claims = adapter.respond(challenge, spec)
    evaluation = evaluate_cognitive_map_claims(challenge, claims, spec)
    payload = {"challenge": challenge.canonical(), "manifest": adapter.manifest.canonical(),
               "map_summary": {"digest": cognitive_map.digest, "full_cells": cognitive_map.full_cell_count,
                               "stored_cells": cognitive_map.stored_cell_count},
               "claim_set": claims.canonical(), "evaluation": evaluation.canonical()}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8"); temporary.replace(args.output)
    raise SystemExit(0 if evaluation.complete_match else 1)


if __name__ == "__main__":
    main()
