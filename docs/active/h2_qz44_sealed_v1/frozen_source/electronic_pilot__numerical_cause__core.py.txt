"""Three invertible coordinates of one full AO span; diagnostics before guards.

No averaging, AO/basis truncation, reference-energy input, or SCF is used.
The outcore path is the historical transformation. The incore path uses one
stored, uncompressed libcint tensor shared byte-for-byte by all coordinates.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import numpy as np
from scipy.linalg import cholesky, eigh, solve_triangular
from electronic_pilot.solver import singlet_matrix

PATHS = ("symmetric", "cholesky", "generalized_h")


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def ao_data(basis, r):
    from pyscf import gto, lib
    lib.num_threads(1)
    mol = gto.M(atom=[("H", (0, 0, -r/2)), ("H", (0, 0, r/2))],
                basis=basis, unit="Bohr", charge=0, spin=0,
                symmetry=False, cart=False, verbose=0)
    s = mol.intor("int1e_ovlp")
    h = mol.intor("int1e_kin")+mol.intor("int1e_nuc")
    eri = mol.intor("int2e", aosym="s1")
    return mol, s, h, eri


def coordinates(s, h, path):
    if path == "symmetric":
        w, u = eigh(s)
        if w[0] <= 0:
            raise ValueError("nonpositive overlap; no deletion allowed")
        return u @ np.diag(w**-0.5) @ u.T
    if path == "cholesky":
        # S=LL^T, C=L^-T, hence C^T S C=L^-1 LL^T L^-T=I.
        l = cholesky(s, lower=True)
        return solve_triangular(l.T, np.eye(len(s)), lower=False)
    if path == "generalized_h":
        # All M vectors retained; no occupancy/truncation/ground orbital choice.
        return eigh(h, s, type=1, driver="gvd")[1]
    raise ValueError("unknown coordinate path")


def symmetry(eri):
    return {"ij_swap_max": float(np.max(np.abs(eri-eri.swapaxes(0, 1)))),
            "kl_swap_max": float(np.max(np.abs(eri-eri.swapaxes(2, 3)))),
            "pair_swap_max": float(np.max(np.abs(eri-eri.transpose(2, 3, 0, 1))))}


def inspect_path(mol, s, h_ao, eri_ao, path, backend, *, artifact=None):
    from pyscf import ao2mo
    started = time.perf_counter()
    w = eigh(s, eigvals_only=True)
    c = coordinates(s, h_ao, path)
    orth = float(np.linalg.norm(c.T@s@c-np.eye(len(s)), ord=2))
    h = c.T@h_ao@c
    if backend == "original_outcore":
        eri = ao2mo.kernel(mol, c, compact=False).reshape((len(s),)*4)
    elif backend == "common_ao_incore":
        eri = ao2mo.kernel(eri_ao, c, compact=False).reshape((len(s),)*4)
    else:
        raise ValueError("unknown backend")
    mat, *_ = singlet_matrix(h, eri)
    asym = float(np.max(np.abs(mat-mat.T)))
    row = dict(path=path, backend=backend, basis_size=len(s), singlet_dimension=len(mat),
               overlap_eigenvalues=w.tolist(), Smin=float(w[0]), condition=float(w[-1]/w[0]),
               orthonormalization_error=orth, transformed_h_asymmetry=float(np.max(np.abs(h-h.T))),
               transformed_eri_symmetry=symmetry(eri), singlet_asymmetry=asym,
               max_abs_C=float(np.max(np.abs(c))), C_singular_values=np.linalg.svd(c, compute_uv=False).tolist(),
               shared_AO_sha256={"s": digest(s), "h": digest(h_ao), "eri_s1": digest(eri_ao)},
               failure_stage=None, accepted=False, electronic_energy_hartree=None,
               total_energy_hartree=None, eigen_residual_l2=None, vector_norm_error=None,
               arithmetic="binary64; no rigorous bound", iteration_count=None)
    # Diagnose later stages even after an earlier guard fails. No energy from
    # a refused matrix is accepted or silently fed to a Hermitian solver.
    if w[0] <= 1e-10:
        row["failure_stage"] = "overlap_floor"
    elif orth > 1e-10:
        row["failure_stage"] = "orthonormalization"
    elif asym > 1e-10:
        row["failure_stage"] = "singlet_hermiticity"
    else:
        e, v = eigh(mat, subset_by_index=(0, 1), driver="evr")
        residual = float(np.linalg.norm(mat@v[:, 0]-e[0]*v[:, 0]))
        norm = float(abs(v[:, 0]@v[:, 0]-1))
        row.update(electronic_energy_hartree=float(e[0]),
                   total_energy_hartree=float(e[0])+float(mol.energy_nuc()),
                   nuclear_repulsion_hartree=float(mol.energy_nuc()),
                   eigen_residual_l2=residual, vector_norm_error=norm)
        if residual > 1e-9 or norm > 1e-10 or not np.isfinite(e[0]):
            row["failure_stage"] = "eigensolve"
        else:
            row["accepted"] = True
        if artifact is not None:
            np.savez_compressed(artifact, c=c, h=h, eri=eri, vector=v[:, 0], s=s)
            row["artifact_sha256"] = hashlib.sha256(Path(artifact).read_bytes()).hexdigest()
    row["wall_seconds"] = time.perf_counter()-started
    return row, c


def coordinate_equivalence(s, ca, cb):
    u = ca.T@s@cb
    return dict(full_dimension=len(s), coordinate_map_orthogonality=float(np.linalg.norm(u.T@u-np.eye(len(s)), ord=2)),
                reconstruction_relative_norm=float(np.linalg.norm(ca@u-cb)/np.linalg.norm(cb)),
                note="Numerical coordinate-map diagnostic; analytic equivalence requires nonsingular full C and exact C^T S C=I")
