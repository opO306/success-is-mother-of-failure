"""Full eigenbasis unitary evolution, not an electron/nuclear engine.

No ground-root re-solve, integrator, truncation, chemistry label, or history
authority. Initial superpositions populate two roots by preparation; ALL
M eigenvectors remain available in propagation and are saved.
"""
import numpy as np


def validate_input(case):
    if set(case) != {"nuclei", "electrons", "sector", "basis", "law"}:
        raise ValueError("REFUSED: invalid authority/chemical label")
    if type(case["electrons"]) is not int or case["electrons"] != 1 or case["sector"] != "doublet":
        raise ValueError("REFUSED: electron/sector mismatch")
    if case["basis"] != "cc-pVTZ" or case["law"] != "isolated_clamped_nonrelativistic_coulomb":
        raise ValueError("REFUSED: law/basis mismatch")
    if case["nuclei"] != [{"Z": 1, "position_bohr": [0., 0., -.7]}, {"Z": 1, "position_bohr": [0., 0., .7]}]:
        raise ValueError("REFUSED: outside sealed single geometry")
    return sum(x["Z"] for x in case["nuclei"])-case["electrons"]


def canonicalize(v):
    """Only global gauge; never used to make +/- physical states equal."""
    k = int(np.argmax(np.abs(v)))
    if abs(v[k]) == 0:
        raise ValueError("REFUSED: zero state")
    return v*np.exp(-1j*np.angle(v[k]))


def coefficients(eigenvectors, sign):
    if sign not in (-1, 1):
        raise ValueError("invalid superposition sign")
    return (eigenvectors[:, 0]+sign*1j*eigenvectors[:, 1])/np.sqrt(2.)


def evolve(initial, s, energies, eigenvectors, times):
    amplitudes = eigenvectors.T@s@initial
    return np.array([eigenvectors@(np.exp(-1j*energies*t)*amplitudes) for t in times])


def density_kernel(v):
    """n(r)=chi(r)^T K chi(r) for the complete REAL AO basis.

K is NOT the full quantum density operator: imaginary coherence is absent.
"""
    return np.outer(v.real, v.real)+np.outer(v.imag, v.imag)


def same_pure_state(a, b, s, tolerance):
    na, nb = np.vdot(a, s@a).real, np.vdot(b, s@b).real
    if abs(na-1) > tolerance or abs(nb-1) > tolerance:
        return False
    return bool(abs(1-abs(np.vdot(a, s@b))**2) <= tolerance)


def observe(v, s, h, dipoles):
    return dict(norm=float(np.vdot(v, s@v).real),
                electronic_energy_hartree=float(np.vdot(v, h@v).real),
                electron_number_integral=float(np.sum(s*density_kernel(v))),
                electronic_dipole_au=[float(np.vdot(v, d@v).real) for d in dipoles])


def experiment(s, h, dipoles, energies, eigenvectors, spec):
    plus, minus = coefficients(eigenvectors, 1), coefficients(eigenvectors, -1)
    times, theta = spec["times_atomic"], spec["global_phase_radians"]
    path_a = canonicalize(plus)
    phase_input = np.exp(1j*theta)*plus
    path_b = canonicalize(phase_input)
    initials = np.array([plus, minus, path_a, path_b, phase_input])
    waves = np.array([evolve(v, s, energies, eigenvectors, times) for v in initials])
    kernels = np.array([[density_kernel(v) for v in series] for series in waves])
    observations = [[observe(v, s, h, dipoles) for v in series] for series in waves]
    summary = dict(times_atomic=times, labels=["plus", "minus", "path_A", "path_B", "global_phase_input"],
                   observations=observations,
                   initial_plus_minus_overlap_abs=float(abs(np.vdot(plus, s@minus))),
                   initial_plus_minus_density_kernel_max=float(np.max(np.abs(density_kernel(plus)-density_kernel(minus)))),
                   initial_plus_minus_energy_difference=abs(observe(plus, s, h, dipoles)["electronic_energy_hartree"]-observe(minus, s, h, dipoles)["electronic_energy_hartree"]),
                   density_kernel_max_differences=[float(np.max(np.abs(kernels[0, k]-kernels[1, k]))) for k in range(len(times))],
                   dipole_z_differences=[observations[0][k]["electronic_dipole_au"][2]-observations[1][k]["electronic_dipole_au"][2] for k in range(len(times))],
                   path_A_B_raw_initial_max=float(np.max(np.abs(path_a-path_b))),
                   phase_same_physical_state=same_pure_state(plus, phase_input, s, spec["norm_tolerance"]),
                   path_A_B_same_physical_state=same_pure_state(path_a, path_b, s, spec["norm_tolerance"]),
                   no_history_argument=True)
    return dict(initials=initials, waves=waves, density_kernels=kernels), summary
