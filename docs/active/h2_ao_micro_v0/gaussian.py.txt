"""Independent Cartesian Gaussian Hermite recurrence, narrow AO spot use.

No PySCF/libcint integral calls, numerical arrays, or old AO values here.
Representation coefficients are explicitly supplied, including angular norms.
All supplied binary64 numbers are promoted EXACTLY; the INTEGRALS are newly
evaluated, unlike promoting an existing libcint integral.
"""
from functools import lru_cache
from itertools import product
import mpmath as mp


def boys(n,t):
    if t==0: return mp.mpf(1)/(2*n+1)
    a=mp.mpf(n)+mp.mpf('0.5')
    return mp.gammainc(a,0,t)/(2*t**a)


def hermite(i,j,displacement,a,b):
    p=a+b
    @lru_cache(None)
    def e(i,j,t):
        if t<0 or t>i+j or i<0 or j<0: return mp.mpf(0)
        if i==j==0: return mp.exp(-a*b/p*displacement**2)
        if i:
            return e(i-1,j,t-1)/(2*p)-b/p*displacement*e(i-1,j,t)+(t+1)*e(i-1,j,t+1)
        return e(i,j-1,t-1)/(2*p)+a/p*displacement*e(i,j-1,t)+(t+1)*e(i,j-1,t+1)
    return [e(i,j,t) for t in range(i+j+1)]


def primitive_overlap(a,A,la,b,B,lb):
    value=(mp.pi/(a+b))**mp.mpf('1.5')
    for axis in range(3): value*=hermite(la[axis],lb[axis],A[axis]-B[axis],a,b)[0]
    return value


def primitive_eri(a,A,la,b,B,lb,c,C,lc,d,D,ld):
    p=a+b; q=c+d; alpha=p*q/(p+q)
    P=[(a*x+b*y)/p for x,y in zip(A,B)]
    Q=[(c*x+d*y)/q for x,y in zip(C,D)]
    pq=[x-y for x,y in zip(P,Q)]
    argument=alpha*sum(x*x for x in pq)
    eab=[hermite(la[t],lb[t],A[t]-B[t],a,b) for t in range(3)]
    ecd=[hermite(lc[t],ld[t],C[t]-D[t],c,d) for t in range(3)]
    @lru_cache(None)
    def r(t,u,v,n):
        if t==u==v==0: return (-2*alpha)**n*boys(n,argument)
        if t: return (t-1)*r(t-2,u,v,n+1)+pq[0]*r(t-1,u,v,n+1) if t>1 else pq[0]*r(0,u,v,n+1)
        if u: return (u-1)*r(t,u-2,v,n+1)+pq[1]*r(t,u-1,v,n+1) if u>1 else pq[1]*r(t,0,v,n+1)
        return (v-1)*r(t,u,v-2,n+1)+pq[2]*r(t,u,v-1,n+1) if v>1 else pq[2]*r(t,u,0,n+1)
    value=mp.mpf(0)
    for t,u,v in product(*(range(len(x)) for x in eab)):
        left=eab[0][t]*eab[1][u]*eab[2][v]
        if not left: continue
        for x,y,z in product(*(range(len(a)) for a in ecd)):
            right=ecd[0][x]*ecd[1][y]*ecd[2][z]
            if right: value+=left*right*(-1)**(x+y+z)*r(t+x,u+y,v+z,0)
    return 2*mp.pi**mp.mpf('2.5')/(p*q*mp.sqrt(p+q))*value


def terms(orbital):
    center=tuple(mp.mpf(float(x)) for x in orbital['center'])
    return [(mp.mpf(float(ex)),center,tuple(poly['powers']),mp.mpf(float(rad))*mp.mpf(float(poly['coefficient'])))
            for ex,rad in zip(orbital['exponents'],orbital['radial']) for poly in orbital['polynomial']]


def overlap(a,b):
    return mp.fsum(aa[3]*bb[3]*primitive_overlap(*aa[:3],*bb[:3]) for aa,bb in product(terms(a),terms(b)))


def eri(a,b,c,d):
    return mp.fsum(aa[3]*bb[3]*cc[3]*dd[3]*primitive_eri(*aa[:3],*bb[:3],*cc[:3],*dd[:3])
                   for aa,bb,cc,dd in product(terms(a),terms(b),terms(c),terms(d)))
