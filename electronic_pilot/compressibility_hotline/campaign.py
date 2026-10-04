"""Exclusive, source-sealed finite-corpus experiment and independent checks."""
import argparse
import copy
import gzip
import hashlib
import json
import platform
from pathlib import Path
import time
import numpy as np
import scipy
from . import tensor,baseline,checker


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p,value):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')


def rss():
    p=Path('/proc/self/smaps_rollup')
    if not p.exists():return None
    for line in p.read_text().splitlines():
        if line.startswith('Rss:'):return int(line.split()[1])*1024


def faults(receipt,p):
    results=[]
    for fault in p['mutations']:
        bad=copy.deepcopy(receipt)
        rows=bad['rows']
        def block(epoch,i):return next(r for r in rows[epoch]['blocks'] if r['block']==i)
        if fault=='cold_zero':block(0,2)['center']=0.
        elif fault=='hot_stops_others':rows[3]['blocks']=[block(3,0)]
        elif fault=='stale_bound':block(3,0)['radius']=0.
        elif fault=='omitted_coupling':
            # Electronic pair omission is tested separately below; additive control omits block 2.
            rows[0]['coverage_center']-=3.;rows[0]['coverage_radius']-=.0005
        elif fault=='wrong_threshold':block(2,0).update(status='FULL',reason='ERROR_BOUND')
        elif fault=='unsafe_hysteresis':block(3,0).update(status='COARSE_CERTIFIED',reason='HYSTERESIS')
        elif fault=='order_dependent':rows[-1]['result']+=1e-5
        elif fault=='permanent_starvation':
            for row in rows[3:]:row['blocks']=[r for r in row['blocks'] if r['block']!=1]
        try:checker.control(bad,p)
        except ValueError as e:results.append(dict(fault=fault,caught=True,reason=str(e)))
        else:results.append(dict(fault=fault,caught=False))
    return results


def main(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    root=Path.cwd(); module=Path(__file__).parent
    p=json.loads((module/'protocol.json').read_text())
    source={str(f.relative_to(root)):sha(f) for f in sorted(module.glob('*')) if f.is_file()}
    corpusroot=root/'docs/active/electronic_representation_survey_v1'
    sources={key:{'corpus':sha(corpusroot/(key+'_corpus.npz')),'contract':sha(corpusroot/(key+'_contract.json'))} for key in p['corpora']}
    save(out/'execution_seal.json',dict(protocol=p,source=source,corpus_sources=sources,
         python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
         scope='NUMERICAL_FINITE_CORPUS_NOT_FORMAL_OR_EXTERNAL_AUDIT'))
    data={}
    for key in p['corpora']:
        with np.load(corpusroot/(key+'_corpus.npz')) as z:data[key]={k:z[k].copy() for k in z.files}
        data[key].update(label=key,electrons=1 if key=='A' else 2)
    gs,meta=tensor.gauges(data['A'],data['B']);np.savez_compressed(out/'gauges.npz',**gs)
    save(out/'gauge_metadata.json',meta)
    samples=[rss()];tensor_summary={};arrays={};allrows={};schmidt_checks=[];phase=[]
    for key,d in data.items():
        rows,recons,costs=tensor.diagnostic(d,gs,data['B']['c'],p)
        allrows[key]=rows;arrays[key+'_recon']=recons
        # Independent density/observable reconstruction for every diagnostic.
        max_disagreement=0.; max_future_disagreement=0.;U=checker.unitary(d,p['future_delta_atomic'])
        originals={}
        for name,v0 in zip(p['states'],d['states']):
            for t in p['times_atomic']:originals[name,t]=tensor.evolve(v0,d,t)
        for row,v in zip(rows,recons):
            ref=originals[row['state'],row['time']]
            actual=checker.physical(ref,v,d)
            max_disagreement=max(max_disagreement,max(abs(actual[k]-row['metrics'][k]) for k in actual))
            future=checker.physical(U@ref,U@v,d)
            max_future_disagreement=max(max_future_disagreement,max(abs(future[k]-row['future_metrics'][k]) for k in future))
        assert max_disagreement<1e-9 and max_future_disagreement<1e-9
        # Direct fermionic occupation enumeration checks all states/gauges/cuts at t=0.
        for name,v in zip(p['states'],d['states']):
            for gauge,r in gs.items():
                x=tensor.coordinates(v,d,data['B']['c'],r)
                packed=x if d['electrons']==1 else tensor.pack(x)
                for cut in p['cuts_spatial_orbitals']:
                    direct=np.linalg.svd(checker.fock_matrix(packed,d['electrons'],cut),compute_uv=False)
                    claimed=tensor.decompose(x,cut)['singular']
                    err=float(np.max(abs(direct[:len(claimed)]-claimed)))
                    tail=float(np.linalg.norm(direct[len(claimed):]))
                    assert max(err,tail)<1e-10
                    schmidt_checks.append(dict(corpus=key,state=name,gauge=gauge,cut=cut,error=err,tail=tail))
        cases=[]
        for name in p['states']:
            for t in p['times_atomic']:
                for gauge in gs:
                    rr=[r for r in rows if r['state']==name and r['time']==t and r['gauge']==gauge]
                    requirements={}
                    for eps in p['diagnostic_state_error_levels']:
                        passing=[chi for chi in p['chi'] if all(r['metrics']['state_error_S']<=eps for r in rr if r['chi']==chi)]
                        requirements[str(eps)]=min(passing) if passing else None
                    strict=[chi for chi in p['chi'] if all(r['meets_inherited_tolerances'] for r in rr if r['chi']==chi)]
                    low=[chi for chi in strict if chi<=8 and all(r['factor_payload_bytes']+32<r['dense_payload_bytes'] for r in rr if r['chi']==chi)]
                    cases.append(dict(state=name,time=t,gauge=gauge,required_chi= requirements,
                                      inherited_chi=min(strict) if strict else None,small_payload_success=bool(low)))
        successes=sum(r['small_payload_success'] for r in cases)
        classification='PROMISING' if successes==len(cases) else ('CONDITIONAL' if successes else 'POOR')
        tensor_summary[key]=dict(classification=classification,cases=cases,rows=len(rows),
          inherited_small_payload_cases=successes,decomposition_cost=costs,
          max_independent_metric_disagreement=max_disagreement,
          max_independent_future_disagreement=max_future_disagreement,
          max_rank=max(r['rank_at_1e_12'] for r in rows),
          entropy_range=[min(r['entropy_bits'] for r in rows),max(r['entropy_bits'] for r in rows)])
        for gauge in gs:
            for cut in p['cuts_spatial_orbitals']:
                for chi in p['chi']:
                    idx=lambda name:next(i for i,r in enumerate(rows) if r['state']==name and r['time']==0 and r['gauge']==gauge and r['cut']==cut and r['chi']==chi)
                    vp,vm=recons[idx('plus')],recons[idx('minus')]
                    phase.append(dict(corpus=key,gauge=gauge,cut=cut,chi=chi,
                         initial_density_difference=float(np.max(abs(checker.density(vp,d)-checker.density(vm,d)))),
                         future_density_difference=float(np.max(abs(checker.density(U@vp,d)-checker.density(U@vm,d)))),
                         future_dipole_difference=float(max(abs(np.vdot(U@vp,op@(U@vp))-np.vdot(U@vm,op@(U@vm))) for op in d['dipoles'])),
                         projector_overlap=float(abs(np.vdot(vp,d['s']@vm))**2)))
        samples.append(rss())
    np.savez_compressed(out/'tensor_reconstructions.npz',**arrays)
    save(out/'tensor_rows.json',allrows);save(out/'tensor_phase_distinction.json',phase)
    save(out/'tensor_independent_schmidt_checks.json',schmidt_checks)
    print('Tensor diagnostics',sum(len(r) for r in allrows.values()),'rows',flush=True)
    baseline_summary=[]; receipts=[]; reference_cost=[]; pair_faults=[]
    for key,d in data.items():
        for name,v in zip(p['states'],d['states']):
            start=time.process_time();waves=np.array([tensor.evolve(v,d,t) for t in p['times_atomic']]);ev=time.process_time()-start
            start=time.process_time()
            for _ in range(p['cost_repeats']):
                for w in waves:
                    # Required REF energy, density, dipoles and norm.
                    tensor.metrics(w,w,d)
            reference_cost.append(dict(corpus=key,state=name,fixed_H_evolution_cpu=ev,
                 REF_observe_per_three_times_cpu=(time.process_time()-start)/p['cost_repeats']))
            for path in ['REF','BASELINE','HOTLINE']:
                order_outputs=[]
                for order in p['orders']:
                    receipt,outputs=baseline.run(waves,d,p,path,order)
                    checker.electronic(receipt,waves,d,p,outputs)
                    order_outputs.append(outputs)
                    receipt.update(corpus=key,state=name)
                    receipts.append(receipt)
                    baseline_summary.append(dict(corpus=key,state=name,path=path,order=order,cost=receipt['cost'],
                                                  canonical_bits_equal_REF=outputs.tobytes()==waves.tobytes()))
                    if key=='A' and name=='plus' and path=='HOTLINE' and order=='ascending':
                        bad=copy.deepcopy(receipt);bad['trace'][0]['accounts'][1].pop()
                        try:checker.electronic(bad,waves,d,p,outputs)
                        except ValueError as e:pair_faults.append(dict(fault='real_electronic_pair_omission',caught=True,reason=str(e)))
                        else:pair_faults.append(dict(fault='real_electronic_pair_omission',caught=False))
                assert all(v.tobytes()==order_outputs[0].tobytes() for v in order_outputs)
        samples.append(rss());print('Baseline checked',key,flush=True)
    with gzip.open(out/'baseline_receipts.json.gz','wt',encoding='utf-8') as f:json.dump(receipts,f)
    controls=[]
    for kind in ['hidden','thrash']:
        for order in p['orders']:
            receipt=baseline.controls(p,kind,order);checker.control(receipt,p);controls.append(receipt)
    safety_thresholds=dict(enter=.02,exit=.002,safety=.008)
    # Safety branch probe, explicitly noncanonical and not tuned to electronic results.
    safety=baseline.controls(p,'hidden',thresholds=safety_thresholds);checker.control(safety,p)
    controls.append(safety)
    mutation_results=faults(controls[0],p)+pair_faults
    assert all(r['caught'] for r in mutation_results)
    save(out/'controls_and_mutations.json',dict(controls=controls,mutations=mutation_results,
         safety_probe_scope='BRANCH_TEST_ONLY / additional thresholds declared in source execution seal'))
    save(out/'results.json',dict(tensor=tensor_summary,baseline=baseline_summary,reference_cost=reference_cost,
         mutations=mutation_results,observed_RSS_samples_bytes=samples,
         observed_peak_RSS_bytes=max(x for x in samples if x is not None) if any(x is not None for x in samples) else None,
         RAM_scope='boundary observations of combined campaign; no per-path absolute peak or production scaling claim',
         monitoring_note='monitor_self excludes full-coordinate radius acquisition; baseline conversion includes it; enclosure is separately charged',
         certificate_scope='exact Fraction coefficient L1 enclosure; quadratic floating error model bound, no interval library or formal certification',
         numerical_cost_repeats=p['cost_repeats'],scope=p['scope']))
    save(out/'closure.json',dict(files={f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file()},
         sources_unchanged=all(sha(root/k)==v for k,v in source.items())))
    print('Completed separate axes; no push',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    main(parser.parse_args().output)
