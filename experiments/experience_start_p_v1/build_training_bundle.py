"""Build the sealed training experience bundle from the verified SELECTOR_SERVICE_V1 evidence.

    python -m experiments.experience_start_p_v1.build_training_bundle OUT_JSON
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from experiments.experience_start_p_v1.experience import ROOT, build_bundle, canonical_bytes

SRC = ROOT / "docs/active/selector_service_v1/laptop_run"
SOURCE_ID = "SELECTOR_SERVICE_V1@0e6953b:docs/active/selector_service_v1/laptop_run"


def main():
    out = Path(sys.argv[1])
    b = build_bundle(SRC / "records.json.gz", SRC / "checker_verdict.json", SRC / "execution_seal.json", SOURCE_ID)
    data = canonical_bytes(b)
    out.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    out.with_suffix(".sha256").write_text(sha + "\n", encoding="utf-8")
    print("records", len(b["records"]), "verified", sum(r["verification_status"] == "VERIFIED" for r in b["records"]))
    for k, e in sorted(b["exact"].items(), key=lambda kv: (kv[1]["T"], kv[1]["N"])):
        print(f"exact N{e['N']} T{e['T']} lowest_observed_success_p {e['lowest_observed_success_p']} "
              f"highest_observed_failure_p {e['highest_observed_failure_p']} fp {k[:12]}")
    for k, f in sorted(b["family"].items(), key=lambda kv: kv[1]["T"]):
        print(f"family T{f['T']} members {[m['N'] for m in f['members']]} FAMILY_MIN {f['FAMILY_MIN']} FAMILY_MAX {f['FAMILY_MAX']}")
    print("physics", b["physics_contract_hash"][:16], "numeric", b["numeric_contract_hash"][:16], "bundle sha256", sha)


if __name__ == "__main__":
    main()
