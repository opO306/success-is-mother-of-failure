"""Run the exact oracle through the model-neutral B-Language boundary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    CausalWorldSpec,
    EnvironmentWorldSpec,
    ExactOracleAdapter,
    evaluate_state_digest_claims,
    load_causal_world_spec,
    load_environment_world_spec,
    make_prediction_challenge,
    run_causal_world,
    run_environment_world,
)


def _load(path: Path) -> CausalWorldSpec | EnvironmentWorldSpec:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if str(raw.get("format", "")).startswith("deterministic-environment-world-spec-"):
        return load_environment_world_spec(path)
    return load_causal_world_spec(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--ticks", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = _load(args.spec)
    challenge = make_prediction_challenge(spec, args.ticks)
    adapter = ExactOracleAdapter()
    claims = adapter.respond(challenge, spec)
    run = run_environment_world(spec) if isinstance(spec, EnvironmentWorldSpec) else run_causal_world(spec)
    evaluation = evaluate_state_digest_claims(challenge, claims, run)
    payload = {"challenge": challenge.canonical(), "manifest": adapter.manifest.canonical(),
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
