"""Execute incorrect implementations, rather than fake PASS/FAIL labels."""
from fractions import Fraction as Q
from pathlib import Path
from types import FunctionType
import importlib
import pytest
from a_numeric.profiles import FixedPoint
from a_reference import c1b1_pilot3_impulse as P,c1b1_two_atom as C


def checker():
    assert Path('experiments/verified_superoptimizer_c1b1/pilot3_checker.py').exists(),'independent Pilot3 checker missing'
    return importlib.import_module('experiments.verified_superoptimizer_c1b1.pilot3_checker')


def packet_at(raw,F):return P.RawRelative(tuple(raw),F,tuple(Q(v,1<<F) for v in raw))


@pytest.mark.parametrize('fault',['scale_plus','scale_minus','sign'])
def test_B_wrong_real_relative_implementation_is_caught(fault):
    k=checker();pos=FixedPoint(96,48)
    i=C.Atom('Ar40',(1,-3,17),(0,0,0));j=C.Atom('Ar40',(1<<50,5,31),(0,0,0))
    def wrong(pos,i,j):
        raw=tuple(b-a for a,b in zip(i.r,j.r))
        if fault=='sign':raw=tuple(-v for v in raw)
        F=pos.frac_bits+(1 if fault=='scale_plus' else -1 if fault=='scale_minus' else 0)
        return packet_at(raw,F)
    k.check_relative(i.r,j.r,48,P.relative_raw(pos,i,j))
    with pytest.raises(AssertionError):k.check_relative(i.r,j.r,48,wrong(pos,i,j))


@pytest.mark.parametrize('fault',['scale_plus','scale_minus','omit_term','upper_minus_one'])
def test_C_wrong_real_radius_implementation_is_caught(fault):
    k=checker();raw=(3,4,5);F=0;M=128
    def correct(raw,F,M):return P.radius_raw(sum(v*v for v in raw),F,M)
    def wrong(raw,F,M):
        n=sum(v*v for v in (raw[:2] if fault=='omit_term' else raw))
        f=F+(1 if fault=='scale_plus' else -1 if fault=='scale_minus' else 0)
        if fault=='scale_minus':n <<= 2;f=F # Wrong R² scale equivalent to shift -1.
        lo,hi=P.radius_raw(n,f,M)
        return lo,hi-1 if fault=='upper_minus_one' else hi
    k.check_radius(raw,F,M,correct)
    with pytest.raises(AssertionError):k.check_radius(raw,F,M,wrong)


@pytest.mark.parametrize('fault',['scale_plus','scale_minus','dt_numerator','denominator_reuse','sign'])
def test_D_wrong_real_final_interval_implementation_is_caught(fault):
    k=checker();g=(-30,-20);v=17;F=7;dt=Q(7,11);M=128
    def wrong(g,v,F,dt,M):
        if fault=='dt_numerator':dt=Q(dt.numerator+1,dt.denominator)
        if fault=='sign':v=-v
        if fault=='denominator_reuse':
            # Stale dt denominator from another run (13, current run uses 11).
            a,b=g[0]*v*dt.numerator,g[1]*v*dt.numerator
            return min(a,b),max(a,b),13<<(M+F)
        F=F+(1 if fault=='scale_plus' else -1 if fault=='scale_minus' else 0)
        return P.component_interval(g,v,F,dt,M)
    k.check_component(g,v,F,dt,M,P.component_interval)
    with pytest.raises(AssertionError):k.check_component(g,v,F,dt,M,wrong)


def test_D_wrong_half_even_parity_in_actual_decision_code_is_caught():
    k=checker()
    def wrong_parity(n,d):
        sign=-1 if n<0 else 1;q,r=divmod(abs(n),d)
        return sign*(q+int(2*r>d or (2*r==d and q%2==0)))
    ns=dict(P.decide_raw.__globals__);ns['_div_round']=wrong_parity
    wrong=FunctionType(P.decide_raw.__code__,ns,'wrong_half_even')
    mom=FixedPoint(8,0)
    k.check_rounding(5,2,8,0,P.decide_raw(mom,lambda M:(5,5,2)))
    with pytest.raises(AssertionError):k.check_rounding(5,2,8,0,wrong(mom,lambda M:(5,5,2)))


def test_A_wrong_constant_denominator_in_actual_model_is_caught():
    k=checker();ns=dict(P.model_prepared.__globals__)
    ns['_scale']=lambda a,c:P._scale(a,(c[0],c[1]+1))
    wrong=FunctionType(P.model_prepared.__code__,ns,'wrong_constant_denominator')
    wrong.__kwdefaults__=P.model_prepared.__kwdefaults__
    k.check_model(Q(100),128,True,P.model_prepared)
    with pytest.raises(AssertionError):k.check_model(Q(100),128,True,wrong)
