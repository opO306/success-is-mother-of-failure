"""Run one B0.1 causal specification on the A1 deterministic CPU kernel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import load_causal_world_spec, run_causal_world


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = load_causal_world_spec(args.spec)
    run = run_causal_world(spec)
    payload = {**run.canonical(), "run_digest": run.digest, "world_id": spec.world_id}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)


if __name__ == "__main__":
    main()
