"""Apply sealed diagnostic selection without consulting physical reference."""
import argparse
import hashlib
import json
from pathlib import Path


def select(controls, comparison, spec):
    expected={(b,r) for b,grid in spec["controls"].items() for r in grid}
    if {(r["basis"],r["R_bohr"]) for r in controls["rows"]}!=expected:
        raise ValueError("incomplete controls")
    ranking=[]
    for path in spec["paths"]:
        for backend in spec["transform_backends"]:
            records=[next(x for x in r["paths"] if x["path"]==path and x["backend"]==backend) for r in controls["rows"]]
            # All coordinate paths must read the exact same uncompressed AO arrays.
            if any(len({tuple(sorted(x["shared_AO_sha256"].items())) for x in r["paths"]})!=1 for r in controls["rows"]+comparison["rows"]):
                raise ValueError("AO inputs differ across paths")
            delta=max(abs(x["total_energy_hartree"]-r["original"]["energy"]) if x["accepted"] else float("inf") for x,r in zip(records,controls["rows"]))
            full=all(x["singlet_dimension"]==x["basis_size"]*(x["basis_size"]+1)//2 and min(x["C_singular_values"])>0 for x in records)
            qualified=all(x["accepted"] for x in records) and delta<=spec["comparison_energy_abs_max_hartree"] and full
            count=sum(x["accepted"] for r in comparison["rows"] for x in r["paths"] if x["path"]==path and x["backend"]==backend)
            ranking.append(dict(path=path,backend=backend,qualified=qualified,max_control_energy_difference_hartree=delta,
                                original_refusal_points_accepted=count,full_dimension=full))
    options=[x for x in ranking if x["qualified"]]
    if not options:
        return dict(status="NO_QUALIFIED_PATH",ranking=ranking)
    priority={"cholesky":0,"generalized_h":1,"symmetric":2}
    choice=min(options,key=lambda x:(-x["original_refusal_points_accepted"],priority[x["path"]],spec["transform_backends"].index(x["backend"])))
    return dict(status="SAME_FINITE_BASIS_ANALYTIC_AND_CONTROL_NUMERICAL_EVIDENCE_NOT_CERTIFIED",**choice,ranking=ranking,
                qualification_scope="all 10 accepted controls; other geometries retain guards; no universal equivalence certificate",
                reference_used=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    args=p.parse_args()
    root=Path(args.root)
    paths={"controls":root/"controls/results.json","comparison":root/"compare/results.json","protocol":Path(__file__).with_name("protocol.json")}
    result=select(*[json.loads(paths[x].read_text()) for x in ("controls","comparison","protocol")])
    result["input_sha256"]={k:hashlib.sha256(x.read_bytes()).hexdigest() for k,x in paths.items()}
    with (root/"selection.json").open("x",encoding="utf-8") as f:
        f.write(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
