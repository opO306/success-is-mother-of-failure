"""Fixed published integrator coefficients; no production KDK calls."""
import math
import mpmath as m


def coefficients():
    s=m.root(2,3);w=1/(2-s);z=-s/(2-s)
    return dict(yoshida4=dict(kick=[w/2,(w+z)/2,(w+z)/2,w/2],drift=[w,z,w]),
                chin4a=dict(kick=[m.mpf(1)/6,m.mpf(2)/3,m.mpf(1)/6],drift=[m.mpf(1)/2]*2,gradient=m.mpf(1)/48))


def advance(method,q,p,h,mu,field,chord):
    if method=='yoshida4':
        cs=coefficients()['yoshida4'];q=q[:];p=p[:]
        for index,a in enumerate(cs['kick']):
            f=field.force(q);p=[x+a*h*y for x,y in zip(p,f)]
            if index<len(cs['drift']):
                old=q;q=[x+cs['drift'][index]*h*y/mu for x,y in zip(q,p)]
                chord(old,q)
        return q,p
    if method=='chin4a':
        q=q[:];p=p[:]
        for index,a in enumerate([m.mpf(1)/6,m.mpf(2)/3,m.mpf(1)/6]):
            f=field.gradient_force(q,h) if index==1 else field.force(q)
            p=[x+a*h*y for x,y in zip(p,f)]
            if index<2:
                old=q;q=[x+h*y/(2*mu) for x,y in zip(q,p)];chord(old,q)
        return q,p
    raise ValueError('only the two sealed methods are allowed')


def first_gate(error,cost,gain,stable,domain,conservation):
    if not stable:return 'UNRESOLVED_PRECISION'
    if not domain:return 'REJECT_DOMAIN'
    if not conservation:return 'REJECT_CONSERVATION'
    if not math.isfinite(error) or error>1e-5:return 'REJECT_ACCURACY'
    if not math.isfinite(cost) or cost>2 or (cost>1 and gain<10):return 'REJECT_COST'
    if cost<=1 and gain>=1:return 'BEATS_KDK20_KERNEL'
    if gain>=10:return 'PROMISING_PARETO'
    return 'NO_TRADEOFF_GAIN'
