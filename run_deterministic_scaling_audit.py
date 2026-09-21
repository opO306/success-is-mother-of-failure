"""Run deterministic locality, resolution, and optional CPU scaling audits."""
from __future__ import annotations

import argparse
import json

from engine.deterministic import benchmark_environment_sizes, run_scaling_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--sizes", default="64,128,256")
    parser.add_argument("--ticks", type=int, default=4)
    args = parser.parse_args()
    audit = run_scaling_audit()
    payload = {"audit": audit.canonical(), "audit_digest": audit.digest}
    if args.benchmark:
        sizes = tuple(int(value) for value in args.sizes.split(",") if value)
        payload["benchmark"] = benchmark_environment_sizes(sizes, args.ticks)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
