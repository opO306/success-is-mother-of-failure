"""Fail-closed reporting semantics, independent of numerical constructors."""
from decimal import Decimal


def overall_status(numerical_guards, spatial_guards):
    """Unknown is not PASS. Empty guard sets are incomplete, not vacuous PASS."""
    values = [*numerical_guards.values(), *spatial_guards.values()]
    if not numerical_guards or not spatial_guards or any(v not in ("PASS", "FAIL", "UNRESOLVED") for v in values):
        return "UNRESOLVED"
    if "FAIL" in values:
        return "REFUSED"
    return "ACCEPTED" if all(v == "PASS" for v in values) else "UNRESOLVED"


def compare_interval(left, right, left_bound=None, right_bound=None, threshold="1e-9"):
    """Bounds must already be independently verified; empirical spread is not a bound."""
    difference = Decimal(str(left))-Decimal(str(right))
    band = Decimal(str(threshold))
    if not difference.is_finite() or not band.is_finite() or band < 0:
        raise ValueError("finite signed energies and nonnegative threshold required")
    result = {"signed_difference": str(difference), "threshold": str(band),
              "measured_relation": "WITHIN_BAND" if abs(difference) <= band else "OUTSIDE_BAND"}
    if left_bound is None or right_bound is None:
        return dict(result, uncertainty_relation="UNRESOLVED", evidence="measured comparison; unverified uncertainty")
    a, b = Decimal(str(left_bound)), Decimal(str(right_bound))
    if not a.is_finite() or not b.is_finite() or a < 0 or b < 0:
        raise ValueError("nonnegative finite verified bounds required")
    radius = a+b
    relation = "WITHIN_BAND" if abs(difference)+radius <= band else (
        "OUTSIDE_BAND" if abs(difference)-radius > band else "UNRESOLVED")
    return dict(result, uncertainty_relation=relation, verified_difference_radius=str(radius),
                evidence="conditional on independently verified supplied bounds")


def classifications(arms, baseline_relations, inter_arm_relation, precision_sensitive):
    """B, C and precision findings coexist. One accepted arm never proves equivalence."""
    accepted = sum(arm == "ACCEPTED" for arm in arms.values())
    both = set(arms) == {"L", "I"} and accepted == 2
    equivalent = both and set(baseline_relations) == {"L", "I"} and all(
        r == "WITHIN_BAND" for r in baseline_relations.values()) and inter_arm_relation == "WITHIN_BAND"
    return {
        "accepted_arm_count": accepted,
        "SAME_BASIS_ENERGY_EQUIVALENCE_SUPPORTED": equivalent,
        "NUMERICAL_FRONTEND_ENERGY_SHIFT_CONFIRMED": any(r == "OUTSIDE_BAND" for r in baseline_relations.values()),
        "INDEPENDENT_AO_PATH_DISAGREEMENT": inter_arm_relation == "OUTSIDE_BAND",
        "PRECISION_SENSITIVITY_SUPPORTED": bool(precision_sensitive),
        "SAME_BASIS_RECONSTRUCTION_UNRESOLVED": not equivalent,
        "NOT_CERTIFIED": True,
    }


def require_comparison_context(left, right, cross_arm=False, common_mapping_verified=False):
    if cross_arm:
        if not common_mapping_verified:
            raise ValueError("unaligned cross-arm MO subtraction prohibited")
    elif left["AO_sha256"] != right["AO_sha256"] or left["C_sha256"] != right["C_sha256"]:
        raise ValueError("within-arm algorithm comparison requires identical AO and C")


def signed_budget(old, new, reference):
    old, new, reference = map(lambda x: Decimal(str(x)), (old, new, reference))
    if not all(x.is_finite() for x in (old, new, reference)):
        raise ValueError("finite energies required")
    return {"E_old_minus_E_new": str(old-new), "E_new_minus_E_reference": str(new-reference),
            "sum_equals_old_minus_reference": old-new+new-reference == old-reference,
            "numerical_error_bound": None, "reference_error_bound": None,
            "pure_finite_basis_error": "NOT_ESTABLISHED", "error_cancellation": "NOT_EXCLUDED"}
