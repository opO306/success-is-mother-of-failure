"""Run the exact B0.2 physical scale contract and heat refinement audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.deterministic import reference_scale_family, run_physical_scale_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    contract = reference_scale_family()
    audit = run_physical_scale_audit()
    rendered = json.dumps({
        "contract": contract.canonical(),
        "contract_digest": contract.digest,
        "audit": audit.canonical(),
        "audit_digest": audit.digest,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(args.output)


if __name__ == "__main__":
    main()
