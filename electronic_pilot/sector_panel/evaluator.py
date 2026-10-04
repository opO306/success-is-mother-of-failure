"""One full finite-basis Coulomb law in one/two-electron spin sectors.

Independent Psi4/Libint AO; every orbital and every ERI retained. No
symmetrization, orbital cutoff, HF/DFT substitute, or reference energy.
"""
import hashlib
import time

import numpy as np
from scipy.linalg import eigh

from .contract import dimension, validate


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def symmetry(g):
    return {"ij": float(np.max(np.abs(g-g.swapaxes(0, 1)))),
            "kl": float(np.max(np.abs(g-g.swapaxes(2, 3)))),
            "pair": float(np.max(np.abs(g-g.transpose(2, 3, 0, 1))))}


def transform(s, h, g):
    c = eigh(h, s, type=1, driver="gvd")[1]  # All M generalized roots.
    x = c.astype(np.longdouble)
    sh, hh = x.T@s.astype(np.longdouble)@x, x.T@h.astype(np.longdouble)@x
    gg = np.einsum("pa,pqrs->aqrs", x, g.astype(np.longdouble), optimize=False)
    gg = np.einsum("qb,aqrs->abrs", x, gg, optimize=False)
    gg = np.einsum("rc,abrs->abcs", x, gg, optimize=False)
    gg = np.einsum("sd,abcs->abcd", x, gg, optimize=False)
    return c, sh, hh, gg


def matrix(h, g, electrons, sector):
    dimension(len(h), electrons, sector)
    if electrons == 1:
        return h.copy()
    i, j = np.triu_indices(len(h), 0 if sector == "singlet" else 1)
    a, b, c, d = i[:, None], j[:, None], i[None, :], j[None, :]

    def ordered(p, q, r, t):
        return h[p, r]*(q == t) + h[q, t]*(p == r) + g[p, r, q, t]

    sign = 1 if sector == "singlet" else -1
    m = ordered(a, b, c, d) + sign*ordered(a, b, d, c)
    m += sign*ordered(b, a, c, d) + ordered(b, a, d, c)
    norm = np.sqrt(np.longdouble(2)*(1+(i == j).astype(int)))
    return m/(norm[:, None]*norm[None, :])


def solve_integrals(case, s, h, g, spec, artifact):
    """Portable same-source saved-AO replay; this does NOT generate integrals."""
    charge = validate(case)
    m = len(s)
    if s.shape != (m, m) or h.shape != (m, m) or g.shape != (m,)*4:
        raise ValueError("REFUSED: incomplete full AO space")
    row = dict(input=case, electrons=case["electrons"], sector=case["sector"],
               derived_charge_e=charge, multiplicity={"doublet": 2, "singlet": 1, "triplet": 3}[case["sector"]],
               basis_size=m, ci_dimension=dimension(m, case["electrons"], case["sector"]),
               AO_sha256={"s": digest(s), "h": digest(h), "eri": digest(g)},
               longdouble_nmant=np.finfo(np.longdouble).nmant, accepted=False,
               status="REFUSED", electronic_energy_hartree=None, total_energy_hartree=None,
               failure_stage=None, iteration_count=None, spherical=True)
    nuclei = case["nuclei"]
    nn = sum(n["Z"]*q["Z"]/np.linalg.norm(np.array(n["position_bohr"])-q["position_bohr"])
             for k, n in enumerate(nuclei) for q in nuclei[k+1:])
    row["nuclear_repulsion_hartree"] = float(nn)
    w = eigh(s, eigvals_only=True)
    row.update(overlap_eigenvalues=w.tolist(), Smin=float(w[0]), condition=float(w[-1]/w[0]),
               AO_s_asymmetry=float(np.max(np.abs(s-s.T))), AO_h_asymmetry=float(np.max(np.abs(h-h.T))),
               AO_eri_symmetry=symmetry(g))
    vector = np.zeros(0)
    c, sh, hh, gg = transform(s, h, g)
    mat = matrix(hh, gg, case["electrons"], case["sector"])
    row.update(orthonormalization_error=float(np.linalg.norm(np.asarray(sh-np.eye(m), dtype=float), 2)),
               transformed_h_asymmetry=float(np.max(np.abs(hh-hh.T))),
               transformed_eri_symmetry=symmetry(gg), matrix_asymmetry=float(np.max(np.abs(mat-mat.T))))
    checks = [(m == 14*(len(nuclei)+len(case["ghost_centers_bohr"])), "basis_dimension"),
              (w[0] > spec["overlap_floor"], "overlap_floor"),
              (row["orthonormalization_error"] <= spec["orthogonality_tolerance"], "orthogonality"),
              (max(row["AO_s_asymmetry"], row["AO_h_asymmetry"], max(row["AO_eri_symmetry"].values())) <= spec["hermiticity_tolerance"], "AO_symmetry"),
              (max(row["transformed_h_asymmetry"], max(row["transformed_eri_symmetry"].values()), row["matrix_asymmetry"]) <= spec["hermiticity_tolerance"], "matrix_hermiticity")]
    row["failure_stage"] = next((name for ok, name in checks if not ok), None)
    if row["failure_stage"] is None:
        e, v = eigh(np.asarray(mat, dtype=float), subset_by_index=(0, 1), driver="evr")
        vector = v[:, 0]
        residual = mat@vector.astype(np.longdouble)-np.longdouble(e[0])*vector
        row.update(eigen_residual_l2=float(np.sqrt(residual@residual)),
                   vector_norm_error=float(abs(vector@vector-1)), next_sector_gap=float(e[1]-e[0]))
        if not np.isfinite(e[0]) or row["eigen_residual_l2"] > spec["residual_tolerance"] or row["vector_norm_error"] > spec["norm_tolerance"]:
            row["failure_stage"] = "eigen_residual_or_norm"
        else:
            row.update(accepted=True, status="NUMERICAL_RESULT_NOT_CERTIFIED",
                       electronic_energy_hartree=float(e[0]), total_energy_hartree=float(e[0])+float(nn))
    np.savez_compressed(artifact, s=s, h_ao=h, eri_ao=g, c=c, h=hh, eri=gg, vector=vector)
    row.update(artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
               artifact_file=artifact.name, matrix_dimension=len(mat), matrix_bytes=mat.nbytes)
    return row


def solve(case, spec, artifact, log):
    import psi4
    charge = validate(case)
    if np.finfo(np.longdouble).nmant != 63:
        raise ValueError("REFUSED: sealed desktop extended format unavailable")
    wall, cpu = time.perf_counter(), time.process_time()
    psi4.set_num_threads(1)
    psi4.core.set_output_file(str(log), False)
    mult = {"doublet": 2, "singlet": 1, "triplet": 3}[case["sector"]]
    # Z=1 is the only supported nucleus; H here is an element/basis identity.
    lines = [f"{charge} {mult}"]
    lines += ["H " + " ".join(format(x, ".17g") for x in n["position_bohr"]) for n in case["nuclei"]]
    lines += ["@H " + " ".join(format(x, ".17g") for x in p) for p in case["ghost_centers_bohr"]]
    lines += ["units bohr", "symmetry c1", "no_reorient", "no_com"]
    mol = psi4.geometry("\n".join(lines)+"\n")
    bs = psi4.core.BasisSet.build(mol, "BASIS", case["basis"], puream=1)
    mi = psi4.core.MintsHelper(bs)
    s = np.asarray(mi.ao_overlap()).copy()
    h = np.asarray(mi.ao_kinetic())+np.asarray(mi.ao_potential())
    g = np.asarray(mi.ao_eri()).reshape((bs.nbf(),)*4).copy()
    row = solve_integrals(case, s, h, g, spec, artifact)
    row.update(backend="Psi4/Libint independent binary64 AO, extended full contractions, binary64 LAPACK",
               basis_shells=bs.nshell(), spherical=bs.has_puream(),
               backend_charge_e=mol.molecular_charge(), backend_multiplicity=mol.multiplicity(),
               backend_positions_bohr=np.asarray(mol.geometry()).tolist(),
               backend_nuclear_repulsion_hartree=float(mol.nuclear_repulsion_energy()),
               wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu)
    return row
