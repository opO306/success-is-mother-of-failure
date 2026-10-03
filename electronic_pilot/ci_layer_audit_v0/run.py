"""Sealed sequential CI micro-audit, no energy/reference/eigensolver calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np
from . import fermion, baseline


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, obj):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def verify(mapping):
    bad = [p for p, expected in mapping.items() if not Path(p).is_file() or sha(p) != expected]
    if bad:
        raise ValueError('SEALED BYTE DRIFT: '+repr(bad))


def basis_check(a, b, independent):
    def keyed(rows):
        pairs = [tuple(x['pair']) for x in rows]
        return pairs, {pair: row for pair, row in zip(pairs, rows)}
    ap, am = keyed(a); bp, bm = keyed(b); cp, cm = keyed(independent)
    universe = set(cm)
    duplicates = {name: len(pairs)-len(set(pairs)) for name, pairs in [('A',ap),('prior',bp),('independent',cp)]}
    missing = {name: sorted(universe-set(mapping)) for name, mapping in [('A',am),('prior',bm)]}
    extras = {name: sorted(set(mapping)-universe) for name, mapping in [('A',am),('prior',bm)]}
    unmappable = []
    rows = []
    for pair in sorted(universe):
        for name, mapping in [('A',am),('prior',bm)]:
            if pair not in mapping:
                continue
            if any(mapping[pair][key] != cm[pair][key] for key in ('occupation','S','Ms','normalization')):
                unmappable.append(dict(path=name,pair=list(pair)))
        if pair in am and pair in bm:
            rows.append(dict(**cm[pair], A_index=am[pair]['index'], prior_lower_index=bm[pair]['index']))
    spin_failures = [list(pair) for pair in universe if not fermion.spin_zero(pair)]
    okay = not any(duplicates.values()) and not any(missing.values()) and not any(extras.values()) and not unmappable and not spin_failures
    return dict(status='MATCH' if okay else 'STOP', dimensions={'A':len(a),'prior':len(b),'independent':len(independent)},
                unique={'A':len(am),'prior':len(bm),'independent':len(cm)}, duplicates=duplicates,
                missing=missing, extra=extras, unmappable=unmappable, spin_raise_failures=spin_failures,
                normalization_check='closed determinant norm=1; open two disjoint determinants with coefficients +/-1/sqrt2; exact S+ cancellation', rows=rows)


def comparison(a, b, limit):
    delta = abs(a-b)
    return dict(existing=a, independent=b, absolute_difference=delta,
                relative_difference=None if max(abs(a),abs(b)) == 0 else delta/max(abs(a),abs(b)), mismatch=delta>limit)


def prepare(target, evidence, old_raw_roots):
    spec = json.loads(Path(__file__).with_name('protocol.json').read_text())
    def git(*args):
        return subprocess.check_output(['git',*args], text=True).strip()
    if git('rev-parse','HEAD') != spec['base_commit'] or git('branch','--show-current') != spec['branch']:
        raise ValueError('Requested exact base/branch absent; no substitute')
    paths = git('ls-tree','-r','--name-only','HEAD','electronic_pilot','tests/test_h2_static_pilot.py',
                'tests/test_h2_numerical_cause.py','tests/test_h2_ao_micro_v0.py','tests/test_h2_qz44_sealed_v1.py',
                'tests/test_h2_qz44_failure_diagnostic.py','tests/test_h2_failure_cause_v0.py',
                'docs/active/h2_static_pilot_v2','docs/active/h2_numerical_cause_v1','docs/active/h2_ao_micro_v0',
                'docs/active/h2_qz44_sealed_v1','docs/active/h2_failure_cause_v0').splitlines()
    protected = {p:sha(p) for p in paths}
    for p, digest in protected.items():
        expected = hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+p])).hexdigest()
        if digest != expected:
            raise ValueError('Base source byte drift '+p)
    raw = {str(p):sha(p) for root in old_raw_roots for p in Path(root).rglob('*') if p.is_file()}
    sources = {str(p):sha(p) for p in Path(__file__).parent.glob('*') if p.is_file()}
    sources['tests/test_h2_ci_layer_audit_v0.py'] = sha('tests/test_h2_ci_layer_audit_v0.py')
    env = {k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}
    if set(env.values()) != {'1'}:
        raise ValueError('Thread policy drift')
    numeric = json.loads(Path('electronic_pilot/ao_micro_v0/protocol.json').read_text())
    if spec['comparison_abs_max'] != numeric['guards']['H_asym_max']:
        raise ValueError('Predeclared comparison criterion differs')
    record_path = Path(evidence)/'R_0.4.json'; ao_path = record_path.with_suffix('.npz')
    record = json.loads(record_path.read_text())
    if sha(ao_path) != record['artifact_sha256']:
        raise ValueError('Original R04 artifact drift')
    # Source/protocol/selection seal exists before materializing MO, before any
    # CI matrix element or action evaluation.
    save(target/'preparation_seal.json', dict(spec=spec, protected_sha256=protected, old_raw_sha256=raw,
         source_sha256=sources, input_sha256={str(record_path):sha(record_path),str(ao_path):sha(ao_path)},
         head=git('rev-parse','HEAD'),branch=git('branch','--show-current'),
         origin_master=git('rev-parse','origin/master'),origin_h2_micro=git('rev-parse','origin/codex/h2-ao-micro-v0'),
         dirty=git('status','--short'),recent_commits=git('log','-6','--oneline'),thread_environment=env,
         old_guards=numeric['guards'],old_canonical_rule=numeric['canonical_rule']))
    started = time.perf_counter()
    from pyscf import ao2mo, lib, fci
    from electronic_pilot.ao_micro_v0.reuse import one_electron_unique
    lib.num_threads(1)
    with np.load(ao_path) as ao:
        s,h,g8,c = (ao[key] for key in ('s','h','eri_s8','c'))
    if s.shape != (60,60) or c.shape != (60,60):
        raise ValueError('AO60 required')
    hm = one_electron_unique(h,c)
    gm = ao2mo.restore(1,ao2mo.incore.full(g8,c,compact=True),60)
    pair = float(abs(gm-gm.transpose(2,3,0,1)).max())
    if pair != record['paths'][0]['transformed_ERI_symmetry']['pair_swap_max']:
        raise ValueError('Frozen compact transform pair residual not reproduced')
    np.save(target/'h.npy',hm); np.save(target/'g.npy',gm)
    import inspect, pyscf, scipy
    save(target/'runtime_source.json',dict(pyscf_version=pyscf.__version__,numpy_version=np.__version__,scipy_version=scipy.__version__,
         python=sys.version, direct_spin1_sha256=sha(fci.direct_spin1.__file__),
         libfci_sha256=sha(Path(pyscf.__file__).parent/'lib/libfci.so'),
         absorb_h1e=inspect.getsource(fci.direct_spin1.absorb_h1e),contract_2e=inspect.getsource(fci.direct_spin1.contract_2e)))
    bound = protected|raw|sources|{str(record_path):sha(record_path),str(ao_path):sha(ao_path),
          str(target/'h.npy'):sha(target/'h.npy'),str(target/'g.npy'):sha(target/'g.npy')}
    save(target/'execution_seal.json',dict(bound_sha256=bound,preparation_seal_sha256=sha(target/'preparation_seal.json'),
         runtime_source_sha256=sha(target/'runtime_source.json'),MO_input=dict(h_shape=list(hm.shape),g_shape=list(gm.shape),
         h_array_sha256=hashlib.sha256(hm.tobytes()).hexdigest(),g_array_sha256=hashlib.sha256(gm.tobytes()).hexdigest(),
         pair_interchange=pair,within_first_pair=float(abs(gm-gm.transpose(1,0,2,3)).max()),within_second_pair=float(abs(gm-gm.transpose(0,1,3,2)).max()),
         mode='unchanged frozen C and compact transform; saved once before CI audit'),preparation_seconds=time.perf_counter()-started))
    return spec,bound


def audit(target,spec,bound):
    started=time.perf_counter(); verify(bound)
    h=np.load(target/'h.npy',mmap_mode='r');g=np.load(target/'g.npy',mmap_mode='r')
    limit=spec['comparison_abs_max']; n=len(h)
    mapping=basis_check(baseline.catalog(n),baseline.catalog(n,True),fermion.state_catalog(n))
    save(target/'basis_mapping.json',mapping)
    if mapping['status']!='MATCH':
        return dict(classification='BASIS_MAPPING_MISMATCH_CONFIRMED',failure_stage='basis_mapping')
    states=[tuple(x['pair']) for x in mapping['rows']]
    selected=[(tuple(x['bra']),tuple(x['ket'])) for x in spec['stage_A']]
    existing=baseline.entries(h,g,selected); prior=baseline.entries(h,g,selected,True)
    rows=[]
    for selection,a,pa in zip(spec['stage_A'],existing,prior):
        detail=fermion.breakdown(h,g,selection['bra'],selection['ket'])
        row=dict(**selection,**comparison(a,detail['value'],limit),prior_direct_pair=pa,
                 prior_difference=abs(pa-detail['value']),breakdown=detail)
        rows.append(row)
        if row['mismatch'] or row['prior_difference']>limit:
            save(target/'matrix_elements.json',dict(status='STOP',rows=rows,first_mismatch=row))
            save(target/'counterexample.json',row)
            return dict(classification='CI_CONSTRUCTION_MISMATCH_CONFIRMED',failure_stage='matrix_element')
    save(target/'matrix_elements.json',dict(status='AGREE',rows=rows,max_absolute_difference=max(x['absolute_difference'] for x in rows)))
    subset=[tuple(x) for x in spec['stage_B_states']]
    requests=[(bra,ket) for bra in subset for ket in subset]
    aa=np.array(baseline.entries(h,g,requests)).reshape((len(subset),)*2)
    bb=np.array([fermion.breakdown(h,g,bra,ket)['value'] for bra,ket in requests]).reshape(aa.shape)
    delta=abs(aa-bb); where=tuple(map(int,np.unravel_index(delta.argmax(),delta.shape)))
    sub=dict(status='AGREE' if float(delta.max())<=limit else 'STOP',size=len(subset),canonical_states=subset,
             existing=aa.tolist(),independent=bb.tolist(),max_absolute_difference=float(delta.max()),
             mismatch_count=int((delta>limit).sum()),largest_pair=[subset[where[0]],subset[where[1]]],
             existing_symmetry_residual=float(abs(aa-aa.T).max()),independent_symmetry_residual=float(abs(bb-bb.T).max()))
    save(target/'submatrix.json',sub)
    if sub['status']=='STOP':
        save(target/'counterexample.json',sub)
        return dict(classification='CI_CONSTRUCTION_MISMATCH_CONFIRMED',failure_stage='submatrix')
    verify(bound); op=baseline.PriorAction(h,g);columns={};vectors=[]
    for vector in spec['stage_C_vectors']:
        entries=[(tuple(x['state']),x['weight']) for x in vector['entries']]
        start=time.perf_counter()
        for ket,_ in entries:
            if ket not in columns:
                columns[ket]=(baseline.column(h,g,ket,states),np.array([fermion.value(h,g,bra,ket) for bra in states]))
        a=sum(weight*columns[ket][0] for ket,weight in entries)
        b=sum(weight*columns[ket][1] for ket,weight in entries)
        old=op(entries,states)
        d=abs(a-b); action=abs(old-b)
        index=int(action.argmax()); first=next((k for k,x in enumerate(action) if x>limit),None)
        row=dict(name=vector['name'],entries=vector['entries'],output_dimension=len(states),
                 A_vs_independent_max=float(d.max()),A_vs_independent_L2=float(np.linalg.norm(a-b)),
                 prior_action_vs_independent_max=float(action.max()),prior_action_vs_independent_L2=float(np.linalg.norm(old-b)),
                 mismatch_count=int((action>limit).sum()),largest_output_state=states[index],
                 first_mismatch_state=None if first is None else states[first],seconds=time.perf_counter()-start,
                 status='AGREE' if max(float(d.max()),float(action.max()))<=limit else 'STOP')
        vectors.append(row)
        np.savez_compressed(target/('matvec_'+vector['name']+'.npz'),existing_direct_pair=a,independent_SC=b,prior_determinant_action=old)
        if row['status']=='STOP':
            save(target/'matvec.json',dict(status='STOP',vectors=vectors,not_executed=[x['name'] for x in spec['stage_C_vectors'][len(vectors):]],reason='first mismatch; no further campaign'))
            # The first predeclared vector is a single e_i, hence already a
            # single-column counterexample. Preserve both first and largest.
            if len(entries)!=1:
                raise ValueError('Protocol first-vector assumption violated')
            ket=entries[0][0]; bra=states[index]
            detail=fermion.breakdown(h,g,bra,ket)
            kbefore,trace,f=baseline.uncompressed_absorption(h,g)
            before,bterms=fermion.e_product_element(kbefore,bra,ket)
            packed,pterms=fermion.e_product_element(op.k,bra,ket)
            first_detail=dict(bra=states[first],ket=ket,existing_direct_pair=float(a[first]),
                              independent_SC=float(b[first]),prior_action=float(old[first]))
            counter=dict(bra=bra,ket=ket,existing_direct_pair=float(a[index]),independent_SC=detail['value'],
                         prior_action=float(old[index]),absolute_difference=float(action[index]),first_lexicographic_counterexample=first_detail,
                         independent_breakdown=detail,spin_free_unpacked_value=before,spin_free_packed_value=packed,
                         spin_free_unpacked_minus_raw_SC=before-detail['value'],spin_free_packed_minus_PySCF=packed-float(old[index]),
                         unpacked_terms=bterms,packed_terms=pterms,
                         trace_asymmetry=float(abs(trace-trace.T).max()),absorbed_f_asymmetry=float(abs(f-f.T).max()),
                         f_bra_orbital_ket_orbital=[[float(f[i,j]),float(f[j,i])] for i in sorted(set(bra)) for j in sorted(set(ket))],
                         no_repair_applied=True)
            save(target/'counterexample.json',counter)
            return dict(classification='CI_CONSTRUCTION_MISMATCH_CONFIRMED',failure_stage='prior_determinant_action',
                        A_vs_independent='CI_LAYER_EQUIVALENCE_SUPPORTED on selected elements/submatrix and one full column',
                        seconds=time.perf_counter()-started)
    save(target/'matvec.json',dict(status='AGREE',vectors=vectors))
    return dict(classification='CI_LAYER_EQUIVALENCE_SUPPORTED',failure_stage=None,seconds=time.perf_counter()-started,
                next_gate='same-matrix dense audit allowed; this micro-audit contains no eigensolver implementation')


def main():
    import resource  # Linux worker accounting; dependency-free helpers also run on Windows.
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--output',required=True)
    p.add_argument('--old-raw-root',action='append',default=[]);args=p.parse_args()
    target=Path(args.output);target.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
    try:
        spec,bound=prepare(target,Path(args.evidence),args.old_raw_root)
        result=audit(target,spec,bound)
        verify(bound)
        for name in ('matrix_elements','submatrix','matvec','counterexample'):
            if not (target/(name+'.json')).exists():
                save(target/(name+'.json'),dict(status='NOT_EXECUTED',reason=result['failure_stage']))
        save(target/'eigensolver.json',dict(status='NOT_EXECUTED',reason='CI/action mismatch; energy and Pachucki comparison prohibited',same_matrix_provided=False))
        save(target/'preservation.json',dict(all_bound_bytes_unchanged=True,bound_count=len(bound),
             old_gate_unchanged=True,old_results_unchanged=True,production_applied=False))
        result.update(R_bohr=.4,not_certified=True,designer_decision_required=True,valid_approaches=1,
             wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time(),
             peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
             peak_scope='whole process including Git hashing, MO materialization and diagnostic intermediate; not full CI solver')
        save(target/'summary.json',result)
        print(json.dumps(result,indent=2),flush=True)
    except Exception as exc:
        save(target/'failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),wall_seconds=time.perf_counter()-start))
        raise


if __name__=='__main__':
    main()
