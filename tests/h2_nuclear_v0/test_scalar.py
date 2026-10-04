"""Analytic toy energy and deliberate false-success/rounding faults."""
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction as Q
import pytest
from electronic_pilot.h2_nuclear_v0.scalar import start,finish,geometry,force,individual,finite
from electronic_pilot.h2_nuclear_v0.check import check

MASS='1836.152673426'


def row(requested,old=False):
    g=geometry(requested)
    with localcontext() as ctx:
        ctx.prec=100
        e=float((D(requested)-D('1.4'))**2-D(1))
    r=dict(requested_R=requested,R_bohr=g['actual_serialized_R'],geometry=g,
        actual_stored_positions_bohr=g['positions_bohr'],total_energy_hartree=e,
        accepted=True,failure_stage=None,basis='cc-pV5Z',mode='AO_and_MO_integral_reuse',
        basis_size=110,singlet_dimension=6105,arithmetic='IEEE binary64',driver='evr',energy_convention='EBO=Ee+1/R',
        guards=dict(Smin_floor=1e-10,orth_l2_max=1e-10,H_asym_max=1e-10,eigen_l2_max=1e-9,norm_max=1e-10),
        Smin=1e-5,orthogonality_l2=1e-14,singlet_asymmetry=1e-15,eigen_residual_l2=1e-14,vector_norm_error=1e-16)
    if old:r['R_decimal']=requested
    return r


def fixture():
    old=[row(x,True) for x in ('1.4','1.5','1.6')]
    initial=start(*old,MASS)
    new=[row(initial['requested_geometries'][key]) for key in ('left','center','right')]
    result=finish(initial,*new)
    return old,new,result


def test_known_quadratic_force_and_verlet_mass_factor():
    old,new,result=fixture()
    initial=result['initial']
    f=Q.from_float(old[0]['total_energy_hartree'])-Q.from_float(old[2]['total_energy_hartree'])
    f*=5
    assert Q(initial['F0'])==f
    assert abs(Q(initial['requested_R1'])-(Q(3,2)+f/Q(MASS)))<Q(1,10**75)
    assert Q(result['P1'])<0 and Q(result['R1_requested'])<Q(3,2)
    assert result['energy_diagnostic_status']=='MEASURED' and result['energy_conservation_tolerance'] is None
    assert check(result,old,new,MASS)['status']=='SCALAR_AND_GEOMETRY_REPLAY_PASS'


def test_individual_canonical_momentum_and_kinetic_identity():
    states=individual('1.499','-0.03')
    assert states['p_A']=='0.03' and states['p_B']=='-0.03'
    assert D(states['z_A'])+D(states['z_B'])==0
    p=Q('-0.03');m=Q(MASS)
    assert ((-p)**2+p**2)/(2*m)==p**2/(2*(m/2))


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),'NaN','Infinity',True,{},None])
def test_nonfinite_or_invalid_scalar_refused(bad):
    with pytest.raises((ValueError,TypeError)): finite(bad)


@pytest.mark.parametrize('mass',['0','-1','NaN'])
def test_invalid_mass_refused(mass):
    with pytest.raises(ValueError):start(*[row(x,True) for x in ('1.4','1.5','1.6')],mass)


@pytest.mark.parametrize('index',[0,1,2])
def test_refused_new_point_not_substituted(index):
    old,new,result=fixture();new[index]['accepted']=False
    with pytest.raises(ValueError,match='REFUSED'):finish(result['initial'],*new)


def test_old_initial_direction_flip_stops_before_new_calls():
    old=[row(x,True) for x in ('1.4','1.5','1.6')]
    old[0]['total_energy_hartree'],old[2]['total_energy_hartree']=old[2]['total_energy_hartree'],old[0]['total_energy_hartree']
    with pytest.raises(ValueError,match='initial direction'): start(*old,MASS)


def test_final_force_flip_stops_before_step_supported():
    old,new,result=fixture()
    new[0]['total_energy_hartree'],new[2]['total_energy_hartree']=new[2]['total_energy_hartree'],new[0]['total_energy_hartree']
    with pytest.raises(ValueError,match='direction'):finish(result['initial'],*new)


@pytest.mark.parametrize('fault',['mu','P_half','P1','R1','p_A','COM','storedCOM','rounding','dt','h','steps','energy_tolerance','guard','mass','geometry'])
def test_independent_checker_rejects_false_success(fault):
    old,new,result=fixture()
    if fault=='mu':result['initial']['mu']=MASS
    elif fault=='P_half':result['initial']['P_half']='0'
    elif fault=='P1':result['P1']='0.1'
    elif fault=='R1':result['initial']['requested_R1']='1.6'
    elif fault=='p_A':result['nuclei']['p_A']=result['P1']
    elif fault=='COM':result['nuclei']['z_A']='0'
    elif fault=='storedCOM':new[1]['geometry']['positions_bohr'][0][2]=0
    elif fault=='rounding':new[1]['geometry']['R_rounding_delta']='0.1'
    elif fault=='dt':result['initial']['dt']='2'
    elif fault=='h':result['initial']['h']='0.01'
    elif fault=='steps':result['executed_steps']=2
    elif fault=='energy_tolerance':result['energy_conservation_tolerance']='1e-5'
    elif fault=='guard':new[1]['eigen_residual_l2']=2e-9
    elif fault=='mass':result['initial']['m_p']='1836'
    elif fault=='geometry':new[1]['requested_R']=new[0]['requested_R']
    with pytest.raises(ValueError):check(result,old,new,MASS)


def test_geometry_rounding_explicit_and_com_zero():
    g=geometry('1.499983984187650548204')
    assert Q(g['actual_R_exact_decimal'])==Q.from_float(g['actual_serialized_R'])
    assert g['R_rounding_delta']!='0'
    assert Q.from_float(g['positions_bohr'][0][2])+Q.from_float(g['positions_bohr'][1][2])==0
