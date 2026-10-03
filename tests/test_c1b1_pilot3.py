"""Independent REF endpoints catch exact scale, radius and final rounding errors."""
import copy
import importlib
from fractions import Fraction as Q
from pathlib import Path
import pytest
from a_numeric.profiles import FixedPoint,VMHalt
from a_reference import c1b1_two_atom as C,c1b1_fast_impulse as F
from experiments.verified_superoptimizer_c1b1 import integration_stages as I


def pilot():
    assert Path('a_reference/c1b1_pilot3_impulse.py').exists(),'isolated Pilot3 missing'
    return importlib.import_module('a_reference.c1b1_pilot3_impulse')

@pytest.mark.parametrize('raw,shift,values',[
    ((3,0,0),0,(Q(4),Q(0),Q(0))),
    ((3,0,0),-1,(Q(3),Q(0),Q(0))),
    ((True,0,0),0,(Q(1),Q(0),Q(0))),
    ((3,0,0),0,[Q(3),Q(0),Q(0)]),
])
def test_raw_packet_public_boundary_rejects_inconsistent_or_mutable_data(raw,shift,values):
    with pytest.raises(C.ContractViolation,match='raw relative packet'):
        pilot().RawRelative(raw,shift,values)


@pytest.mark.parametrize('M',[128,256,512,1024])
@pytest.mark.parametrize('R2',[Q(25,4),Q(100),Q(201,2)])
@pytest.mark.parametrize('ret',[False,True])
def test_A_same_fixed_M_REF_and_original_B_endpoints(M,R2,ret):
    p=pilot();radius=F._radius(R2,M)
    assert p.model_prepared(radius,M,ret)==F._model(R2,M,ret)==C._model(R2,M,ret)[1:]


@pytest.mark.parametrize('width,Fpos',[(8,0),(16,7),(96,48),(192,150)])
def test_B_raw_relative_exact_and_unrounded_beyond_stored_limit(width,Fpos):
    p=pilot();pos=FixedPoint(width,Fpos)
    a=C.Atom('Ar40',(pos.lo,0,pos.hi),(0,0,0));b=C.Atom('Ar40',(pos.hi,-1,pos.lo),(0,0,0))
    packet=p.relative_raw(pos,a,b)
    assert tuple(packet)==C.relative(pos,a,b)
    assert packet.raw==(pos.hi-pos.lo,-1,pos.lo-pos.hi)
    with pytest.raises((AttributeError,TypeError)):packet.shift=Fpos+1


@pytest.mark.parametrize('M',[128,256,512,1024,16384])
@pytest.mark.parametrize('shift',[0,48,150])
def test_C_raw_squared_radius_has_identical_integer_endpoints(M,shift):
    p=pilot()
    for raw in [(0,3<<shift,0),(3<<shift,-4<<shift,5<<shift),(1,-7,1<<shift)]:
        N=sum(v*v for v in raw);r2=sum((Q(v,1<<shift)**2 for v in raw),Q(0))
        assert Q(N,1<<(2*shift))==r2
        assert p.radius_raw(N,shift,M)==F._radius(r2,M)


@pytest.mark.parametrize('v',[0,1,-1,1<<51,-(1<<51)])
@pytest.mark.parametrize('dt',[Q(20),Q(7,11),Q(-9,13)])
def test_D_final_interval_cross_products_equal_REF(v,dt):
    p=pilot();M=128;shift=48;g=(-123456789,987654321)
    lo,hi,d=p.component_interval(g,v,shift,dt,M)
    ends=sorted([Q(g[0],1<<M)*Q(v,1<<shift)*dt,Q(g[1],1<<M)*Q(v,1<<shift)*dt])
    assert lo*ends[0].denominator==ends[0].numerator*d
    assert hi*ends[1].denominator==ends[1].numerator*d


@pytest.mark.parametrize('n,d,want',[(5,2,2),(7,2,4),(-5,2,-2),(-7,2,-4),
    (499,200,2),(501,200,3),(-499,200,-2),(-501,200,-3),(0,1,0),(-128,1,-128),(127,1,127)])
def test_D_half_even_neighbors_and_exact_limits(n,d,want):
    p=pilot();mom=FixedPoint(8,0)
    assert p.decide_raw(mom,lambda M:(n,n,d))==want


def test_D_cancels_exact_binary_scale_before_bigint_multiply():
    p=pilot();mom=FixedPoint(96,80);n=(3<<100)+5;d=7<<176
    a,b=p.round_operands(mom,n,d)
    assert (a,b)==(n,7<<96)
    assert Q(a,b)==Q(n,d)*(1<<80)
    assert a.bit_length()< (n<<80).bit_length()


@pytest.mark.parametrize('lo,hi',[(128,129),(-130,-129),(-1000,1000)])
def test_D_same_overflow_or_cap_refusal(lo,hi,monkeypatch):
    p=pilot();mom=FixedPoint(8,0);monkeypatch.setattr(C,'MAX_PRECISION_BITS',256)
    assert I.capture(p.decide_raw,mom,lambda M:(lo,hi,1))==I.capture(C._decide,mom,lambda M:(Q(lo),Q(hi)))


@pytest.mark.parametrize('variant',['A','B','BC','BCD','ABCD'])
def test_isolated_runtime_keeps_every_step_and_original_code(variant):
    p=pilot();base=I.make_run(dict(e='9',b_frac='0'));run=copy.copy(base)
    from a_reference.c1b1_combined_arithmetic import CombinedRuntime
    a,b=CombinedRuntime(base),p.Runtime(run,variant)
    assert b.function.__code__ is C.step.__code__
    original=(C.step,C.impulse,C._model_R,F.impulse,F.step_fast)
    for _ in range(12):
        a.step();b.step();assert I.raw(base)==I.raw(run)
    assert original==(C.step,C.impulse,C._model_R,F.impulse,F.step_fast)


@pytest.mark.parametrize('kind',['domain','impulse_overflow','momentum_overflow','position_overflow'])
@pytest.mark.parametrize('variant',['A','B','BC','BCD','ABCD'])
def test_real_runtime_refusals_remain_atomic(kind,variant):
    p=pilot();a=I.make_run(dict(refusal=kind));b=copy.copy(a);before=dict(vars(b))
    assert I.capture(p.Runtime(b,variant).step)==I.capture(C.step,a)
    assert vars(b)==before


@pytest.mark.parametrize('field',['dt','pos','mom','species'])
def test_new_run_preparation_is_not_reused_after_binding_change(field):
    p=pilot();run=I.make_run(dict(e='9',b_frac='0'));ex=p.Runtime(run,'ABCD')
    if field=='dt':run.dt=Q(20)
    elif field=='pos':run.pos=FixedPoint(96,47)
    elif field=='mom':run.mom=FixedPoint(96,79)
    else:run.atoms=(C.Atom('other',run.atoms[0].r,run.atoms[0].p),run.atoms[1])
    before=dict(vars(run))
    with pytest.raises(C.ContractViolation,match='stale'):ex.step()
    assert vars(run)==before


def test_ABCD_whole_impulse_has_zero_actual_Fraction_creations_and_gcd(tmp_path):
    from experiments.verified_superoptimizer_c1b1.pilot3_census import Census
    p=pilot();pos=FixedPoint(96,48);mom=FixedPoint(96,80)
    a=C.Atom('Ar40',(0,0,0),(0,0,0));b=C.Atom('Ar40',(5<<48,-3<<48,2<<48),(0,0,0))
    packet=p.relative_raw(pos,a,b);dt=Q(20);expected=F.impulse(tuple(packet),dt,mom)
    c=Census(tmp_path/'values.sqlite')
    with c:got=p.impulse_raw(packet,dt,mom,prepared=True)
    assert got==expected
    counts=c.summary()['counts']
    assert counts['new']==counts['coprime']==counts['gcd']==0


@pytest.mark.parametrize('kind',['binary64','subclass','instance_override','retired_v1'])
def test_uncanonical_paths_retain_original_combined_fallback(kind):
    from a_reference.c1b1_combined_arithmetic import CombinedRuntime
    from a_numeric.profiles import Binary64Finite
    p=pilot();base=I.make_run(dict(e='9',b_frac='0'))
    if kind=='binary64':
        i,j=base.atoms;mom=Binary64Finite()
        base=C.new_run(base.pos,base.dt,C.exact(base.pos,i.r),C.exact(base.mom,i.p),
                       C.exact(base.pos,j.r),C.exact(base.mom,j.p),momentum_profile=mom,validated_only=False)
    elif kind=='subclass':
        class Other(FixedPoint):pass
        base.pos=Other(96,48)
    elif kind=='instance_override':
        base.pos=copy.copy(base.pos);base.pos.to_exact=lambda v:Q(v,1<<48)
    else:base.drift='v1'
    other=copy.copy(base);a,b=CombinedRuntime(base),p.Runtime(other)
    assert not b.pilot3_enabled and b.function.__globals__['impulse'] is F.impulse
    for _ in range(3):
        assert I.capture(a.step)==I.capture(b.step)
        assert I.raw(base)==I.raw(other)
