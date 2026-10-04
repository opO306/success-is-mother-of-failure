"""Exclusive captures; seal source, inputs, thresholds, and provenance first."""
import argparse
import hashlib
import json
import multiprocessing as mp
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, obj):
    with p.open("x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write("\n")


def sources():
    return {p.name: sha(p) for p in Path(__file__).parent.glob("*") if p.is_file()}


def worker(case, spec, root):
    import resource
    root = Path(root)
    try:
        from .evaluator import solve
        row = solve(case, spec, root/"matrices.npz", root/"psi4.log")
    except Exception as e:
        row = dict(input=case, accepted=False, status="IMPLEMENTATION_ERROR_PRESERVED",
                   error=repr(e), traceback=traceback.format_exc(),
                   electronic_energy_hartree=None, total_energy_hartree=None)
    row["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    write(root/"result.json", row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--git-receipt", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    protocol_path = Path(__file__).with_name("protocol.json")
    spec = json.loads(protocol_path.read_text(encoding="utf-8"))
    receipt_path = Path(args.git_receipt)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt["HEAD"] != "5095b085502c2de4f2f34a48ab4a35d4d6aa75ca" or not receipt["generation1_is_ancestor"]:
        raise ValueError("REFUSED: incorrect ancestry")
    if any(sha(Path(p)) != h for p, h in receipt["protected_sha256"].items()):
        raise ValueError("REFUSED: historical bytes changed")
    import psi4
    import numpy as np
    import scipy
    psi4.set_num_threads(1)
    psi4.core.set_output_file(str(output/"basis_preflight.log"), False)
    mol = psi4.geometry("0 1\nH 0 0 -1\nH 0 0 1\nunits bohr\nsymmetry c1\nno_reorient\nno_com\n")
    basis = psi4.core.BasisSet.build(mol, "BASIS", "cc-pVTZ", puream=1)
    shells = [[basis.shell(k).am]+[[basis.shell(k).exp(i), basis.shell(k).original_coef(i)]
              for i in range(basis.shell(k).nprimitive)] for k in range(basis.nshell())]
    old = json.loads(Path("docs/active/h2_numerical_cause_v1/controls_seal.json").read_text(encoding="utf-8"))["hydrogen_basis_data"]["cc-pVTZ"]
    if shells != old+old or basis.nbf() != 28 or not basis.has_puream():
        raise ValueError("REFUSED: basis input does not exactly match original TZ")
    seal = dict(protocol=spec, protocol_sha256=sha(protocol_path), source_sha256=sources(),
                git_receipt=receipt, git_receipt_sha256=sha(receipt_path),
                host=platform.node(), platform=platform.platform(), python=sys.version,
                versions=dict(psi4=psi4.__version__, numpy=np.__version__, scipy=scipy.__version__),
                longdouble_nmant=np.finfo(np.longdouble).nmant,
                basis=dict(nbf=basis.nbf(), shells=shells, original_coefficients_exact_match=True,
                           file_sha256=sha(Path(psi4.core.get_datadir())/"basis/cc-pvtz.gbs")),
                linkage=subprocess.check_output(["ldd", psi4.core.__file__], text=True),
                created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    write(output/"seal.json", seal)
    for p in Path(__file__).parent.glob("*"):
        if p.is_file():
            (output/(p.name+".executed.txt")).write_bytes(p.read_bytes())
    rows, started = [], time.perf_counter()
    control_ok = True
    historical = json.loads(Path("docs/active/h2_numerical_cause_v1/controls_results.json").read_text(encoding="utf-8"))
    from .checker import valid
    for key in spec["execution_order"]:
        case = spec["cases"][key]
        point = output/key
        point.mkdir(exist_ok=False)
        process = mp.get_context("spawn").Process(target=worker, args=(case, spec, str(point)))
        process.start()
        process.join()
        if process.exitcode != 0 or not (point/"result.json").exists():
            write(point/"process_failure.json", dict(exitcode=process.exitcode))
            control_ok = False
            break
        row = json.loads((point/"result.json").read_text(encoding="utf-8"))
        row["case_key"] = key  # Reporting key added after physical evaluation.
        row["process_exitcode"] = process.exitcode
        rows.append(row)
        print(key, row["status"], row.get("failure_stage"), row.get("total_energy_hartree"), flush=True)
        if key in spec["historical_control_keys"]:
            r = abs(case["nuclei"][1]["position_bohr"][2]-case["nuclei"][0]["position_bohr"][2])
            baseline = next(x for x in historical["rows"] if x["basis"] == "cc-pVTZ" and x["R_bohr"] == r)
            control_ok = (valid(row, case, spec) and baseline["original"]["accepted"] and
                          abs(row["total_energy_hartree"]-baseline["original"]["energy"]) <= spec["control_energy_tolerance"] and
                          max(abs(a-b) for a, b in zip(row["overlap_eigenvalues"], baseline["paths"][0]["overlap_eigenvalues"])) <= spec["control_spectrum_tolerance"])
            if not control_ok:
                break  # No later panel execution after control failure.
        # Non-control refusals are preserved; independent other cases still run.
    result = dict(rows=rows, control_gate="PASS" if control_ok and all(k in {x["case_key"] for x in rows} for k in spec["historical_control_keys"]) else "STOP",
                  seal_sha256=sha(output/"seal.json"), wall_seconds=time.perf_counter()-started,
                  protected_bytes_unchanged=all(sha(Path(p)) == h for p, h in receipt["protected_sha256"].items()),
                  source_bytes_unchanged=sources() == seal["source_sha256"])
    write(output/"results.json", result)
    print(result["control_gate"], "rows", len(rows), "wall", result["wall_seconds"], flush=True)


if __name__ == "__main__":
    main()
