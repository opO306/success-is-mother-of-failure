"""Actual production selection and arithmetic boundaries, with the original oracle."""
import copy
from fractions import Fraction as Q
import pytest
from a_numeric.profiles import FixedPoint
from a_reference import c1b1_runtime as R, c1b1_two_atom as C, c1b1_fast_impulse as F
from experiments.verified_superoptimizer_c1b1 import integration_stages as I


def test_combined_is_opt_in_and_bound_to_original_step_body():
    run=I.make_run(dict(e='9',b_frac='0'))
    ex=R.bind(run,mode='fast_combined')
    assert ex.function.__code__ is C.step.__code__
    assert ex.function.__globals__['impulse'] is F.impulse
    assert R.select()==(F.impulse,F.step_fast)
    assert R.select('reference')==(C.impulse,C.step)
    old=(C.step,C._drift,C._kick,C.impulse,F.step_fast)
    ref=copy.copy(run);base=copy.copy(run)
    for _ in range(20):
        R.step(ref,mode='reference');R.step(base);ex.step()
        assert I.raw(ref)==I.raw(base)==I.raw(run)
    assert old==(C.step,C._drift,C._kick,C.impulse,F.step_fast)


@pytest.mark.parametrize('change',['run','dt','pos','mom','species','mass','profile'])
def test_bound_combined_rejects_stale_constants_before_mutation(change,monkeypatch):
    run=I.make_run(dict(e='9',b_frac='0'))
    run.pos=copy.copy(run.pos);run.mom=copy.copy(run.mom)
    ex=R.bind(run,mode='fast_combined')
    if change=='run':ex.run=copy.copy(run)
    elif change=='dt':run.dt=Q(20)
    elif change=='pos':run.pos=FixedPoint(96,48)
    elif change=='mom':run.mom=FixedPoint(96,80)
    elif change=='species':run.atoms=(C.Atom('other',run.atoms[0].r,run.atoms[0].p),run.atoms[1])
    elif change=='mass':monkeypatch.setitem(C.SPECIES_MASS,'Ar40',Q(1))
    else:run.pos.frac_bits=47
    before=dict(vars(ex.run))
    with pytest.raises(C.ContractViolation,match='stale'):ex.step()
    assert vars(ex.run)==before


@pytest.mark.parametrize('p,J',[(0,0),(0,1),(0,-1),(127,0),(-128,0),
    (126,1),(127,1),(-127,-1),(-128,-1),(0,-128),(-128,127),(127,-128)])
def test_production_kick_limits_match_fraction(p,J):
    from a_reference import c1b1_combined_arithmetic as A
    mom=FixedPoint(8,4)
    atoms=(C.Atom('Ar40',(0,0,0),(p,0,0)),C.Atom('Ar40',(48,0,0),(p,0,0)))
    assert I.capture(A.kick,mom,atoms,(J,0,0))==I.capture(C._kick,mom,atoms,(J,0,0))


def test_production_round_displacement_keeps_exact_endpoint():
    from a_reference import c1b1_combined_arithmetic as A
    pos=FixedPoint(8,0);mom=FixedPoint(16,0)
    atom=C.Atom('Ar40',(1,0,0),(1,0,0));dt=C.AR40_MASS_ME/2
    k=A.DriftConversionContract.build(pos,mom,dt,C.AR40_MASS_ME)
    assert A.drift(k,pos,mom,atom,dt)==C._drift(pos,mom,atom,dt)
    moved,endpoint=A.drift(k,pos,mom,atom,dt)
    assert moved.r==(1,0,0) and endpoint==(Q(3,2),Q(0),Q(0))


def test_single_call_combined_and_bound_combined_match():
    run=I.make_run(dict(e='9',b_frac='0'));base=copy.copy(run)
    R.step(run,mode='fast_combined');R.bind(base,mode='fast_combined').step()
    assert I.raw(run)==I.raw(base)


@pytest.mark.parametrize('field',['displacement_raw','exact_endpoint','delta','result'])
def test_trace_checker_rejects_same_fault_in_all_three_modes(field,tmp_path):
    import gzip,json
    from experiments.verified_superoptimizer_c1b1 import combined_promotion as G
    spec=dict(id='unit',e='9',b_frac='0',cap=1)
    G.paired(spec,tmp_path/'trace.gz')
    with gzip.open(tmp_path/'trace.gz','rb') as f:rows=[json.loads(x) for x in f]
    obs=rows[1]['per_mode']
    for value in obs.values():
        name='segment_min_R2' if field in ('delta','result') else '_drift'
        ev=next(x for x in value['events'] if x['function']==name)
        if field=='displacement_raw':ev[field][0]+=1
        elif field=='result':ev[field]['raw']='0'
        else:ev[field][0]=str(Q(ev[field][0])+1)
    with pytest.raises(AssertionError):G.validate_observations(spec,obs)


def test_trace_checker_rejects_broken_def_use_chain(tmp_path):
    import gzip,json
    from experiments.verified_superoptimizer_c1b1 import combined_promotion as G
    spec=dict(id='unit',e='9',b_frac='0',cap=1)
    G.paired(spec,tmp_path/'trace.gz')
    with gzip.open(tmp_path/'trace.gz','rb') as f:rows=[json.loads(x) for x in f]
    o=rows[1]['per_mode']['reference']
    ev=next(x for x in o['events'] if x['function']=='_kick')
    ev['J'][0]+=1
    with pytest.raises(AssertionError):G.validate_transition(G.make_run(spec),rows[0]['initial'],o)


def test_exact_segment_refusal_despite_unchanged_rounded_storage(tmp_path):
    from experiments.verified_superoptimizer_c1b1 import combined_promotion as G
    spec=next(s for s in G.EXTRA if s['id']=='exact_segment_boundary')
    row=G.paired(spec,tmp_path/'trace.gz')
    assert row['end']=='PhysicsDomainExceeded' and row['steps']==0


def test_research_variants_are_not_runtime_modes():
    for mode in ('A','B','C','Combined','BASE'):
        with pytest.raises(ValueError):R.bind(object(),mode=mode)


def test_original_impulse_recheck_rejects_correlated_mode_fault(tmp_path):
    import gzip,json
    from experiments.verified_superoptimizer_c1b1 import combined_promotion as G
    spec=dict(id='unit',e='9',b_frac='0',cap=1)
    G.paired(spec,tmp_path/'trace.gz')
    with gzip.open(tmp_path/'trace.gz','rb') as f:rows=[json.loads(x) for x in f]
    obs=rows[1]['per_mode']
    for o in obs.values():next(x for x in o['events'] if x['function']=='impulse')['result']['raw'][0]+=1
    with pytest.raises(AssertionError,match='REF impulse'):G.validate_observations(spec,obs)


@pytest.mark.parametrize('fault',['FAIL','ERROR','SKIP','wrong_xfail','missing_item','short_baseline'])
def test_full_gate_rejects_semantic_failure_even_with_parseable_xml(fault,tmp_path):
    import json
    import xml.etree.ElementTree as ET
    from experiments.verified_superoptimizer_c1b1 import combined_promotion as G
    suite=ET.Element('testsuite');ids=[]
    for n in range(1 if fault=='short_baseline' else 3865):
        ids.append(['tests.fixture','case_'+str(n)])
        ET.SubElement(suite,'testcase',classname=ids[-1][0],name=ids[-1][1])
    ids.append(list(G.STRICT_XFAIL))
    x=ET.SubElement(suite,'testcase',classname=G.STRICT_XFAIL[0],name=G.STRICT_XFAIL[1])
    ET.SubElement(x,'skipped',type='pytest.xfail')
    if fault in ('FAIL','ERROR','SKIP'):
        ET.SubElement(suite[0],{'FAIL':'failure','ERROR':'error','SKIP':'skipped'}[fault])
    elif fault=='wrong_xfail':x.set('name','another_test')
    elif fault=='missing_item':suite.remove(suite[0])
    ET.ElementTree(suite).write(tmp_path/'full.xml')
    (tmp_path/'full_execution.json').write_text(json.dumps(dict(exit_code=0,wall_seconds=1)))
    with pytest.raises(AssertionError):G.validate_full(tmp_path,dict(full_identities=ids))


def test_campaign_can_parse_sealed_actual_cap_stress_without_changing_numeric_cap():
    import sys
    from experiments.verified_superoptimizer_c1b1 import combined_promotion as G
    previous=sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        G.configure_text_limit()
        original=G.read(G.E.HERE/'promotion_inputs.json')
        spec=next(x for x in original['impulses'] if 'precision_target_16384' in x['tags'])
        run=G.make_run(dict(spec,id='real_cap_precision_STOP',cap=1))
        assert run.dt==2*Q(spec['dt']) and C.MAX_PRECISION_BITS==16384
    finally:sys.set_int_max_str_digits(previous)
