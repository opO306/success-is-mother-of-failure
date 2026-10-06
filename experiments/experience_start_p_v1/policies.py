"""Start-p policies of EXPERIENCE_START_P_V1 (protocol 'policies'). A decision uses only pre-run features of the request
and the read-only sealed ExperienceStore; it picks the first p and nothing else."""

from __future__ import annotations

from experiments.experience_start_p_v1.experience import family_key, fingerprint

POLICIES = ("P2_BASE", "EXACT_MEMORY", "FAMILY_MIN", "FAMILY_MAX")
DEFAULT_START = 64


def decide(policy, N, T, evaluator, initial_digest, store, current_physics, current_numeric):
    if policy not in POLICIES:
        raise ValueError(policy)
    contracts_match = (current_physics, current_numeric) == (store.physics, store.numeric)
    fp = fingerprint(current_physics, current_numeric, evaluator, initial_digest, T)
    fk = family_key(T, evaluator, current_physics, current_numeric)
    exact = store.exact(fp) if contracts_match else None
    fam = store.family(fk) if contracts_match else None
    d = {"policy": policy, "N": N, "T": T, "evaluator": evaluator, "initial_state_digest": initial_digest,
         "request_fingerprint": fp, "family_key": fk, "bundle_sha256": store.sha256,
         "contracts_match": contracts_match, "exact_hit": exact is not None,
         "exact_lowest_observed_success_p": exact["lowest_observed_success_p"] if exact else None,
         "exact_highest_observed_failure_p": exact["highest_observed_failure_p"] if exact else None,
         "family_hit": fam is not None, "FAMILY_MIN": fam["FAMILY_MIN"] if fam else None,
         "FAMILY_MAX": fam["FAMILY_MAX"] if fam else None}
    if policy == "EXACT_MEMORY" and d["exact_lowest_observed_success_p"] is not None:
        start, src = d["exact_lowest_observed_success_p"], "EXACT_MEMORY"
    elif policy == "FAMILY_MIN" and fam:
        start, src = fam["FAMILY_MIN"], "FAMILY_MIN"
    elif policy == "FAMILY_MAX" and fam:
        start, src = fam["FAMILY_MAX"], "FAMILY_MAX"
    else:
        start, src = DEFAULT_START, "DEFAULT_64"
    d["start_p"], d["start_source"] = start, src
    return d
