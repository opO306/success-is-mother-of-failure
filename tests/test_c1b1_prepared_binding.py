"""Deliberate stale faults must stop BEFORE the actual numerical step."""
import copy
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as Q
import pytest
from a_numeric import profiles as N
from a_reference import c1b1_runtime as R, c1b1_two_atom as C, ar2_lang2024 as L
from experiments.verified_superoptimizer_c1b1 import pilot3_campaign as P


@pytest.mark.parametrize('mode',['fast_combined','fast_pilot3'])
@pytest.mark.parametrize('fault',['dt','species','mass','pos_f','mom_f','other_run',
                                'physics','coefficient','fraction_inplace','rounding','round_function','profile_method',
                                'exp_constant','exp_alias','exp_code','dt_type','drift_function','drift_rounder','segment_function',
                                'coefficient_key_type','retardation_type','mass_slot_type','dt_slot_type','precision_type','exp_constant_slot_type'])
def test_stale_contract_refuses_before_numerical_entry(mode,fault,monkeypatch):
    run=P.make_run(dict(e='2',b_frac='1/2'));ex=R.bind(run,mode=mode)
    if fault=='dt':run.dt+=1
    elif fault=='dt_type':run.dt=int(run.dt)
    elif fault=='species':run.atoms=(replace(run.atoms[0],species='wrong'),run.atoms[1])
    elif fault=='mass':monkeypatch.setitem(C.SPECIES_MASS,'Ar40',C.SPECIES_MASS['Ar40']+1)
    elif fault=='pos_f':monkeypatch.setattr(run.pos,'frac_bits',run.pos.frac_bits+1)
    elif fault=='mom_f':monkeypatch.setattr(run.mom,'frac_bits',run.mom.frac_bits+1)
    elif fault=='other_run':ex.run=copy.copy(run)
    elif fault=='physics':monkeypatch.setattr(L,'parameter_fingerprint',lambda:'changed')
    elif fault=='coefficient':
        coefs=next(iter(L.COMPONENTS['BO'][0].values()))[1]
        k=next(iter(coefs));monkeypatch.setitem(coefs,k,coefs[k]+Q(1,100))
    elif fault=='fraction_inplace':
        q=next(iter(next(iter(L.COMPONENTS['BO'][0].values()))[1].values()))
        monkeypatch.setattr(q,'_numerator',q.numerator+1)
    elif fault=='coefficient_key_type':
        coefs=L.COMPONENTS['BO'][1][1];value=coefs[3]
        monkeypatch.delitem(coefs,3);monkeypatch.setitem(coefs,3.0,value)
        assert L.parameter_fingerprint()!=C.FROZEN_C1A_FINGERPRINT
    elif fault=='retardation_type':monkeypatch.setattr(L,'WORLD_RETARDATION',int(L.WORLD_RETARDATION))
    elif fault=='mass_slot_type':monkeypatch.setattr(C.SPECIES_MASS['Ar40'],'_denominator',float(C.SPECIES_MASS['Ar40'].denominator))
    elif fault=='dt_slot_type':monkeypatch.setattr(run.dt,'_numerator',float(run.dt.numerator))
    elif fault=='precision_type':monkeypatch.setattr(C,'START_PRECISION_BITS',float(C.START_PRECISION_BITS))
    elif fault=='rounding':monkeypatch.setattr(N,'PREPARED_ROUNDING_CONTRACT','wrong',raising=False)
    elif fault=='round_function':monkeypatch.setattr(N,'_div_round',lambda n,d:0)
    elif fault=='profile_method':monkeypatch.setattr(N.FixedPoint,'from_exact',lambda self,v:0)
    elif fault=='exp_constant':
        from a_reference import c1b1_impulse_primitives as IP
        monkeypatch.setattr(IP,'LN2_UPPER',Q(0))
    elif fault=='exp_constant_slot_type':
        from a_reference import c1b1_impulse_primitives as IP
        monkeypatch.setattr(IP.LN2_UPPER,'_denominator',float(IP.LN2_UPPER.denominator))
    elif fault=='exp_alias':
        from a_reference import c1b1_pilot3_impulse as X
        monkeypatch.setattr(X,'_exp_neg',lambda x,M:(0,0))
    elif fault=='exp_code':
        from a_reference import c1b1_impulse_primitives as IP
        monkeypatch.setattr(IP._exp_neg,'__code__',(lambda x,M:(0,0)).__code__)
    elif fault=='drift_function':
        from a_reference import c1b1_combined_arithmetic as K
        monkeypatch.setattr(K,'drift',lambda contract,pos,mom,atom,dt,rule='v2':(atom,C.exact(pos,atom.r)))
    elif fault=='drift_rounder':
        from a_reference import c1b1_combined_arithmetic as K
        monkeypatch.setattr(K.DriftConversionContract,'_rounded',lambda self,n,d:0)
    elif fault=='segment_function':monkeypatch.setattr(C,'segment_min_R2',lambda a,d:Q(100))
    before=dict(vars(ex.run));entered=[]
    ex.function=lambda r:entered.append(r)
    with pytest.raises(C.ContractViolation,match='stale|binding'):ex.step()
    assert not entered and vars(ex.run)==before


def test_binding_keys_are_immutable_and_expose_actual_dependencies():
    ex=R.bind(P.make_run(dict(e='2',b_frac='1/2')),mode='fast_pilot3')
    key=ex.binding_key
    assert key.dt==Q(40) and key.species==('Ar40','Ar40')
    assert key.position_profile==(96,48) and key.momentum_profile==(96,80)
    assert key.world.parameter_fingerprint==C.FROZEN_C1A_FINGERPRINT
    with pytest.raises(FrozenInstanceError):key.dt_ratio=(41,1)
    exposed=key.dt;exposed._numerator=41
    assert key.dt==Q(40)


def test_variant_change_refuses_before_calculation():
    ex=R.bind(P.make_run(dict(e='2',b_frac='1/2')),mode='fast_pilot3')
    ex.variant='BCD';entered=[];ex.function=lambda r:entered.append(r)
    with pytest.raises(C.ContractViolation,match='stale|binding'):ex.step()
    assert not entered


@pytest.mark.parametrize('mode',['fast_combined','fast_pilot3'])
@pytest.mark.parametrize('fault',['dt','positions','cache'])
def test_rebind_rejects_cached_impulse_from_old_inputs(mode,fault):
    run=P.make_run(dict(e='2',b_frac='1/2'));R.bind(run,mode=mode).step()
    if fault=='dt':run.dt+=1
    elif fault=='positions':run.atoms=(replace(run.atoms[0],r=tuple(v+1 for v in run.atoms[0].r)),run.atoms[1])
    else:run.J_cache=tuple(v+1 for v in run.J_cache)
    before=dict(vars(run))
    with pytest.raises(C.ContractViolation,match='cached impulse'):R.bind(run,mode=mode)
    assert vars(run)==before
    run.J_cache=None;ref=copy.copy(run)
    R.bind(run,mode=mode).step();C.step(ref)
    assert P.I.raw(run)==P.I.raw(ref)


def test_mutable_candidate_b_prepared_cache_refuses_before_entry(monkeypatch):
    from a_reference import c1b1_impulse_primitives as IP
    run=P.make_run(dict(e='2',b_frac='1/2'));ex=R.bind(run,mode='fast_combined')
    coefs=IP._const_cache(128)['BO'][0][0][2];k=next(iter(coefs))
    monkeypatch.setitem(coefs,k,coefs[k]+1);entered=[];ex.function=lambda r:entered.append(r)
    with pytest.raises(C.ContractViolation,match='cache|binding'):ex.step()
    assert not entered
