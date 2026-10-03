"""Parse actual branch markers; a printed energy or exit 0 never establishes convergence."""
from pathlib import Path

from .snapshot import context, decode_word


def parse(path):
    ctx = context()
    observation = {"iterations": [], "leq1s": [], "maxit_exhausted": False,
                   "converged_by_eigenvalue_test": False, "structure_errors": []}
    values, current = {}, None
    for line in Path(path).read_text(encoding="ascii").splitlines():
        parts = line.split()
        if not parts:
            continue
        tag = parts[0]
        if tag == "VALUE":
            if len(parts) != 11:
                raise ValueError("invalid sidecar dyadic record")
            name, words = parts[1], list(map(int, parts[2:]))
            value, bits = decode_word(words, ctx)
            target = current if name in ("previous", "updated", "signed_delta", "abs_delta", "threshold") else values
            if target is None or name in target:
                raise ValueError("duplicate/orphan sidecar value")
            target[name] = value
            target[name + "_precision_bits"] = bits
        elif tag == "SNAPSHOT":
            if "dimension" in observation:
                raise ValueError("duplicate invsg snapshot")
            n, omega, nmax, nd, maxit = map(int, parts[1:])
            observation.update(dimension=n, OMEGA=omega, NMAX=nmax, NDIGITS=nd, ITMAX=maxit)
        elif tag == "BEGIN":
            n, maxit, job = map(int, parts[1:])
            if (n, maxit) != (observation["dimension"], observation["ITMAX"]):
                raise ValueError("invsg/header disagreement")
            observation["ijob"] = job
        elif tag == "LEQ":
            job, iteration, error = map(int, parts[1:])
            observation["leq1s"].append(dict(job=job, iteration=iteration, error=error))
        elif tag == "ITER":
            current = {"index": int(parts[1])}
            observation["iterations"].append(current)
        elif tag == "EXHAUSTED":
            observation["maxit_exhausted"] = True
            observation["exhausted_maxit"] = int(parts[1])
        elif tag in ("NORMALIZED_CONVERGED", "NORMALIZED_EXHAUSTED"):
            if "termination_reason" in observation:
                raise ValueError("duplicate termination marker")
            observation.update(actual_iteration_count=int(parts[1]), normalization_ier=int(parts[2]),
                               termination_reason="EIGENVALUE_TEST" if tag.endswith("CONVERGED") else "MAXIT_EXHAUSTED",
                               converged_by_eigenvalue_test=tag.endswith("CONVERGED"))
        elif tag == "RETURN":
            if "final_ierror" in observation:
                raise ValueError("duplicate invsg return")
            observation["final_ierror"] = int(parts[1])
        else:
            raise ValueError("unknown sidecar event: " + tag)
    errors = observation["structure_errors"]
    required_values = ("initial_EN", "final_EN", "EPSKOR", "errest")
    if any(name not in values for name in required_values) or "final_ierror" not in observation:
        raise ValueError("incomplete invsg sidecar")
    if observation["final_ierror"]:
        observation.setdefault("termination_reason", "LEQ1S_ERROR")
        observation.setdefault("actual_iteration_count", max([x["iteration"] for x in observation["leq1s"]], default=0))
    else:
        if "termination_reason" not in observation:
            errors.append("missing native normalization branch marker")
        if "factor_negative_count" not in values or "wa1" not in values:
            errors.append("missing inertia observation")
        elif values["factor_negative_count"] != values["wa1"]:
            errors.append("factor/return inertia disagreement")
    iters = observation["iterations"]
    if observation["final_ierror"] == 0:
        if observation.get("actual_iteration_count") != len(iters) or not 1 <= len(iters) <= observation["ITMAX"]:
            errors.append("actual iteration count disagreement")
        solves = [entry for entry in observation["leq1s"] if entry["job"] == 2]
        if [entry["iteration"] for entry in solves] != list(range(1, len(iters) + 1)):
            errors.append("linear solve count/order disagreement")
    last = None
    for index, row in enumerate(iters, 1):
        if row["index"] != index or any(name not in row for name in ("previous", "updated", "signed_delta", "abs_delta", "threshold")):
            raise ValueError("missing/out-of-order iteration")
        if abs(row["signed_delta"]) != row["abs_delta"]:
            errors.append("signed/absolute delta disagreement")
        if row["updated"] - row["previous"] != row["signed_delta"]:
            errors.append("primitive/delta disagreement")
        expected_threshold = values["errest"] * abs(row["updated"])
        roundoff = ctx.ldexp(abs(expected_threshold), 1 - row["threshold_precision_bits"])
        if abs(expected_threshold - row["threshold"]) > roundoff:
            errors.append("primitive/threshold disagreement")
        expected_previous = values["initial_EN"] if last is None else last["updated"]
        if row["previous"] != expected_previous:
            errors.append("broken eigenvalue chain")
        row["eigenvalue_test_true"] = row["abs_delta"] < row["threshold"]
        if index < len(iters) and row["eigenvalue_test_true"]:
            errors.append("native loop continued past reported true criterion")
        last = row
    if last is not None:
        if last["updated"] != values["final_EN"] and observation["final_ierror"] == 0:
            errors.append("final eigenvalue/iteration disagreement")
        if observation["converged_by_eigenvalue_test"] != last["eigenvalue_test_true"]:
            errors.append("native branch/criterion disagreement")
    if observation["maxit_exhausted"]:
        if observation.get("actual_iteration_count") != observation["ITMAX"] or len(iters) != observation["ITMAX"]:
            errors.append("exhaustion/count disagreement")
        if observation["converged_by_eigenvalue_test"]:
            errors.append("both convergence and exhaustion")
    observation["solver_factorization_error_free"] = observation["final_ierror"] == 0 and all(x["error"] == 0 for x in observation["leq1s"])
    if "wa1" in values:
        count = values["wa1"]
        if count != int(count) or not 0 <= count <= observation["dimension"]:
            errors.append("invalid inertia count")
        observation["number_of_eigenvalues_below_initial_EN_source_reported"] = int(count)
    observation["inverse_iteration_supported"] = bool(iters) and observation["converged_by_eigenvalue_test"] and not observation["maxit_exhausted"] and observation["solver_factorization_error_free"] and not errors
    observation.update(values)

    def serial(value):
        if isinstance(value, dict):
            return {k: serial(v) for k, v in value.items()}
        if isinstance(value, list):
            return [serial(v) for v in value]
        if isinstance(value, ctx.mpf):
            return ctx.nstr(value, 160)
        return value
    return serial(observation)
