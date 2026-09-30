"""Raw integer KDK and unrounded segment guard, independently implemented."""
from fractions import Fraction as Q
from . import spec
from .types import Invalid

def raw(v):
    if type(v) is not int or not spec.LOW <= v <= spec.HIGH:
        raise Invalid("not a signed96 raw integer")
    return v

def state(values):
    if not isinstance(values, (tuple, list)) or len(values) != 12:
        raise Invalid("state must have 12 raw integers")
    return tuple(raw(v) for v in values)

def impulse(values):
    if not isinstance(values, (tuple, list)) or len(values) != 3:
        raise Invalid("J must have three raw integers")
    return tuple(raw(v) for v in values)

def nearest(n, d):
    if d <= 0:
        raise ValueError("positive denominator required")
    magnitude, rem = divmod(abs(n), d)
    if 2*rem > d or (2*rem == d and magnitude & 1):
        magnitude += 1
    return -magnitude if n < 0 else magnitude

def relative(s):
    return tuple(Q(s[6+c]-s[c], 1<<48) for c in range(3))

def radius2(s):
    return sum(x*x for x in relative(s))

def kinetic(s):
    return sum(Q(s[9+c]-s[3+c], 1<<81)**2 for c in range(3))/spec.MASS

def outgoing(s):
    return radius2(s) >= 400 and sum((s[6+c]-s[c])*(s[9+c]-s[3+c]) for c in range(3)) > 0

def guard(a, delta):
    length = sum(x*x for x in delta)
    dot = sum(x*y for x,y in zip(a,delta))
    u = min(Q(1),max(Q(0),-dot/length)) if length else Q(0)
    if sum((x+u*d)**2 for x,d in zip(a,delta)) < spec.R_MIN2:
        raise Invalid("unrounded drift segment enters r_min")

def drift(s, j):
    s, j = state(s), impulse(j)
    p = tuple(raw(s[3+c]-j[c]) for c in range(3))
    q = tuple(raw(s[9+c]+j[c]) for c in range(3))
    scale = spec.DT/spec.MASS
    # displacement and addition are distinct checked operations, as in drift v2.
    di = tuple(raw(nearest(v*scale.numerator,scale.denominator*(1<<32))) for v in p)
    dj = tuple(raw(nearest(v*scale.numerator,scale.denominator*(1<<32))) for v in q)
    ri = tuple(raw(s[c]+di[c]) for c in range(3))
    rj = tuple(raw(s[6+c]+dj[c]) for c in range(3))
    delta = tuple(Q(q[c]-p[c],1<<80)*scale for c in range(3))
    guard(relative(s),delta)
    out = ri+p+rj+q
    if radius2(out) < spec.R_MIN2:
        raise Invalid("stored position enters r_min")
    return out

def finish(mid, j):
    j = impulse(j)
    return mid[:3]+tuple(raw(mid[3+c]-j[c]) for c in range(3))+mid[6:9]+tuple(raw(mid[9+c]+j[c]) for c in range(3))

def transition(s,j,next_j):
    return finish(drift(s,j),next_j)
