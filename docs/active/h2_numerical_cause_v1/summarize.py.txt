"""Derived evidence summary; every number remains traceable to raw stage rows."""
import argparse
from collections import Counter
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    args=p.parse_args()
    root=Path(args.root)
    paths={x:root/x/"results.json" for x in ("controls","reproduce","compare","qz_curve","high_precision_v2")}
    inputs={k:json.loads(x.read_text()) for k,x in paths.items()}
    controls=inputs["controls"]["rows"]
    original=max(abs(r["original"]["energy"]-x["total_energy_hartree"]) for r in controls for x in r["paths"])
    cmax=max(r["coordinate_equivalence"][p]["coordinate_map_orthogonality"] for r in controls for p in r["coordinate_equivalence"])
    reconstruction=max(r["coordinate_equivalence"][p]["reconstruction_relative_norm"] for r in controls for p in r["coordinate_equivalence"])
    hp=[]
    with localcontext() as ctx:
        ctx.prec=100
        for r in inputs["high_precision_v2"]["rows"]:
            measured=Decimal(str(r["binary64_worst_coupling"]["asymmetry"]))
            fixed=Decimal(r["fixed_binary64_C_80digit_contraction"]["total"])
            fine=Decimal(r["high_precision_coordinates"]["80"]["propagated_asymmetry"]["total"])
            less=Decimal(r["high_precision_coordinates"]["60"]["propagated_asymmetry"]["total"])
            hp.append(dict(R_bohr=r["R_bohr"],binary64_measured_signed_asymmetry=str(measured),
                           AO_input_propagated_with_fixed_binary64_C=str(fixed),
                           remaining_binary64_transform_and_assembly_component=str(measured-fixed),
                           high_precision_coordinate_effect_on_AO_component=str(fine-fixed),
                           coordinate_60_to_80_digit_change=str(fine-less),
                           high_precision_raw_S_orth_error_frobenius_upper=r["high_precision_coordinates"]["80"]["orth_error_frobenius_upper"],
                           scope="one original worst Cholesky/common-AO singlet coupling; not full-matrix enclosure"))
    out=dict(status="NUMERICAL_CAUSE_IDENTIFIED_FOR_SAMPLED_DIAGNOSTICS_NOT_CERTIFIED",
             controls_count=len(controls),control_calculations=sum(len(r["paths"]) for r in controls),
             max_control_energy_difference_hartree=original,
             max_control_coordinate_map_orthogonality=cmax,max_control_coordinate_reconstruction_relative_norm=reconstruction,
             reproduced_original_failures=sum(not r["original"]["accepted"] for r in inputs["reproduce"]["rows"]),
             reproduction_failure_stages=dict(Counter(r["paths"][0]["failure_stage"] for r in inputs["reproduce"]["rows"])),
             new_QZ_curve_computed=sum(r["paths"][0]["accepted"] for r in inputs["qz_curve"]["rows"]),
             new_QZ_curve_attempted=len(inputs["qz_curve"]["rows"]),
             new_QZ_failure_stages=dict(Counter(r["paths"][0]["failure_stage"] for r in inputs["qz_curve"]["rows"] if not r["paths"][0]["accepted"])),
             high_precision_decomposition=hp,
             stage_wall_seconds={k:v["wall_seconds"] for k,v in inputs.items()},
             sequential_stage_wall_sum_seconds=sum(v["wall_seconds"] for v in inputs.values()),
             cost_scope="completed stage execution only; initial HP/adapter failures, preparation, tests, atom diagnostics excluded",
             stage_peak_rss_bytes={k:max(r["process_peak_rss_bytes"] for r in v["rows"]) for k,v in inputs.items()},
             input_sha256={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in paths.items()})
    (root/"summary.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2))


if __name__=="__main__":
    main()
