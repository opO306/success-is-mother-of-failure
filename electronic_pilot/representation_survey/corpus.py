"""Reuse sealed AO/state artifacts; no new integrals, basis, or law."""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from electronic_pilot.sector_panel.evaluator import matrix
from electronic_pilot.sector_panel.action_check import action


def digest(v):
    return hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()


def unpack(v, m):
    i, j = np.triu_indices(m)
    w = np.zeros((m, m), dtype=complex)
    values = v/np.sqrt(2*(1+(i == j)))
    w[i, j] = values
    w[j, i] += values
    return w


def pack(w):
    i, j = np.triu_indices(len(w))
    return w[i, j]*np.sqrt(2/(1+(i == j)))


def density(v, data):
    if data["electrons"] == 1:
        return np.outer(v, v.conj()).real
    w = unpack(v, len(data["c"]))
    gamma = 2*w@w.conj().T
    return (data["c"]@gamma@data["c"].T).real


def observe(v, data):
    return dict(norm=float(np.vdot(v, data["s"]@v).real),
                energy=float(np.vdot(v, data["h"]@v).real),
                dipole=[float(np.vdot(v, op@v).real) for op in data["dipoles"]])


def evolve(v, data, times):
    a = data["u"].T@data["s"]@v
    return np.array([data["u"]@(np.exp(-1j*data["e"]*t)*a) for t in times])


def initial_states(u, theta):
    plus = (u[:, 0]+1j*u[:, 1])/np.sqrt(2)
    return np.array([u[:, 0].astype(complex), u[:, 1].astype(complex),
                     plus, plus.conj(), np.exp(1j*theta)*plus])


def build(root, output, protocol):
    root, output = Path(root), Path(output)
    history = root/"docs/active/electronic_state_history_v1"
    result = json.loads((history/"desktop_results.json").read_text(encoding="utf-8"))
    path = history/"desktop_experiment.npz"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == result["artifact_sha256"]["experiment.npz"]
    with np.load(path) as z:
        A = {k:z[k].copy() for k in ["s", "h", "dipoles", "energies", "eigenvectors"]}
        oldplus, oldminus = z["initials"][:2].copy()
    A["e"], A["u"] = A.pop("energies"), A.pop("eigenvectors")
    A.update(electrons=1, sector="doublet-one-spin-projection", c=np.eye(28))
    A["states"] = initial_states(A["u"], protocol["global_phase_radians"])
    assert np.array_equal(A["states"][2], oldplus) and np.array_equal(A["states"][3], oldminus)
    A["states"][2:4] = [oldplus, oldminus]  # Preserve signed-zero bits too.
    old = json.loads((root/"docs/active/electronic_sector_panel_v1/desktop_results.json").read_text(encoding="utf-8"))
    row = next(r for r in old["rows"] if r["case_key"] == "pair_singlet_1.4")
    bpath = output.parent/"prior_singlet_matrices.npz"
    assert hashlib.sha256(bpath.read_bytes()).hexdigest() == row["artifact_sha256"]
    with np.load(bpath) as z:
        s, hao, c, hmo, g, prior = [z[k].copy() for k in ["s", "h_ao", "c", "h", "eri", "vector"]]
    assert digest(s) == digest(A["s"]) and digest(hao) == digest(A["h"])
    full = matrix(hmo, g, 2, "singlet")  # Existing sealed full-space law.
    assert full.shape == (406, 406)
    assert np.max(np.abs(full-full.T)) <= protocol["hermiticity_tolerance"]
    h = np.asarray(full, dtype=float)  # No symmetrization or tolerance change.
    e, u = eigh(h, driver="evd")       # All 406 eigenvectors retained.
    for k in range(len(e)):
        if u[np.argmax(abs(u[:, k])), k] < 0: u[:, k] *= -1
    errors = [action(hmo, g, u[:, k], e[k], 2, "singlet") for k in range(2)]
    assert all(x["product_residual_l2"] <= protocol["residual_tolerance"] for x in errors)
    assert abs(e[0]-row["electronic_energy_hartree"]) <= protocol["observable_tolerance"]
    prior_overlap = abs(np.vdot(prior, u[:, 0]))
    assert abs(prior_overlap-1) <= protocol["norm_tolerance"]
    mu = [np.asarray(c.T.astype(np.longdouble)@x.astype(np.longdouble)@c.astype(np.longdouble),
                     dtype=float) for x in A["dipoles"]]
    dipoles = []
    basis_waves = [unpack(np.eye(406)[k], 28) for k in range(406)]
    for op in mu:
        dipoles.append(np.column_stack([pack(op@w+w@op.T) for w in basis_waves]).real)
    B = dict(s=np.eye(406), h=h, dipoles=np.array(dipoles), e=e, u=u, c=c,
             electrons=2, sector="full-singlet", states=initial_states(u, protocol["global_phase_radians"]))
    metadata = dict(A={"source":str(path.relative_to(root)), "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                       "dimension":28, "electrons":1, "sector":A["sector"]},
                    B={"source":"prior_singlet_matrices.npz", "sha256":row["artifact_sha256"],
                       "dimension":406, "electrons":2, "sector":B["sector"],
                       "new_saved_H_full_eigensolve":True, "fresh_AO":False,
                       "root0_difference_hartree":float(e[0]-row["electronic_energy_hartree"]),
                       "prior_ground_overlap_abs":float(prior_overlap), "independent_product_actions":errors,
                       "max_all_root_residual":float(np.max(np.linalg.norm(h@u-u*e, axis=0))),
                       "all_eigenvectors_retained":406, "E0":float(e[0]), "E1":float(e[1])})
    corpora = {"A":A, "B":B}
    for key, data in corpora.items():
        data["contract"] = dict(law_fingerprint=digest(data["h"]), basis_contract="cc-pVTZ-R1.4-full-space-"+key,
                                N_e=data["electrons"], sector=data["sector"], dimension=len(data["h"]))
        np.savez_compressed(output/(key+"_corpus.npz"),
                            **{k:v for k,v in data.items() if isinstance(v, np.ndarray)})
        (output/(key+"_contract.json")).write_text(json.dumps(data["contract"], indent=2)+"\n", encoding="utf-8")
    return corpora, metadata
