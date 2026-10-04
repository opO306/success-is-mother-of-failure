"""Seal one geometry, source/thresholds/times; then acquire fresh AO states."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from scipy.linalg import eigh, solve

from .core import experiment, validate_input


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, x):
    with p.open("x", encoding="utf-8") as f:
        json.dump(x, f, indent=2, allow_nan=False)
        f.write("\n")


def sources():
    return {p.name: sha(p) for p in Path(__file__).parent.glob("*") if p.is_file()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--git-receipt", required=True)
    args = p.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    spec_path = Path(__file__).with_name("protocol.json")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    receipt_path = Path(args.git_receipt)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt["HEAD"] != "7b91cfff3642edcc5d957145052814e4cb0f3bbd" or receipt["origin_sector_SHA"] != receipt["HEAD"]:
        raise ValueError("REFUSED: wrong local/remote Sector baseline")
    if not all(sha(Path(k)) == v for k, v in receipt["protected_sha256"].items()):
        raise ValueError("REFUSED: historical source/evidence changed")
    import scipy
    import psi4
    seal = dict(protocol=spec, protocol_sha256=sha(spec_path), source_sha256=sources(),
                git_receipt=receipt, git_receipt_sha256=sha(receipt_path), python=sys.version,
                versions=dict(psi4=psi4.__version__, numpy=np.__version__, scipy=scipy.__version__),
                platform=platform.platform(), host=platform.node(),
                arithmetic="binary64 real generalized eigensolver, complex128 analytic/eigenbasis evolution; NOT bitwise A-world authority",
                utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    write(out/"seal.json", seal)
    for path in Path(__file__).parent.glob("*"):
        if path.is_file(): (out/(path.name+".executed.txt")).write_bytes(path.read_bytes())
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        case = spec["case"]; charge = validate_input(case)
        psi4.set_num_threads(1); psi4.core.set_output_file(str(out/"psi4.log"), False)
        lines = [f"{charge} 2"]+["H "+" ".join(format(v, ".17g") for v in n["position_bohr"]) for n in case["nuclei"]]
        mol = psi4.geometry("\n".join(lines+["units bohr", "symmetry c1", "no_com", "no_reorient"])+"\n")
        basis = psi4.core.BasisSet.build(mol, "BASIS", case["basis"], puream=1)
        shells = [[basis.shell(k).am]+[[basis.shell(k).exp(i), basis.shell(k).original_coef(i)] for i in range(basis.shell(k).nprimitive)] for k in range(basis.nshell())]
        baseline = json.loads(Path("docs/active/electronic_sector_panel_v1/desktop_seal.json").read_text(encoding="utf-8"))
        if shells != baseline["basis"]["shells"] or basis.nbf() != spec["basis_size"] or not basis.has_puream():
            raise ValueError("REFUSED: original full contracted TZ basis mismatch")
        mints = psi4.core.MintsHelper(basis)
        s = np.asarray(mints.ao_overlap()).copy()
        h = np.asarray(mints.ao_kinetic())+np.asarray(mints.ao_potential())
        mu = np.array([np.asarray(x) for x in mints.ao_dipole()])
        np.savez_compressed(out/"raw_AO.npz", s=s, h=h, dipoles=mu)
        if (np.max(np.abs(s-s.T)) > spec["hermiticity_tolerance"] or np.max(np.abs(h-h.T)) > spec["hermiticity_tolerance"] or
                np.max(np.abs(mu-mu.transpose(0, 2, 1))) > spec["hermiticity_tolerance"] or eigh(s, eigvals_only=True)[0] <= spec["overlap_floor"]):
            raise ValueError("REFUSED: raw AO Hermiticity/overlap; no averaging or solve")
        e, u = eigh(h, s, type=1, driver="gvd")  # ALL 28 roots and vectors.
        for k in range(len(e)):
            if u[int(np.argmax(np.abs(u[:, k]))), k] < 0: u[:, k] *= -1
        residual = h@u-(s@u)*e
        residual_norms = [float(np.sqrt(max(0., residual[:, k]@solve(s, residual[:, k])))) for k in range(len(e))]
        np.savez_compressed(out/"eigenstates.npz", s=s, h=h, dipoles=mu, energies=e, eigenvectors=u)
        if max(residual_norms) > spec["residual_tolerance"] or np.max(np.abs(u.T@s@u-np.eye(len(e)))) > spec["norm_tolerance"]:
            raise ValueError("REFUSED: S-metric eigenstates invalid")
        oldrows = json.loads(Path("docs/active/electronic_sector_panel_v1/desktop_results.json").read_text(encoding="utf-8"))["rows"]
        old = next(x for x in oldrows if x["case_key"] == "pair_doublet_1.4")
        nn = float(mol.nuclear_repulsion_energy())
        if abs(float(e[0])+nn-old["total_energy_hartree"]) > spec["baseline_energy_tolerance"]:
            raise ValueError("REFUSED: Sector energy control mismatch")
        arrays, summary = experiment(s, h, mu, e, u, spec)
        data = dict(s=s, h=h, dipoles=mu, energies=e, eigenvectors=u, **arrays)
        np.savez_compressed(out/"experiment.npz", **data)
        summary.update(input=case, E0_hartree=float(e[0]), E1_hartree=float(e[1]),
                       gap_hartree=float(e[1]-e[0]), nuclear_repulsion_hartree=nn,
                       E0_total_hartree=float(e[0])+nn, E1_total_hartree=float(e[1])+nn,
                       selected_residuals_S_metric=residual_norms[:2], all_root_residuals_S_metric=residual_norms,
                       eigenstate_orthogonality=float(u[:, 0]@s@u[:, 1]),
                       spatial_orbitals=len(e), retained_eigenvectors=len(e),
                       original_TZ_exact_basis_match=True, backend_charge_e=mol.molecular_charge(),
                       backend_multiplicity=mol.multiplicity(), backend_positions_bohr=np.asarray(mol.geometry()).tolist(),
                       dipole_sign_check_first_left_s_AO=float(mu[2, 0, 0]/s[0, 0]),
                       baseline_total_difference_hartree=float(e[0])+nn-old["total_energy_hartree"],
                       raw_AO_sha256={k: hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() for k, v in {"s": s, "h": h, "dipoles": mu}.items()},
                       raw_AO_matches_prior_S_h={k: hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest() == old["AO_sha256"][k] for k,v in {"s":s,"h":h}.items()},
                       wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu)
        from .checker import check
        verdict = check(data, summary, spec)
        summary.update(checker=verdict, status=verdict["status"],
                       protected_bytes_unchanged=all(sha(Path(k)) == v for k,v in receipt["protected_sha256"].items()),
                       source_bytes_unchanged=sources() == seal["source_sha256"],
                       artifact_sha256={name:sha(out/name) for name in ["raw_AO.npz","eigenstates.npz","experiment.npz"]})
        write(out/"results.json", summary)
        print(json.dumps({k:summary[k] for k in ["status","E0_hartree","E1_hartree","gap_hartree","density_kernel_max_differences","dipole_z_differences","wall_seconds"]},indent=2),flush=True)
        if verdict["status"] != "PASS": raise RuntimeError("STOP: independent author checker failed")
    except Exception as error:
        write(out/"failure.json",dict(status="REFUSED_OR_ERROR_PRESERVED",error=repr(error),traceback=traceback.format_exc()))
        raise


if __name__ == "__main__": main()
