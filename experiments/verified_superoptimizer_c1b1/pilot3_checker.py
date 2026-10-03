"""Independent Fraction obligations; no executor, profile or candidate imports.

The retained independent Pilot1 checker supplies frozen-parameter grid endpoints.
This is implementation equivalence evidence, not an independent physics model.
"""
from fractions import Fraction as Q
from . import checker as original_checker


def check_relative(ri,rj,F,packet):
    expected=tuple(Q(b,2**F)-Q(a,2**F) for a,b in zip(ri,rj))
    assert tuple(packet)==expected,'raw relative exact value mismatch'
    assert packet.shift==F,'raw relative scale mismatch'
    assert tuple(packet.raw)==tuple(b-a for a,b in zip(ri,rj)),'raw relative integer difference mismatch'


def check_radius(raw,F,M,function):
    squared=sum((Q(v,2**F)**2 for v in raw),Q(0))
    assert function(raw,F,M)==original_checker.radius_raw(squared,M),'same-M radius endpoints differ'


def check_component(g,v,F,dt,M,function):
    endpoints=sorted(Q(x,2**M)*Q(v,2**F)*dt for x in g)
    lo,hi,d=function(g,v,F,dt,M)
    assert d>0
    assert lo*endpoints[0].denominator==endpoints[0].numerator*d,'component lower endpoint differs'
    assert hi*endpoints[1].denominator==endpoints[1].numerator*d,'component upper endpoint differs'


def check_rounding(n,d,width,F,raw):
    expected=original_checker.round_raw(Q(n,d),dict(kind='FX',width=width,frac=F))
    assert expected==('value',raw),'nearest-even or range decision differs'


def check_model(R2,M,ret,function):
    radius=original_checker.radius_raw(R2,M)
    expected=original_checker.model(R2,M,ret)
    assert function(radius,M,ret)==expected,'dV / inverse endpoints differ from independent checker'
