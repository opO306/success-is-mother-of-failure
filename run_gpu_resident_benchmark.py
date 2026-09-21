"""Validate and benchmark resident CUDA field execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic.environment_spec import load_environment_world_spec
from engine.deterministic.gpu_environment import benchmark_cuda_resident, verify_cuda_resident_every_tick


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--sizes", default="64,128,256,512")
    parser.add_argument("--ticks", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = load_environment_world_spec(args.spec)
    parity = verify_cuda_resident_every_tick(spec)
    sizes = tuple(int(value) for value in args.sizes.split(",") if value)
    benchmark = benchmark_cuda_resident(sizes, args.ticks)
    payload = {"parity": parity.canonical(), "benchmark": [x.canonical() for x in benchmark],
               "timing_is_physics": False}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8"); temporary.replace(args.output)
    raise SystemExit(0 if parity.complete_match and all(x.complete_match for x in benchmark) else 1)


if __name__ == "__main__":
    main()
