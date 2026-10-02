"""Independent residual enclosure for the exact stored dyadic input matrices.

No executor imports, BLAS arithmetic, or high-precision library is used in
the exact path. Bounds certify only this finite input residual, not AO physics.
"""
import math
from fractions import Fraction


def scaled_dyadics(matrix):
    ratios=[[float(x).as_integer_ratio() for x in row] for row in matrix]
    power=max(d.bit_length()-1 for row in ratios for _,d in row)
    integers=[[num << (power-(den.bit_length()-1)) for num,den in row] for row in ratios]
    return integers,power


def matmul_int(a,b):
    cols=list(zip(*b))
    return [[sum(x*y for x,y in zip(row,col)) for col in cols] for row in a]


def residual_dyadics(s,c):
    n=len(s)
    if not n or any(len(row)!=n for row in s+c): raise ValueError('square full matrices required')
    si,sp=scaled_dyadics(s);ci,cp=scaled_dyadics(c)
    integer=matmul_int(list(zip(*ci)),matmul_int(si,ci))
    denominator=1 << (sp+2*cp)
    for i in range(n): integer[i][i]-=denominator
    return integer,denominator


def sqrt_enclosure(square,digits=40):
    if square<0: raise ValueError('negative square')
    scale=10**digits
    k=math.isqrt(square.numerator*scale**2//square.denominator)
    exact=k*k*square.denominator==square.numerator*scale**2
    def decimal(integer):
        return str(integer//scale)+'.'+str(integer%scale).zfill(digits)
    return [decimal(k),decimal(k if exact else k+1)]


def exact_norm_bounds(s,c,threshold='1e-10'):
    integer,den=residual_dyadics(s,c);n=len(integer)
    lower_sq=Fraction(max(sum(integer[i][j]**2 for i in range(n)) for j in range(n)),den**2)
    upper_sq=Fraction(sum(x*x for row in integer for x in row),den**2)
    tau=Fraction(threshold)
    verdict='BELOW' if upper_sq<tau*tau else 'ABOVE' if lower_sq>tau*tau else 'UNRESOLVED'
    return dict(operator_norm_lower=sqrt_enclosure(lower_sq)[0],
                operator_norm_upper=sqrt_enclosure(upper_sq)[1],
                frobenius_enclosure=sqrt_enclosure(upper_sq),
                exact_lower_squared=[str(lower_sq.numerator),str(lower_sq.denominator)],
                exact_upper_squared=[str(upper_sq.numerator),str(upper_sq.denominator)],
                threshold=threshold,relation=verdict,dimension=n,
                exact_residual_denominator_bits=den.bit_length(),
                scope='exact binary64 stored-input residual only; integer/Fraction implementation trusted; no solver or AO certification')


def interval_product(al,au,bl,bu):
    import numpy as np
    lo=np.zeros((al.shape[0],bl.shape[1]));hi=lo.copy()
    for k in range(al.shape[1]):
        products=np.stack([a[:,k,None]*b[k,None,:] for a in (al,au) for b in (bl,bu)])
        low=np.nextafter(products.min(axis=0),-np.inf)
        high=np.nextafter(products.max(axis=0),np.inf)
        lo=np.nextafter(lo+low,-np.inf);hi=np.nextafter(hi+high,np.inf)
    if not np.isfinite(lo).all() or not np.isfinite(hi).all(): raise ValueError('interval overflow/nonfinite')
    return lo,hi


def cheap_interval_bounds(s,c,threshold='1e-10'):
    import numpy as np
    s=np.asarray(s);c=np.asarray(c)
    lo,hi=interval_product(s,s,c,c)
    lo,hi=interval_product(c.T,c.T,lo,hi)
    eye=np.eye(len(s))
    lo=np.nextafter(lo-eye,-np.inf);hi=np.nextafter(hi-eye,np.inf)
    minabs=np.where((lo<=0)&(hi>=0),0,np.minimum(abs(lo),abs(hi)))
    lower=Fraction(float(minabs.max()))
    upper=len(s)*Fraction(float(np.maximum(abs(lo),abs(hi)).max()))
    tau=Fraction(threshold)
    verdict='BELOW' if upper<tau else 'ABOVE' if lower>tau else 'UNRESOLVED'
    return dict(operator_norm_lower=str(lower),operator_norm_upper=str(upper),relation=verdict,
                scope='outward nextafter after each binary64 multiplication/addition; IEEE round-to-nearest, gradual underflow, no FTZ assumed')


def adaptive_guard(s,c,threshold='1e-10'):
    import time
    start=time.perf_counter();cheap=cheap_interval_bounds(s,c,threshold)
    cheap_seconds=time.perf_counter()-start
    exact=None;fallback_seconds=0.
    if cheap['relation']=='UNRESOLVED':
        start=time.perf_counter();exact=exact_norm_bounds(s.tolist(),c.tolist(),threshold)
        fallback_seconds=time.perf_counter()-start
    relation=exact['relation'] if exact else cheap['relation']
    return dict(cheap=cheap,exact_fallback=exact,relation=relation,
                cheap_seconds=cheap_seconds,fallback_seconds=fallback_seconds,
                production_applied=False,changes_original_QZ44=False)
