"""Forecast an A2/A2.1 environment with B, then compare to the actual run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import (
    evaluate_environment_forecast,
    forecast_environment_world,
    load_environment_world_spec,
    run_environment_world,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = load_environment_world_spec(args.spec)
    forecast = forecast_environment_world(spec, args.ticks)
    run = run_environment_world(spec)
    evaluation = evaluate_environment_forecast(forecast, run)
    payload = {
        "evaluation": evaluation.canonical(),
        "forecast": forecast.canonical(),
        "forecast_digest": forecast.digest,
        "run_digest": run.digest,
        "world_id": spec.causal_world.world_id,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)
    raise SystemExit(0 if evaluation.complete_match else 1)


if __name__ == "__main__":
    main()
