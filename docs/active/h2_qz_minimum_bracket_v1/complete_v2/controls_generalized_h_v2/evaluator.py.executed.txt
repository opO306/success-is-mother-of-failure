"""Independent Libint AO -> full two-electron singlet reference.

No PySCF, historical solver, reference table, energy hint, or world imports.
Longdouble contracts *new independent binary64 AO integrals*. This is not
arbitrary-precision AO evaluation and does not repair historical AO values.
"""
from __future__ import annotations

import hashlib
import time

import numpy as np
from scipy.linalg import cholesky, eigh, solve_triangular


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def symmetry(g):
    return {"ij_swap_max": float(np.max(np.abs(g-g.swapaxes(0, 1)))),
            "kl_swap_max": float(np.max(np.abs(g-g.swapaxes(2, 3)))),
            "pair_swap_max": float(np.max(np.abs(g-g.transpose(2, 3, 0, 1))))}


def transform(s, h, g, coordinate_path="cholesky"):
    """Invertible full span, no coefficient or orbital deletion."""
    if coordinate_path == "cholesky":
        c = solve_triangular(cholesky(s, lower=True).T, np.eye(len(s)), lower=False)
    elif coordinate_path == "generalized_h":
        c = eigh(h, s, type=1, driver="gvd")[1]  # ALL M roots retained.
    else:
        raise ValueError("unsupported full-span coordinates")
    x = c.astype(np.longdouble)
    sh = x.T @ s.astype(np.longdouble) @ x
    hh = x.T @ h.astype(np.longdouble) @ x
    # These contractions evaluate every entry. No packing, averaging or
    # copied transformed permutations force a symmetric output.
    gg = np.einsum("pa,pqrs->aqrs", x, g.astype(np.longdouble), optimize=False)
    gg = np.einsum("qb,aqrs->abrs", x, gg, optimize=False)
    gg = np.einsum("rc,abrs->abcs", x, gg, optimize=False)
    gg = np.einsum("sd,abcs->abcd", x, gg, optimize=False)
    return c, sh, hh, gg


def singlet(h, g):
    """Direct four ordered-pair contributions, independently assembled."""
    n = len(h)
    i, j = np.triu_indices(n)
    a, b = i[:, None], j[:, None]
    c, d = i[None, :], j[None, :]

    def ordered(p, q, r, t):
        return h[p, r]*(q == t) + h[q, t]*(p == r) + g[p, r, q, t]

    m = ordered(a, b, c, d)
    m += ordered(a, b, d, c)
    m += ordered(b, a, c, d)
    m += ordered(b, a, d, c)
    norm = np.sqrt(np.longdouble(2)*(1+(i == j).astype(int)))
    m /= norm[:, None]*norm[None, :]
    return m


def guard(row, spec, stage):
    if stage == "matrix":
        checks = [(row["basis_size"] == spec["basis_size"], "basis_dimension"),
                  (row["singlet_dimension"] == spec["singlet_dimension"], "singlet_dimension"),
                  (row["Smin"] > spec["overlap_min_eigenvalue_floor"], "overlap_floor"),
                  (row["orthonormalization_error"] <= spec["orthonormalization_max_norm"], "orthonormalization"),
                  (row["transformed_h_asymmetry"] <= spec["hermitian_max_asymmetry"], "h_hermiticity"),
                  (max(row["transformed_eri_symmetry"].values()) <= spec["hermitian_max_asymmetry"], "eri_permutation"),
                  (row["singlet_asymmetry"] <= spec["hermitian_max_asymmetry"], "singlet_hermiticity")]
    elif stage == "solve":
        checks = [(row["eigen_residual_l2"] <= spec["eigen_residual_max_l2_hartree"], "eigen_residual"),
                  (row["vector_norm_error"] <= spec["vector_norm_error_max"], "vector_norm"),
                  (np.isfinite(row["electronic_energy_hartree"]), "nonfinite_energy")]
    else:
        raise ValueError("unknown guard stage")
    return next((name for passed, name in checks if not passed), None)


def solve(r, spec, artifact, log):
    import psi4
    if not np.isfinite(r) or r <= 0 or spec["electrons"] != 2 or spec["basis"] != "cc-pVQZ":
        raise ValueError("unsupported reference input")
    if np.finfo(np.longdouble).nmant != spec["longdouble_required_nmant"]:
        raise ValueError("sealed longdouble format unavailable")
    wall, cpu = time.perf_counter(), time.process_time()
    psi4.set_num_threads(1)
    psi4.core.set_output_file(str(log), False)
    mol = psi4.geometry(f"0 1\nH 0 0 {-r/2:.17g}\nH 0 0 {r/2:.17g}\nunits bohr\nsymmetry c1\nno_reorient\nno_com\n")
    bs = psi4.core.BasisSet.build(mol, "BASIS", "cc-pVQZ", puream=1)
    mints = psi4.core.MintsHelper(bs)
    s = np.asarray(mints.ao_overlap()).copy()
    h = np.asarray(mints.ao_kinetic())+np.asarray(mints.ao_potential())
    g = np.asarray(mints.ao_eri()).reshape((bs.nbf(),)*4).copy()
    integral_seconds = time.perf_counter()-wall
    w = eigh(s, eigvals_only=True)
    row = dict(R_bohr=r, basis="cc-pVQZ", basis_size=bs.nbf(),
               singlet_dimension=bs.nbf()*(bs.nbf()+1)//2,
               electrons=2, sector=spec["sector"], charge=mol.molecular_charge(),
               multiplicity=mol.multiplicity(), positions_bohr=np.asarray(mol.geometry()).tolist(),
               spherical=bs.has_puream(), overlap_eigenvalues=w.tolist(), Smin=float(w[0]),
               condition=float(w[-1]/w[0]), AO_s_asymmetry=float(np.max(np.abs(s-s.T))),
               AO_h_asymmetry=float(np.max(np.abs(h-h.T))), AO_eri_symmetry=symmetry(g),
               AO_sha256={"s": digest(s), "h": digest(h), "eri": digest(g)},
               nuclear_repulsion_hartree=float(mol.nuclear_repulsion_energy()),
               accepted=False, status="REFUSED", failure_stage=None,
               electronic_energy_hartree=None, total_energy_hartree=None,
               eigen_residual_l2=None, vector_norm_error=None,
               iteration_count=None, integral_seconds=integral_seconds,
               method="Psi4/Libint AO binary64, extended contractions, full singlet, LAPACK",
               longdouble_nmant=np.finfo(np.longdouble).nmant,
               precision_note="64 significand bits in contractions, binary64 independent AO and eigensolve; no rigorous enclosure")
    row["coordinate_path"] = spec.get("coordinate_path", "cholesky")
    c, sh, hh, gg = transform(s, h, g, row["coordinate_path"])
    row["transformation_seconds"] = time.perf_counter()-wall-integral_seconds
    row["orthonormalization_error"] = float(np.linalg.norm(np.asarray(sh-np.eye(len(s)), dtype=float), ord=2))
    row["transformed_h_asymmetry"] = float(np.max(np.abs(hh-hh.T)))
    row["transformed_eri_symmetry"] = symmetry(gg)
    start = time.perf_counter()
    mat = singlet(hh, gg)
    row["assembly_seconds"] = time.perf_counter()-start
    row["singlet_asymmetry"] = float(np.max(np.abs(mat-mat.T)))
    row["failure_stage"] = guard(row, spec, "matrix")
    vector = np.zeros(0)
    if row["failure_stage"] is None:
        start = time.perf_counter()
        e, v = eigh(np.asarray(mat, dtype=float), subset_by_index=(0, 1), driver="evr")
        vector = v[:, 0]
        residual = mat@vector.astype(np.longdouble)-np.longdouble(e[0])*vector
        row.update(eigen_residual_l2=float(np.sqrt(residual@residual)),
                   vector_norm_error=float(abs(vector@vector-1)),
                   electronic_energy_hartree=float(e[0]), next_singlet_gap=float(e[1]-e[0]),
                   diagonalize_seconds=time.perf_counter()-start)
        row["failure_stage"] = guard(row, spec, "solve")
        if row["failure_stage"] is None:
            row.update(accepted=True, status="NUMERICAL_RESULT_NOT_CERTIFIED",
                       total_energy_hartree=float(e[0])+row["nuclear_repulsion_hartree"])
        else:
            row["electronic_energy_hartree"] = None
    np.savez_compressed(artifact, s=s, h_ao=h, eri_ao=g, c=c, h=hh, eri=gg,
                        singlet_vector=vector, positions=np.asarray(mol.geometry()))
    row.update(artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
               artifact_file=artifact.name, wall_seconds=time.perf_counter()-wall,
               cpu_seconds=time.process_time()-cpu,
               AO_eri_bytes=g.nbytes, transformed_eri_bytes=gg.nbytes,
               singlet_matrix_bytes=mat.nbytes)
    return row
