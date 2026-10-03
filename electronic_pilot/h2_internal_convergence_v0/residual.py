"""Independent generalized residual from original dyadic H/S and returned E/v.

No invsg, avms, native dot product, CI builder, or integral evaluator is reused.
Numerical measurements at 160 decimal digits; no post-hoc acceptance tolerance.
"""
import argparse
import json
from pathlib import Path
import time

from .snapshot import DPS, context, read_ev, read_hs


def measure(h, s, energy, vector, ctx):
    n = len(vector)
    if len(h) != n * (n + 1) // 2 or len(s) != len(h):
        raise ValueError("residual input dimension mismatch")
    zero = ctx.mpf(0)
    hv, sv, ha, sa, hn, sn = ([zero] * n for _ in range(6))
    k = 0
    for i in range(n):
        for j in range(i + 1):
            hij, sij = h[k], s[k]
            hv[i] += hij * vector[j]
            sv[i] += sij * vector[j]
            ha[i] += abs(hij) * abs(vector[j])
            sa[i] += abs(sij) * abs(vector[j])
            hn[i] += abs(hij)
            sn[i] += abs(sij)
            if i != j:
                hv[j] += hij * vector[i]
                sv[j] += sij * vector[i]
                ha[j] += abs(hij) * abs(vector[i])
                sa[j] += abs(sij) * abs(vector[i])
                hn[j] += abs(hij)
                sn[j] += abs(sij)
            k += 1
    r = [hv[i] - energy * sv[i] for i in range(n)]
    l2 = ctx.sqrt(ctx.fsum(x * x for x in r))
    linf = max(abs(x) for x in r)
    metric = ctx.fsum(vector[i] * sv[i] for i in range(n))
    numerator = ctx.fsum(vector[i] * hv[i] for i in range(n))
    if metric <= 0 or not ctx.isfinite(metric):
        raise ValueError("nonpositive/nonfinite returned metric norm")
    rayleigh = numerator / metric
    scale = (max(hn) + abs(energy) * max(sn)) * max(abs(x) for x in vector)
    actions = [ha[i] + abs(energy) * sa[i] for i in range(n)]
    componentwise = max((abs(r[i]) / actions[i] if actions[i] else zero) for i in range(n))
    quantities = dict(residual_l2=l2, residual_linf=linf, vTSv=metric,
                      normalization_abs_error=abs(metric - 1), E_RQ=rayleigh,
                      E_invsg=energy, E_RQ_minus_E_invsg=rayleigh - energy,
                      normwise_eta_inf=linf / scale if scale else zero,
                      componentwise_eta=componentwise, normwise_action_scale=scale,
                      max_absolute_action_scale=max(actions),
                      metric_cancellation_ratio=ctx.fsum(abs(vector[i]) * sa[i] for i in range(n)) / abs(metric))
    if any(not ctx.isfinite(x) for x in quantities.values()):
        raise ValueError("nonfinite independent residual quantity")
    return {key: ctx.nstr(value, DPS) for key, value in quantities.items()}


def root_diagnostic(h, s, energy, n):
    import numpy as np
    from scipy.linalg import eigh
    hh, ss = np.empty((n, n)), np.empty((n, n))
    k = 0
    for i in range(n):
        for j in range(i + 1):
            hh[i, j] = hh[j, i] = float(h[k])
            ss[i, j] = ss[j, i] = float(s[k])
            k += 1
    result = {"arithmetic": "BINARY64_DIAGNOSTIC_NOT_HIGH_PRECISION_TRUTH",
              "matrix_modifications": [], "root_selection": "H2SOLV_ROOT_SELECTION_UNRESOLVED"}
    try:
        sroots = eigh(ss, eigvals_only=True, check_finite=True)
        low, high = float(sroots[0]), float(sroots[-1])
        result.update(binary64_S_smallest_eigenvalue=low, binary64_S_largest_eigenvalue=high)
        if low <= 0:
            result["status"] = "UNAVAILABLE_METRIC_NOT_SPD_AFTER_BINARY64_CONVERSION"
            return result
        cond = high / low
        cond_scale = cond * n * np.finfo(float).eps
        result.update(binary64_metric_cond2=cond, condition_roundoff_scale=cond_scale)
        roots, vectors = eigh(hh, ss, type=1, subset_by_index=[0, 1], check_finite=True)
        residuals = [float(np.linalg.norm(hh @ vectors[:, i] - roots[i] * (ss @ vectors[:, i]))) for i in range(2)]
        error_scale = max(x / np.sqrt(low) for x in residuals)
        uncertainty = error_scale + 100 * cond_scale * max(1., max(abs(x) for x in roots))
        delta = float(energy) - float(roots[0])
        gap = float(roots[1] - roots[0])
        result.update(lowest_root=float(roots[0]), second_root=float(roots[1]),
                      root_gap=gap, E_invsg_minus_binary64_lowest=delta,
                      eigensolver_residual_l2=residuals,
                      diagnostic_uncertainty_scale=float(uncertainty), status="MEASURED")
        qualified = cond_scale <= 1e-8 and gap > 4 * uncertainty
        result["condition_qualified_for_root_comparison"] = bool(qualified)
        result["root_contradiction"] = bool(qualified and abs(delta) > uncertainty)
        if qualified and not result["root_contradiction"]:
            result["root_selection"] = "H2SOLV_ROOT_SELECTION_SUPPORTED_NUMERICAL_DIAGNOSTIC_ONLY"
    except Exception as exc:
        result.update(status="UNAVAILABLE_NUMERICAL_DIAGNOSTIC", error=type(exc).__name__ + ": " + str(exc))
    return result


def audit(folder):
    ctx = context()
    start = time.monotonic()
    h, s, matrix = read_hs(folder / "audit_HS.bin", ctx)
    energy, vector, ev = read_ev(folder / "audit_EV.bin", ctx)
    if matrix["n"] != ev["n"]:
        raise ValueError("matrix/vector dimension mismatch")
    measurements = measure(h, s, energy, vector, ctx)
    return dict(status="MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD", decimal_digits=DPS,
                independent_from_native_routines=True, formal_or_interval_certificate=False,
                matrix_snapshot=matrix, returned_state_snapshot=ev, measurements=measurements,
                root_diagnostic=root_diagnostic(h, s, energy, matrix["n"]),
                wall_seconds=time.monotonic() - start)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, required=True)
    args = parser.parse_args()
    output = args.folder / "independent_residual.json"
    try:
        result = audit(args.folder)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
        print(json.dumps({"case": args.folder.name, "status": result["status"],
                          "residual_l2": result["measurements"]["residual_l2"],
                          "wall_seconds": result["wall_seconds"]}), flush=True)
    except Exception as exc:
        output.write_text(json.dumps({"status": "INDEPENDENT_RESIDUAL_UNRESOLVED",
                                      "error": type(exc).__name__ + ": " + str(exc)}, indent=2) + "\n", encoding="utf8")
        raise


if __name__ == "__main__":
    main()
