"""Fresh QZ atom diagnostics and existing independent postprocessing criteria.

The QZ-only adapter is a record view, not a modified physical protocol. No old
QZ curve energies are spliced into the fresh 44-point campaign.
"""
import argparse
import csv
import hashlib
import json
import time
from pathlib import Path
from electronic_pilot.check_reference import compare


def curve_records(data,atoms):
    rows=atoms.copy()
    for r in data["rows"]:
        row=dict(r["paths"][0])
        if row["accepted"]:
            row["process_peak_rss_bytes"]=r["process_peak_rss_bytes"]
            rows.append(row)
        else:
            rows.append(dict(status="FAILED_PRESERVED",job=dict(kind="curve",basis="cc-pVQZ",R=r["R_bohr"]),
                             error=f"REFUSED: {row['failure_stage']}; diagnostics retained in fresh curve"))
    return dict(rows=rows)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--output",default="physical_comparison_v2")
    args=p.parse_args()
    root=Path(args.root)
    target=root/args.output
    target.mkdir(exist_ok=False)
    parent=Path("electronic_pilot/protocol_v2.json")
    spec=json.loads(parent.read_text())
    raw=root/"qz_curve/results.json"
    data=json.loads(raw.read_text())
    if len(data["rows"])!=44:
        raise ValueError("new whole-QZ campaign unfinished")
    reference=Path("electronic_pilot/reference_pachucki_v2.csv")
    seal=dict(parent_protocol_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),
              curve_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
              reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
              original_criteria=spec["criteria"],new_atom_and_ghost_basis="cc-pVQZ",
              atom_executor_sha256=hashlib.sha256(Path("electronic_pilot/solver.py").read_bytes()).hexdigest(),
              postprocessor_sha256=hashlib.sha256(Path("electronic_pilot/check_reference.py").read_bytes()).hexdigest())
    (target/"seal.json").write_text(json.dumps(seal,indent=2)+"\n",encoding="utf-8")
    from electronic_pilot.solver import atom_energy
    atoms=[]
    for distance in (None,1.,2.,6.,20.):
        start=time.perf_counter()
        atoms.append(dict(kind="atom",basis="cc-pVQZ",ghost_distance=distance,
                          energy_hartree=atom_energy("cc-pVQZ",distance),wall_seconds=time.perf_counter()-start))
    record=curve_records(data,atoms)
    (target/"checker_records.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    view=dict(spec,bases=["cc-pVQZ"])
    with reference.open() as f:
        result=compare(record,view,list(csv.DictReader(f)))
    result["scope"]="fresh QZ-only record view; original parent thresholds unchanged; no old curve values used"
    result["original_criteria"]=spec["criteria"]
    (target/"comparison.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result["summaries"],indent=2))


if __name__=="__main__":
    main()
