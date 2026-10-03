"""Immutable-record packaging and localized trace reduction; no solver."""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def dump(path,obj):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(obj,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')


def reduce_trace(h,g,bra,ket,counter):
    # For this single excitation from a closed ket, there are three changed
    # absorbed-K entries. Use the sealed observed state, without reselection.
    shared=ket[0]
    other=next(x for x in bra if x!=shared)
    forward=[];reverse=[]
    for t in range(len(h)):
        forward.append(Fraction(float(g[other,t,t,shared])))
        reverse.append(Fraction(float(g[shared,t,t,other])))
    tf=sum(forward,Fraction());tr=sum(reverse,Fraction())
    # f=(h-T/2)/2: replacing an upper f by its lower representative
    # changes f by (T_upper-T_lower)/4.
    df=(tf-tr)/4
    with localcontext() as ctx:
        ctx.prec=100
        expected=2*Decimal(2).sqrt()*Decimal(df.numerator)/Decimal(df.denominator)
    before={tuple(x['indices']):x for x in counter['unpacked_terms']}
    after={tuple(x['indices']):x for x in counter['packed_terms']}
    changed=[];weighted=Fraction()
    for idx,row in before.items():
        delta=Fraction(after[idx]['input'])-Fraction(row['input'])
        if delta:
            weighted+=row['integer_coefficient']*delta
            changed.append(dict(indices=list(idx),coefficient=row['integer_coefficient'],
                         before=row['input'],after=after[idx]['input'],difference=float(delta),
                         exact_dyadic_difference=str(delta)))
    with localcontext() as ctx:
        ctx.prec=100
        exact_K=Decimal(weighted.numerator)/Decimal(weighted.denominator)/Decimal(2).sqrt()
    return dict(bra=bra,ket=ket,trace_indices=[other,shared],
                T_forward_exact=str(tf),T_reverse_exact=str(tr),T_forward=float(tf),T_reverse=float(tr),
                trace_difference_exact=str(tf-tr),trace_difference=float(tf-tr),f_representative_change_exact=str(df),
                predicted_action_change_from_trace=str(expected),
                action_change_from_all_stored_K_differences=str(exact_K),
                observed_action_change=counter['prior_action']-counter['independent_SC'],
                prediction_minus_observed=float(expected)-(counter['prior_action']-counter['independent_SC']),
                changed_K_entries=changed,dominant_changed_K_entries=[x for x in changed if abs(x['difference'])>1e-10],
                trace_terms=[dict(t=t,forward=float(a),reverse=float(b),exact_pair_difference=str(a-b)) for t,(a,b) in enumerate(zip(forward,reverse))],
                diagnosis='Non-pair-symmetric raw MO yields asymmetric contraction T and f. Fourfold packing reuses lower f in distinct upper slots after absorption; three dominant K changes reproduce the action mismatch.',
                normalization_or_sign_fault_supported=False,index_mapping_fault_supported=False,
                raw_MO_or_H_repair_applied=False,scope='This single physical action component and synthetic two-orbital algebra. No all-entry or energy error bound.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    root=Path(args.run);out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    source=Path(__file__)
    hpath=root/'h.npy';gpath=root/'g.npy';counterpath=root/'counterexample.json'
    sealed=json.loads((root/'execution_seal.json').read_text(encoding='utf-8'))
    prep=json.loads((root/'preparation_seal.json').read_text(encoding='utf-8'))
    dump(out/'postprocess_seal.json',dict(source_sha256=sha(source),input_sha256={str(x):sha(x) for x in (hpath,gpath,counterpath,root/'summary.json')},
          protocol='Localized exact dyadic trace sum and fixed observed-state K loss; no new physical entry selection or eigensolver'))
    counter=json.loads(counterpath.read_text(encoding='utf-8'));started=time.perf_counter()
    reduction=reduce_trace(np.load(hpath,mmap_mode='r'),np.load(gpath,mmap_mode='r'),counter['bra'],counter['ket'],counter)
    reduction['seconds']=time.perf_counter()-started
    dump(out/'counterexample_reduction.json',reduction)
    for path in root.glob('*.json'):
        shutil.copyfile(path,out/path.name)
    for path in root.glob('matvec_*.npz'):
        shutil.copyfile(path,out/path.name)
    for name in ('protocol.json','DERIVATION.md'):
        shutil.copyfile(Path('electronic_pilot/ci_layer_audit_v0')/name,out/name)
    shutil.copytree(root.parent/'preflight',out/'preflight')
    shutil.copyfile(root.parent/'physical_v0.log',out/'physical_v0.log')
    stageA=json.loads((root/'matrix_elements.json').read_text(encoding='utf-8'))
    stageB=json.loads((root/'submatrix.json').read_text(encoding='utf-8'))
    mapping=json.loads((root/'basis_mapping.json').read_text(encoding='utf-8'))
    summary=json.loads((root/'summary.json').read_text(encoding='utf-8'))
    dump(out/'report_metrics.json',dict(basis={key:mapping[key] for key in ('status','dimensions','unique','duplicates','missing','extra','unmappable')},
          matrix_elements=[{key:row[key] for key in ('class','bra','ket','existing','independent','absolute_difference','relative_difference')} for row in stageA['rows']],
          matrix_elements_max=stageA['max_absolute_difference'],submatrix={key:stageB[key] for key in ('size','max_absolute_difference','mismatch_count','largest_pair','existing_symmetry_residual','independent_symmetry_residual')},
          protected_source_count=len(prep['protected_sha256']),prior_raw_count=len(prep['old_raw_sha256']),
          sealed_new_source_count=len(prep['source_sha256']),MO_input=sealed['MO_input'],
          preparation_materialization_seconds=sealed['preparation_seconds'],whole_run=summary,
          peak_rss_MiB=summary['peak_rss_bytes']/2**20,precision_scope='Saved binary64 MO; exact selected coefficients and trace sums do not upgrade AO accuracy',
          raw_MO_not_committed=True,raw_MO_paths=[str(hpath.resolve()),str(gpath.resolve())]))
    dump(out/'artifact_manifest.json',dict(files={str(x.relative_to(out)):sha(x) for x in out.rglob('*') if x.is_file()},
           reproducibility='Compact records include source/input hashes, full basis map, raw selected terms and action outputs. Large h/g arrays remain in the local run; reconstruct from original sealed AO/C by the unchanged transform.',
           original_physical_run_not_repeated=True))
    print(json.dumps(dict(predicted_change=reduction['predicted_action_change_from_trace'],prediction_minus_observed=reduction['prediction_minus_observed'],
          dominant_K_entries=len(reduction['dominant_changed_K_entries']),protected_sources=len(prep['protected_sha256']),prior_raw=len(prep['old_raw_sha256']),
          summary=summary),indent=2))


if __name__=='__main__':
    main()
