"""Independent S-metric/product checks and full matrix exponential replay.

Never imports the executor, eigen-preparation, or its density function.
Shares saved matrices; author numerical checker, not external physics audit.
"""
import numpy as np
from scipy.linalg import eigh, expm, solve


def maxabs(a):
    return float(np.max(np.abs(a)))


def check(data, summary, spec):
    s, h, mu, e, u = (data[k] for k in ["s", "h", "dipoles", "energies", "eigenvectors"])
    initial, waves, kernels = (data[k] for k in ["initials", "waves", "density_kernels"])
    m, times = spec["basis_size"], spec["times_atomic"]
    errors, metrics = [], {}

    def require(ok, name):
        if not ok:
            errors.append(name)

    require(summary.get("input") == spec["case"] and spec["case"]["electrons"] == 1 and spec["case"]["sector"] == "doublet", "electron_sector_or_input_mismatch")
    require(s.shape == h.shape == u.shape == (m, m) and mu.shape == (3, m, m) and e.shape == (m,), "full_basis_dimension")
    require(initial.shape == (5, m) and waves.shape == (5, len(times), m) and kernels.shape == (5, len(times), m, m), "state_trace_dimension")
    if errors:
        return dict(status="FAIL", errors=errors, metrics=metrics)
    require(all(np.all(np.isfinite(x)) for x in data.values()), "nonfinite_data")
    if errors:
        return dict(status="FAIL", errors=errors, metrics=metrics)
    require(maxabs(s-s.T) <= spec["hermiticity_tolerance"] and maxabs(h-h.T) <= spec["hermiticity_tolerance"], "raw_H_S_hermiticity")
    require(maxabs(mu-mu.transpose(0, 2, 1)) <= spec["hermiticity_tolerance"], "dipole_hermiticity")
    w, q = eigh(s)
    require(w[0] > spec["overlap_floor"], "overlap_floor")
    if errors:
        return dict(status="FAIL", errors=errors, metrics=metrics)
    root = (q*np.sqrt(w))@q.T
    invroot = (q/np.sqrt(w))@q.T
    Horth = invroot@h@invroot
    actual_e = eigh(h, s, eigvals_only=True, type=1, driver="gvd")
    metrics["full_spectrum_error"] = maxabs(actual_e-e)
    metrics["eigenvector_S_orthogonality"] = maxabs(u.T@s@u-np.eye(m))
    residuals = h@u-(s@u)*e
    metric_residuals = [float(np.sqrt(max(0., np.dot(residuals[:, k], solve(s, residuals[:, k]))))) for k in range(m)]
    metrics["all_root_residual_max_S_metric"] = max(metric_residuals)
    metrics["selected_root_residuals_S_metric"] = metric_residuals[:2]
    require(metrics["full_spectrum_error"] <= spec["energy_tolerance"], "wrong_eigenvalues")
    require(metrics["eigenvector_S_orthogonality"] <= spec["norm_tolerance"], "eigen_orthogonality")
    require(max(metric_residuals) <= spec["residual_tolerance"], "eigen_residual_S_metric")
    require(e[1]-e[0] > spec["energy_distinction_floor"], "distinct_lowest_roots")
    require(maxabs(u.imag) == 0, "real_eigenvectors_required")

    # Independent raw superposition construction check, no canonicalization.
    wanted = np.column_stack((u[:, 0], u[:, 1]))
    require(maxabs(initial[0]-wanted@np.array([1., 1j])/np.sqrt(2.)) <= spec["state_tolerance"], "plus_construction")
    require(maxabs(initial[1]-wanted@np.array([1., -1j])/np.sqrt(2.)) <= spec["state_tolerance"], "minus_construction")
    metrics["initial_overlap_abs"] = float(abs(np.vdot(initial[0], s@initial[1])))
    require(metrics["initial_overlap_abs"] <= spec["norm_tolerance"], "plus_minus_distinct_orthogonal_states")
    norms, energy_values, density_numbers, dips = [], [], [], []
    expm_errors, kernel_errors = [], []
    projector_errors = {"paths": [], "phase": []}
    for k, t in enumerate(times):
        propagator = expm(-1j*Horth*t)
        for j in range(5):
            v = waves[j, k]
            expected = invroot@propagator@root@initial[j]
            expm_errors.append(maxabs(v-expected))
            independent_kernel = np.outer(v, v.conj()).real
            kernel_errors.append(maxabs(kernels[j, k]-independent_kernel))
            norms.append(float(np.vdot(v, s@v).real))
            density_numbers.append(float(np.trace(s@np.outer(v, v.conj())).real))
            energy_values.append(float(np.vdot(v, h@v).real))
            dips.append([float(np.real(np.trace(d@np.outer(v, v.conj())))) for d in mu])
        z = [root@waves[j, k] for j in range(5)]
        projector_errors["paths"].append(maxabs(np.outer(z[2], z[2].conj())-np.outer(z[3], z[3].conj())))
        projector_errors["phase"].append(maxabs(np.outer(z[0], z[0].conj())-np.outer(z[4], z[4].conj())))
    metrics.update(expm_vs_eigen_evolution_max=max(expm_errors), density_kernel_formula_error=max(kernel_errors),
                   norm_error_max=max(abs(n-1) for n in norms), density_number_error_max=max(abs(n-1) for n in density_numbers),
                   energy_conservation_max=max(abs(v-(e[0]+e[1])/2) for v in energy_values), projector_errors=projector_errors)
    require(metrics["expm_vs_eigen_evolution_max"] <= spec["evolution_tolerance"], "wrong_time_phase_or_state")
    require(metrics["density_kernel_formula_error"] <= spec["density_tolerance"], "density_imaginary_component_error")
    require(metrics["norm_error_max"] <= spec["norm_tolerance"] and metrics["density_number_error_max"] <= spec["norm_tolerance"], "state_normalization")
    require(metrics["energy_conservation_max"] <= spec["energy_tolerance"], "energy_expectation_or_conservation")
    require(summary.get("phase_same_physical_state") is True and summary.get("path_A_B_same_physical_state") is True, "physical_equivalence_classification")
    require(max(projector_errors["paths"]+projector_errors["phase"]) <= spec["projector_tolerance"], "global_phase_or_preparation_path")

    same_density = maxabs(kernels[0, 0]-kernels[1, 0])
    metrics["t0_density_kernel_difference"] = same_density
    require(same_density <= spec["density_tolerance"], "initial_density_not_equal")
    observed_dips = np.array(dips).reshape((len(times), 5, 3)).transpose(1, 0, 2)
    future_diffs = (observed_dips[0, :, 2]-observed_dips[1, :, 2]).tolist()
    metrics["dipole_z_differences"] = future_diffs
    require(all(abs(x) > spec["observable_difference_floor"] for x in future_diffs[1:]), "no_future_observable_difference")
    # Analytic two-root identity cross-check; executor evolves full M roots.
    analytic = [2*np.sin((e[1]-e[0])*t)*(u[:, 0]@mu[2]@u[:, 1]) for t in times]
    require(maxabs(np.array(future_diffs)-analytic) <= spec["observable_tolerance"], "dipole_time_sign_identity")
    require(summary.get("times_atomic") == times, "unsealed_time_points")
    require(maxabs(np.array(summary.get("dipole_z_differences", []))-future_diffs) <= spec["observable_tolerance"], "reported_observable_correspondence")
    flags = dict(P1="PASS", P2="PASS", P3="PASS", P4="PASS") if not errors else dict(P1="UNRESOLVED", P2="UNRESOLVED", P3="UNRESOLVED", P4="FAIL")
    return dict(status="PASS" if not errors else "FAIL", errors=errors, metrics=metrics, **flags,
                scope="author saved-matrix checker: finite closed fixed-nuclei pilot, no formal/external certification")
