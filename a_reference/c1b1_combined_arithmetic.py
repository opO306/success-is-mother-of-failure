"""Combined-only exact production arithmetic. Explicit opt-in, unchanged REF step.

Integer ratios retain exact displacement; only displacement is rounded. Fraction
endpoints still feed the original segment guard. No global cache or research imports.
"""
from dataclasses import dataclass
from types import FunctionType
from fractions import Fraction as Q
from a_numeric.profiles import FixedPoint, VMHalt, _div_round
from . import c1b1_two_atom as C, c1b1_fast_impulse as F


def canonical_fx(profile):
    """Reject lookalikes, subclasses, per-instance overrides and inconsistent fields."""
    if type(profile) is not FixedPoint: return None
    w,f=profile.width,profile.frac_bits
    if type(w) is not int or type(f) is not int or not 0<=f<w or w<2: return None
    expected=dict(width=w,frac_bits=f,lo=-(1<<(w-1)),hi=(1<<(w-1))-1,name=f'FX({w},{f})')
    return (w,f) if vars(profile)==expected else None


@dataclass(frozen=True)
class DriftConversionContract:
    pos: object
    mom: object
    dt: Q
    mass: Q
    pos_signature: tuple
    mom_signature: tuple
    multiplier: int
    denominator: int
    position_shift: int

    @classmethod
    def build(cls,pos,mom,dt,mass):
        ps,ms=canonical_fx(pos),canonical_fx(mom)
        if ps is None or ms is None: raise C.ContractViolation('unsupported raw drift profile')
        if type(dt) not in (int,Q) or type(mass) not in (int,Q):
            raise C.ContractViolation('raw drift needs exact int/Fraction coefficients')
        dt,mass=Q(dt),Q(mass)
        if mass<=0: raise C.ContractViolation('raw drift needs positive mass')
        return cls(pos,mom,dt,mass,ps,ms,dt.numerator*mass.denominator,
                   (1<<ms[1])*dt.denominator*mass.numerator,ps[1])

    def ratio(self,raw):
        self.assert_current()
        return self._ratio(raw)

    def assert_current(self):
        if canonical_fx(self.pos)!=self.pos_signature or canonical_fx(self.mom)!=self.mom_signature:
            raise C.ContractViolation('stale drift contract')

    def _ratio(self,raw):
        if not self.mom.valid_raw(raw): raise C.ContractViolation('invalid stored raw for profile')
        return raw*self.multiplier,self.denominator

    def rounded(self,num,den):
        self.assert_current()
        return self._rounded(num,den)

    def _rounded(self,num,den):
        if type(num) is not int or type(den) is not int or den<=0:
            raise C.ContractViolation('raw drift needs integer numerator and positive denominator')
        raw=_div_round(num<<self.position_shift,den)
        try: return self.pos._check(raw)
        except VMHalt as halt:
            if halt.reason!='overflow': raise
            # Preserve original from_exact refusal and cause, without Fraction construction.
            raise C.ExecutorLimitExceeded('overflow in from_exact') from halt


@dataclass(frozen=True)
class RawPreparedDrift:
    exact_ratios: tuple
    stored_displacement: tuple


def prepare_drift(contract,raws):
    contract.assert_current()
    ratios=tuple(contract._ratio(v) for v in raws)
    stored=tuple(contract._rounded(n,d) for n,d in ratios)
    return RawPreparedDrift(ratios,stored)


def drift(contract,pos,mom,atom,dt,rule='v2'):
    if rule!='v2': return C._drift(pos,mom,atom,dt,rule)
    if (pos is not contract.pos or mom is not contract.mom or dt!=contract.dt or
        C.SPECIES_MASS[atom.species]!=contract.mass):
        raise C.ContractViolation('stale drift contract')
    packet=prepare_drift(contract,atom.p)
    # Fraction is retained where the existing exact segment guard consumes endpoints.
    endpoint=tuple(r+Q(n,d) for r,(n,d) in zip(C.exact(pos,atom.r),packet.exact_ratios))
    raws=tuple(C._limit(pos.add,r,d) for r,d in zip(atom.r,packet.stored_displacement))
    return C.Atom(atom.species,raws,atom.p),endpoint


def _checked_sum(mom,raw):
    try: return mom._check(raw)
    except VMHalt as halt:
        if halt.reason!='overflow': raise
        raise C.ExecutorLimitExceeded('overflow in from_exact') from halt


def kick(mom,atoms,J):
    if canonical_fx(mom) is None: return C._kick(mom,atoms,J)
    i,j=atoms
    if not all(mom.valid_raw(v) for raws in (i.p,j.p,J) for v in raws):
        raise C.ContractViolation('invalid stored raw for profile')
    pi=tuple(_checked_sum(mom,p-q) for p,q in zip(i.p,J))
    pj=tuple(_checked_sum(mom,p+q) for p,q in zip(j.p,J))
    return C.Atom(i.species,i.r,pi),C.Atom(j.species,j.r,pj)


class CombinedRuntime:
    """Prepared coefficients belong to this exact Run and its current contract."""
    def __init__(self,run):
        self.run=run
        self._bound_run=run
        ns=dict(F.step_fast.__globals__)
        ns['_kick']=kick
        self.raw_drift_enabled=(run.drift=='v2' and canonical_fx(run.pos) is not None
                                and canonical_fx(run.mom) is not None)
        if self.raw_drift_enabled:
            self.contracts={a.species:DriftConversionContract.build(run.pos,run.mom,run.dt,
                            C.SPECIES_MASS[a.species]) for a in run.atoms}
            self.binding=(run.pos,run.mom,run.dt,tuple(a.species for a in run.atoms),
                          canonical_fx(run.pos),canonical_fx(run.mom),run.drift)
            def prepared_drift(pos,mom,atom,dt,rule='v2'):
                return drift(self.contracts[atom.species],pos,mom,atom,dt,rule)
            ns['_drift']=prepared_drift
        self.function=FunctionType(C.step.__code__,ns,'step_combined')

    def step(self):
        r=self.run
        if r is not self._bound_run:
            raise C.ContractViolation('stale drift contract: different Run')
        if self.raw_drift_enabled:
            now=(r.pos,r.mom,r.dt,tuple(a.species for a in r.atoms),
                 canonical_fx(r.pos),canonical_fx(r.mom),r.drift)
            if (now!=self.binding or type(r.dt) not in (int,Q) or
                any(C.SPECIES_MASS.get(s)!=k.mass for s,k in self.contracts.items())):
                raise C.ContractViolation('stale drift contract')
        return self.function(r)


def step(run):
    """One-shot entry; retain bind(run) for repeated steps and prepared reuse."""
    return CombinedRuntime(run).step()
