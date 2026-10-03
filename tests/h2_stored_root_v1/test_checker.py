from fractions import Fraction as F
import json
from pathlib import Path
import struct
import pytest
from electronic_pilot.h2_stored_root_v1 import checker as c

def f(tmp_path,a,mode='INERTIA',bits=266):
    n=next(n for n in range(1,10) if n*(n+1)//2==len(a))
    path=tmp_path/'matrix.dyadic';c.matrix_file(path,n,a)
    return c.factor(path,n,bits,mode,tmp_path/'run')

@pytest.mark.parametrize('shift,expected',[(-4,0),(-3-F(1,1<<100),0),(-3+F(1,1<<100),1),
    (0,1),(2-F(1,1<<100),1),(2+F(1,1<<100),2),(4,3)])
def test_known_congruent_roots(tmp_path,shift,expected):
    # T=[[1,0,0],[2,1,0],[-1,3,1]], S=T T^T, H=T diag(-3,2,3)T^T.
    s=[1,2,5,-1,1,11];h=[-3,-6,-10,3,12,18]
    r=f(tmp_path,[F(a)-shift*F(b) for a,b in zip(h,s)])
    assert r['status']=='COMPLETE' and r['negative']==expected and r['positive']==3-expected

def test_spd_direction_and_global_margin(tmp_path):
    r=f(tmp_path,[1,1,2],'SPD')
    assert r['status']=='COMPLETE' and r['positive']==2
    assert c.dyadic(int(r['lambda_min_lower_pair'][0]),r['lambda_min_lower_pair'][1])>0
    assert not c.exact_direction([F(1),F(1),F(2)],r)['negative_witness']

def test_extreme_condition_ladder(tmp_path):
    a=[F(1),F(1),1+F(1,1<<600)]
    r=c.ladder(2,a,'SPD',tmp_path)
    assert [x['result']['status'] for x in r['attempts']]==['UNCERTAIN']*3+['COMPLETE']
    assert r['final']['positive']==2

def test_unresolved_maximum_precision(tmp_path):
    r=c.ladder(2,[F(1),F(1),1+F(1,1<<1000)],'SPD',tmp_path)
    assert len(r['attempts'])==4 and r['final']['status']=='UNCERTAIN'

def test_indefinite_exact_witness(tmp_path):
    a=list(map(F,[1,2,3]));r=f(tmp_path,a,'SPD')
    assert r['status']=='NOT_SPD' and c.exact_direction(a,r)['negative_witness']

@pytest.mark.parametrize('a',[[0,1,0],[1,1,1],[0,0,0]])
def test_zero_pivot_refuses(tmp_path,a):
    r=f(tmp_path,a)
    assert r['status']=='UNCERTAIN' and r['uncertain']==1

def test_exact_root_ambiguity(tmp_path):
    r=f(tmp_path,[0,0,1])
    assert r['status']=='UNCERTAIN'

def test_root_enclosure_and_hp_transformed_residual(tmp_path):
    h=list(map(F,[-3,0,8]));s=list(map(F,[1,0,4]));e=F(-3);v=[F(1),F(0)]
    r=c.root(2,h,s,e,tmp_path)
    assert r['status']=='LOWEST_ROOT_ENCLOSED' and r['E_inside']
    assert (r['inertia_low'],r['inertia_high'])==(0,1)
    m=c.measured(2,h,s,e,v,True)
    assert F(m['nS'])==1 and F(m['transformed_residual'])==0 and F(m['RQ_minus_E'])==0

def test_excited_return_rejected(tmp_path):
    r=c.root(2,list(map(F,[-3,0,2])),list(map(F,[1,0,1])),F(2),tmp_path)
    assert r['status']=='LOWEST_TRANSITION_FAILED' and (r['inertia_low'],r['inertia_high'])==(1,2)

def test_exact_native_probe():
    p=Path('docs/active/h2_internal_convergence_v0/evidence/probe/probe.bin')
    vals=c.records(p.read_bytes(),0,6)
    assert vals==[F(0),-F(3,2),1+F(1,1<<100),-F(1<<100),F(1,1<<300),F(25,8)]

@pytest.mark.parametrize('field,value',[(0,319),(1,0),(2,-(1<<63)+2),(8,1)])
def test_record_faults(field,value):
    words=[320,1,1,0,0,0,0,-(1<<63),0];words[field]=value
    with pytest.raises(ValueError):c.record(words)

def test_matrix_length_and_layout_faults(tmp_path):
    p=c.OLD_RAW/'cases'/c.CASES[1]/'AUDIT/audit_HS.bin';data=p.read_bytes()
    q=tmp_path/'corrupt.bin';q.write_bytes(data[:-1])
    with pytest.raises(ValueError): c.read_hs(q)
    d=bytearray(data);struct.pack_into('<q',d,24,4);q.write_bytes(d)
    with pytest.raises(ValueError):c.read_hs(q)

def test_real_test_copy_only(tmp_path):
    p=c.OLD_RAW/'cases'/c.CASES[1]/'AUDIT/audit_HS.bin';before=c.sha(p)
    n,h,s,meta=c.read_hs(p);s[0]=-abs(s[0])-1
    q=tmp_path/'mutant.dyadic';c.matrix_file(q,n,s)
    r=c.factor(q,n,266,'SPD',tmp_path/'mutant')
    assert r['status']=='NOT_SPD' and c.exact_direction(s,r)['negative_witness']
    assert c.sha(p)==before

@pytest.mark.parametrize('text',[
    'PIVOT 0 1 -1 0 1 0\nRESULT COMPLETE 0 1 0 1 1\nENV 4 6 266\nSECONDS 0\n',
    'PIVOT 0 1 1 0 2 0\nRESULT COMPLETE 1 0 0 1 1\nENV 4 6 266\nSECONDS 0\n',
    'PIVOT 0 0 0 0 0 0\nRESULT COMPLETE 0 0 1 0 1\nENV 4 6 266\nSECONDS 0\n',
    'PIVOT 0 1 1 0 2 0\nENV 4 6 266\nSECONDS 0\n'])
def test_false_backend_claims_rejected(text):
    with pytest.raises(ValueError):c.parse_backend(text,1)

def test_no_vendor_imports_or_execution():
    src=Path(c.__file__).read_text()
    for forbidden in ('h2_internal_convergence_v0 import','h2_vendor_resume_v2 import','import engine','invsg('):
        assert forbidden not in src

def test_qform_exact_cancellation():
    a=[F(1),F(1),1+F(1,1<<600)]
    assert c.qform(a,[F(-1),F(1)])==F(1,1<<600)

def test_log_actual_initial_shift():
    en,wa=c.read_observed(c.OLD_RAW/'cases'/c.CASES[1]/'AUDIT/audit_invsg.log')
    assert wa==1 and en!=F('-1.0573')

def test_stored_dimensions_and_precision():
    for name,nwant in zip(c.CASES,[416,228,416,416,792]):
        base=c.OLD_RAW/'cases'/name/'AUDIT';n,h,s,meta=c.read_hs(base/'audit_HS.bin')
        e,v,prec=c.read_ev(base/'audit_EV.bin',n)
        assert n==nwant and set(meta['precision_counts'])=={320} and set(prec)=={384}

def test_residual_metric_precondition():
    r=c.measured(2,list(map(F,[1,0,1])),list(map(F,[1,0,-1])),F(1),[F(1),F(0)],False)
    assert r['transformed_residual'] is None and r['transformed_status']=='NOT_EXECUTED_S_NOT_SPD'
