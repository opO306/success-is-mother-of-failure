"""Read-only, throwaway comparison for Exact Expression's unrounded KDK map.
Not C1-B1. Not a certified engine. No random numbers in world evolution.
Source: opO306/success-is-mother-of-failure @ 0ecfb7f.
"""
from __future__ import annotations
from fractions import Fraction as Q
from decimal import Decimal, Context, ROUND_FLOOR, ROUND_CEILING
from math import factorial, ceil, log10, prod
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0,str(Path(__file__).parent/'vendor'))
from mpmath import iv
from mpmath.libmp import to_rational
from exact_expression_gate_v0 import lang_iv as LI
from a_reference import ar2_lang2024 as L

MASS=Q('39.9623831237')/Q('5.485799090441e-4')
DT=Q(40)
RMIN2=L.R_MIN_BOHR**2
GRID=[64,96,128,192,256,384,512]

class DomainStop(Exception):
    def __init__(self,kind): self.kind=kind

class DI:
    """Decimal interval. Arithmetic rounds outward; sqrt/exp get one-ulp guards.

    Decimal sqrt/exp are correctly rounded half-even, irrespective of the
    requested directed context mode. Therefore next_minus/next_plus are applied.
    """
    __slots__=('lo','hi','B')
    def __init__(self,lo,hi,B): self.lo,self.hi,self.B=lo,hi,B
    def coerce(self,o): return o if isinstance(o,DI) else self.B.lift(o)
    def __add__(self,o):
        o=self.coerce(o); B=self.B
        return DI(B.down.add(self.lo,o.lo),B.up.add(self.hi,o.hi),B)
    __radd__=__add__
    def __neg__(self): return DI(self.hi.copy_negate(),self.lo.copy_negate(),self.B)
    def __sub__(self,o): return self+-self.coerce(o)
    def __rsub__(self,o): return self.coerce(o)+-self
    def __mul__(self,o):
        o=self.coerce(o); B=self.B
        low=min(B.down.multiply(a,b) for a in (self.lo,self.hi) for b in (o.lo,o.hi))
        high=max(B.up.multiply(a,b) for a in (self.lo,self.hi) for b in (o.lo,o.hi))
        return DI(low,high,B)
    __rmul__=__mul__
    def __truediv__(self,o):
        o=self.coerce(o); B=self.B
        if o.lo<=0<=o.hi: raise ZeroDivisionError('interval denominator contains zero')
        inv=DI(B.down.divide(Decimal(1),o.hi),B.up.divide(Decimal(1),o.lo),B)
        return self*inv
    def __rtruediv__(self,o): return self.coerce(o)/self
    def __pow__(self,n):
        if not isinstance(n,int): raise TypeError('integer exponent required')
        if n<0:return 1/(self**(-n))
        if n==0:return self.B.lift(1)
        out=self.B.lift(1); x=self
        while n:
            if n&1:out=out*x
            n//=2
            if n:x=x*x
        return out
    def exp(self):
        B=self.B
        return DI(B.down.next_minus(B.down.exp(self.lo)),B.up.next_plus(B.up.exp(self.hi)),B)
    def sqrt(self):
        B=self.B
        if self.lo<0:raise ValueError('sqrt domain')
        lo=B.down.next_minus(B.down.sqrt(self.lo)) if self.lo else Decimal(0)
        hi=B.up.next_plus(B.up.sqrt(self.hi)) if self.hi else Decimal(0)
        return DI(lo,hi,B)

class Backend:
    def __init__(self,name,bits):
        self.name,self.bits=name,int(bits)
        if name=='mp': iv.prec=self.bits
        elif name=='decimal':
            self.digits=ceil(self.bits*log10(2))
            self.down=Context(prec=self.digits,rounding=ROUND_FLOOR)
            self.up=Context(prec=self.digits,rounding=ROUND_CEILING)
        else: raise ValueError(name)
    def lift(self,x):
        x=Q(x)
        if self.name=='mp':return LI.c(x)
        n,d=Decimal(x.numerator),Decimal(x.denominator)
        return DI(self.down.divide(n,d),self.up.divide(n,d),self)
    def bounds(self,x):
        if isinstance(x,Q):return x,x
        if self.name=='decimal':return Q(x.lo),Q(x.hi)
        return Q(*to_rational(x._mpi_[0])),Q(*to_rational(x._mpi_[1]))
    def sqrt(self,x):return iv.sqrt(x) if self.name=='mp' else x.sqrt()
    def exp(self,x):return iv.exp(x) if self.name=='mp' else x.exp()


def add_poly(out,k,a):
    out[k]+=a
    if out[k]==0:del out[k]

def pmul(a,b):
    out=defaultdict(Q)
    for i,c in a.items():
        for j,d in b.items():add_poly(out,i+j,c*d)
    return out

def pder(a):return {i-1:i*c for i,c in a.items() if i}

def exact_program():
    """Compile exact identities, without sample values or fitted coefficients."""
    groups=[]; tail=defaultdict(Q)
    for name,(short,(eta,C,kadd)) in L.COMPONENTS.items():
        for alpha,P in short.values():
            poly=defaultdict(Q)
            for i,a in P.items():
                if i:add_poly(poly,i-1,i*a)
                add_poly(poly,i,-alpha*a)
            groups.append((alpha,dict(poly)))
        poly=defaultdict(Q)
        for k,c in C.items():
            n=2*k+kadd
            add_poly(poly,n-2*k,-c*eta**(n+1)/factorial(n))
            for i in range(n+1):
                add_poly(poly,i-2*k-1,-2*k*c*eta**i/factorial(i))
            if not(k==min(C) and name in ('BO','REL')):
                add_poly(tail,-2*k-1,2*k*c)
        groups.append((eta,dict(poly)))
    num={0:Q(1),**{i+1:a for i,a in enumerate(L.RET_A)}}
    den={0:Q(1),**{i+1:a for i,a in enumerate(L.RET_B)}}
    dn=pmul(pder(num),den)
    for i,a in pmul(num,pder(den)).items():add_poly(dn,i,-a)
    k=min(L.BO_LONG[1]); c=L.BO_LONG[1][k]
    return groups,dict(tail),num,den,dict(dn),k,c

PROGRAM=exact_program()

class Laurent:
    """Exact zero coefficients removed before numerical evaluation; Horner blocks."""
    def __init__(self,coefs,B):
        self.zero=B.lift(0)
        positive=max([i for i in coefs if i>=0],default=-1)
        negative=max([-i for i in coefs if i<0],default=0)
        self.pos=tuple(B.lift(coefs.get(i,0)) for i in range(positive,-1,-1))
        self.neg=tuple(B.lift(coefs.get(-i,0)) for i in range(negative,0,-1))
    def __call__(self,r,inv):
        a=self.zero
        for c in self.pos:a=a*r+c
        b=self.zero
        for c in self.neg:b=b*inv+c
        return a+b*inv if self.neg else a

class Force:
    def __init__(self,B,compiled):
        self.B,self.compiled=B,compiled
        if compiled == 'cache':
            from types import FunctionType
            ns=dict(LI.__dict__)
            cache={}
            def c_cached(x):
                x=Q(x)
                if x not in cache:cache[x]=B.lift(x)
                return cache[x]
            ns['c']=c_cached
            for name in ('_poly','_poly_deriv','_g','_component_deriv','dVdR','G_of_R2'):
                f=getattr(LI,name)
                ns[name]=FunctionType(f.__code__,ns,f.__name__,f.__defaults__)
            self.original_cached=ns['G_of_R2']
            return
        if compiled:
            groups,tail,num,den,dn,k,c=PROGRAM
            self.groups=[(B.lift(a),Laurent(P,B)) for a,P in groups]
            self.tail,self.num,self.den,self.dn=[Laurent(P,B) for P in (tail,num,den,dn)]
            self.k,self.c=k,B.lift(c)
    def __call__(self,r2):
        B=self.B
        if self.compiled=='cache':return self.original_cached(r2)
        if not self.compiled:
            if B.name!='mp':raise ValueError('baseline is original mpmath')
            return LI.G_of_R2(r2)
        r=B.sqrt(r2); inv=1/r
        out=self.tail(r,inv)
        for a,P in self.groups:out=out+B.exp(-a*r)*P(r,inv)
        num,den=self.num(r,inv),self.den(r,inv)
        g=num/den; dg=self.dn(r,inv)/(den*den)
        out=out+self.c*(2*self.k*g*inv**(2*self.k+1)-dg*inv**(2*self.k))
        return -out*inv


def reference_force(radius,bits=320):
    B=Backend('mp',bits)
    return B.bounds(LI.G_of_R2(B.lift(radius**2)))

def rhe(x):
    x=Q(x); s=-1 if x<0 else 1
    q,r=divmod(abs(x.numerator),x.denominator)
    if r*2>x.denominator or (r*2==x.denominator and q&1):q+=1
    return s*q

def projection(q,p,B):
    cells=[]; spans=[]
    for rows,F in ((q,48),(p,80)):
        for row in rows:
            for value in row:
                lo,hi=B.bounds(value); lo*=1<<F;hi*=1<<F
                a,b=rhe(lo),rhe(hi)
                if a==b and not -(1<<95)<=a<(1<<95):raise OverflowError('measurement range')
                cells.append(a if a==b else None);spans.append((lo,hi))
    return (None if None in cells else cells),spans


def evolve(q0,p0,steps,B,compiled,checkpoints=None):
    """Same pair forces and unrounded KDK ordering as original stream.py.
    No rounded measurement ever becomes a new world state.
    """
    h,cdt=B.lift(DT/2),B.lift(DT/MASS); zero=B.lift(0)
    q=[[B.lift(x) for x in r] for r in q0]
    p=[[B.lift(x) for x in r] for r in p0]
    n=len(q); force=Force(B,compiled)
    pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
    checks=set(checkpoints or [steps]); out={}
    def forces(q):
        F=[[zero]*3 for _ in q]
        for i,j in pairs:
            d=[q[j][k]-q[i][k] for k in range(3)]
            r2=(d[0]*d[0]+d[1]*d[1])+d[2]*d[2]
            lo,hi=B.bounds(r2)
            if hi<RMIN2:raise DomainStop('VIOLATED')
            if lo<RMIN2:raise DomainStop('UNPROVEN')
            g=force(r2)
            for k in range(3):
                t=(h*g)*d[k]
                F[j][k]=F[j][k]+t; F[i][k]=F[i][k]-t
        return F
    F=forces(q)
    for s in range(1,steps+1):
        p=[[p[a][k]+F[a][k] for k in range(3)] for a in range(n)]
        q=[[q[a][k]+p[a][k]*cdt for k in range(3)] for a in range(n)]
        F=forces(q)
        p=[[p[a][k]+F[a][k] for k in range(3)] for a in range(n)]
        if s in checks:out[s]=projection(q,p,B)
    return out

def ceil_log2_q(x):
    if x<=0:raise ValueError
    e=x.numerator.bit_length()-x.denominator.bit_length()
    if (Q(2)**e)<x:e+=1
    return e

def predict_next(bits,spans,cap=512):
    extra=8
    for lo,hi in spans:
        if rhe(lo)==rhe(hi):continue
        mid=(lo+hi)/2;cell=rhe(mid)
        margin=Q(1,2)-abs(mid-cell)
        if margin<=0:extra=max(extra,32);continue
        # Width/margin is only a predictor. Final enclosure is always checked.
        extra=max(extra,ceil_log2_q((hi-lo)/margin)+8)
    return min(cap,bits+extra)

def exact_free_tie():
    x0=Q(1,1<<49)-DT/MASS
    x1=x0+DT/MASS
    return rhe(x1*(1<<48))

def rns_encode(n,moduli):return [n%m for m in moduli]

def crt_decode(residues,moduli,signed=False):
    N=prod(moduli)
    x=sum(r*(N//m)*pow(N//m,-1,m) for r,m in zip(residues,moduli))%N
    return x-N if signed and x>N//2 else x

SCENARIOS={
 'A2_bound':([('-3.55','0','0'),('3.55','0','0')],[('1','-3','0'),('-1','3','0')]),
 'A3_low':([('0','0','0'),('25','0','0'),('0','25','0')],[('2','1','0'),('-1','2','0'),('-1','-3','0')]),
 'A3_high':([('0','0','0'),('7.1','0','0'),('3.55','6.149','0')],[('3','0','0.5'),('-1.5','2.6','0'),('-1.5','-2.6','-0.5')]),
}
def scenario(name):return tuple([[Q(x) for x in row] for row in part] for part in SCENARIOS[name])
