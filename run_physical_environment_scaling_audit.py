"""Run and optionally save the A2.3 all-channel physical scaling audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import run_physical_environment_scaling_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    audit = run_physical_environment_scaling_audit()
    rendered = json.dumps({"audit": audit.canonical(), "audit_digest": audit.digest},
                          ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)


if __name__ == "__main__":
    main()
