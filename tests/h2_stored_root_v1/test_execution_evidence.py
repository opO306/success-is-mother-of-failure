"""Post-acquisition proof/evidence recheck; does not alter the sealed checker."""
from fractions import Fraction as F
import json
from pathlib import Path
from electronic_pilot.h2_stored_root_v1 import checker as c
from electronic_pilot.h2_stored_root_v1.run import verify

def table():
    t=json.loads((c.DOC/'evidence/table.json').read_text())
    if t.get('compact_metadata'):
        rows=[]
        for r in t['cases']:
            assert c.sha(r['full_result_path'])==r['full_result_sha256']
            rows.append(json.loads(Path(r['full_result_path']).read_text()))
        t['cases']=rows
    return t

def test_all_five_and_aggregate_failure_preserved():
    t=table();assert [r['name'] for r in t['cases']]==list(c.CASES)
    full=all(r['root']['status']=='LOWEST_ROOT_ENCLOSED' for r in t['cases'])
    assert t['classification']==('H2SOLV_VENDOR_LOWEST_ROOT_SUPPORTED' if full else 'H2SOLV_LOWEST_ROOT_UNRESOLVED')
    assert t['STOP'] and t['NOT_CERTIFIED'] and t['NOT_PRODUCTION_APPROVED']

def test_protocol_and_original_bytes_unchanged():
    p=c.DOC/'evidence/protocol.json';proto=json.loads(p.read_text())
    assert c.sha(p)==json.loads((c.DOC/'evidence/protocol_seal.json').read_text())['sha256']
    assert verify(proto['protected_sha256'])==660
    verify(proto['implementation_sha256'])
    assert proto['precision_ladder']==[[d,b] for d,b in c.LADDER]

def test_indefinite_proof_replay_with_separate_fraction_action():
    count=0
    for r in table()['cases']:
        if r['SPD_status']!='STORED_S_NOT_SPD_EXACT_NEGATIVE_DIRECTION':continue
        count+=1
        n,h,s,meta=c.read_hs(c.OLD_RAW/'cases'/r['name']/'AUDIT/audit_HS.bin')
        x=[c.dyadic(int(m),e) for m,e in r['SPD']['final']['direction_pairs']]
        # Separate exact matrix action, without checker.qform's shared integer denominator.
        sx=[sum(s[max(i,j)*(max(i,j)+1)//2+min(i,j)]*x[j] for j in range(len(x))) for i in range(len(x))]
        q=sum(a*b for a,b in zip(x,sx))
        m,e=r['exact_direction']['q_pair']
        assert q==c.dyadic(int(m),e) and q<0
        assert r['root']['status']=='NOT_EXECUTED_S_PRECONDITION_FAILED'
        assert r['residual']['transformed_residual'] is None
    assert count>0

def test_certified_spd_and_bracket_proof_objects():
    for r in table()['cases']:
        if r['SPD_status']!='STORED_S_SPD_CERTIFIED':continue
        final=r['SPD']['final']; assert final['positive']==r['dimension'] and final['status']=='COMPLETE'
        assert all(c.dyadic(int(p['lower_pair'][0]),p['lower_pair'][1])>0 for p in final['pivots'])
        m,e=final['lambda_min_lower_pair'];assert c.dyadic(int(m),e)>0
        root=r['root']
        if root['status']!='LOWEST_ROOT_ENCLOSED':
            assert root['status']=='LOWEST_TRANSITION_FAILED'
            assert (root['inertia_low'],root['inertia_high'])!=(0,1)
            continue
        lo=c.dyadic(int(root['low_pair'][0]),root['low_pair'][1]);hi=c.dyadic(int(root['high_pair'][0]),root['high_pair'][1])
        er,v,prec=c.read_ev(c.OLD_RAW/'cases'/r['name']/'AUDIT/audit_EV.bin',r['dimension'])
        assert lo<er<hi and hi-lo<=F(1,1<<70)
        assert all(t['status']=='COMPLETE' and t['negative'] in (0,1) for t in root['trace'])
        assert all(r['eigenpair_consistency'][k] for k in ('RQ_inside','RQ_cauchy_consistent',
            'residual_spectral_interval_intersects','rho_interval_contained_in_lowest_bracket'))

def test_independent_wa1_only_qualified_where_spd():
    for r in table()['cases']:
        if r['initial_inertia'] is None:
            assert r['WA1_status']=='NOT_EXECUTED_S_PRECONDITION_FAILED'
        else:
            final=r['initial_inertia']['final'];assert final['status']=='COMPLETE'
            assert r['WA1_status']==('MATCH' if final['negative']==r['WA1'] else 'MISMATCH')

def test_actual_copy_mutants_all_five_and_no_threshold():
    for r in table()['cases']:
        m=r['fault_indefinite'];assert m['status']=='DETECTED' and m['exact_witness']['negative_witness']
        assert m['authoritative_unchanged'] and m['result']['final']['pivots'][0]['sign']==-1
        assert r['residual']['grade']=='MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD'
        assert r['residual']['decimal_digits']==240

def test_raw_input_identity_matches_seal():
    p=json.loads((c.DOC/'evidence/protocol.json').read_text())
    for inp in p['inputs']:
        for path,info in inp['files'].items():assert c.sha(path)==info['sha256'] and Path(path).stat().st_size==info['bytes']
