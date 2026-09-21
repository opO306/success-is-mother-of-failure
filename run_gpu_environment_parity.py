"""Compare A2.3 CPU reference and CUDA int64 transport at every tick."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic.environment_spec import load_environment_world_spec
from engine.deterministic.gpu_environment import run_cpu_cuda_parity


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--ticks", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_cpu_cuda_parity(load_environment_world_spec(args.spec), args.ticks)
    rendered = json.dumps(report.canonical(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)
    raise SystemExit(0 if report.complete_match else 1)


if __name__ == "__main__":
    main()
