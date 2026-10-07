"""Build the sealed V2 training experience bundle (protocol 'training_bundle_v2').

    python -m experiments.experience_start_p_v2.build_training_bundle OUT_JSON
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from experiments.experience_start_p_v2.experience import build_bundle, canonical_bytes


def main():
    out = Path(sys.argv[1])
    b = build_bundle()
    data = canonical_bytes(b)
    out.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    out.with_suffix(".sha256").write_text(sha + "\n", encoding="utf-8")
    for m in b["sources"]:
        print("source", m["id"], "read", m["n_records_read"], m["checker_verdict"], "archive", m["archive_sha256_raw"][:16])
    print("records", b["n_records"], "dropped", b["dedup"]["n_dropped"],
          "verified", sum(r["verification_status"] == "VERIFIED" for r in b["records"]))
    print("exact keys", len(b["exact"]), "family keys", len(b["family"]))
    for k, e in sorted(b["exact"].items(), key=lambda kv: (kv[1]["T"], kv[1]["N"])):
        print(f"exact N{e['N']} T{e['T']} success {e['observed_success_p']} failure {e['observed_failure_p']} "
              f"lowest_observed_success_p {e['lowest_observed_success_p']} highest_observed_failure_p "
              f"{e['highest_observed_failure_p']}")
    for k, f in sorted(b["family"].items(), key=lambda kv: kv[1]["T"]):
        print(f"family T{f['T']} members {[(m['N'], m['lowest_observed_success_p']) for m in f['members']]} "
              f"FAMILY_MIN {f['FAMILY_MIN']} FAMILY_MAX {f['FAMILY_MAX']}")
    print("physics", b["physics_contract_hash"][:16], "numeric", b["numeric_contract_hash"][:16], "bundle sha256", sha)


if __name__ == "__main__":
    main()
