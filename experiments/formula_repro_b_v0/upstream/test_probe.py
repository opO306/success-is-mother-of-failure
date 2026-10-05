from fractions import Fraction as Q
import pytest
import probe as P

@pytest.mark.parametrize('b',[64,128,192])
@pytest.mark.parametrize('backend',['mp','decimal'])
def test_interval_algebra(backend,b):
    B=P.Backend(backend,b)
    pairs=[(Q(1,3),Q(2,7)),(Q(-19,13),Q(2,11)),(Q(13),Q(-1,1000))]
    for x,y in pairs:
        a,c=B.lift(x),B.lift(y)
        for v,t in [(a+c,x+y),(a-c,x-y),(a*c,x*y),(a/c,x/y)]:
            lo,hi=B.bounds(v)
            assert lo <= t <= hi

@pytest.mark.parametrize('radius',['2.3','3','7.1','10','25','100'])
@pytest.mark.parametrize('backend',['mp','decimal'])
def test_compiled_force(radius,backend):
    lo,hi=P.reference_force(Q(radius),bits=320)
    B=P.Backend(backend,128)
    f=P.Force(B,compiled=True)
    a,b=B.bounds(f(B.lift(Q(radius)**2)))
    assert a <= lo <= hi <= b

def test_domain():
    B=P.Backend('mp',128)
    with pytest.raises(P.DomainStop):
        P.evolve([(Q(0),)*3]*2,[(Q(0),)*3]*2,1,B,True)

def test_exact_free_tie():
    assert P.exact_free_tie()==0

def test_rns():
    for n in range(-100,101):
        assert P.crt_decode(P.rns_encode(n,[5,7,11]),[5,7,11],signed=True)==n

@pytest.mark.parametrize('radius',['2.3','7.1','25'])
def test_cache_only_preserves_endpoints(radius):
    B=P.Backend('mp',128)
    x=B.lift(Q(radius)**2)
    assert P.Force(B,compiled='cache')(x)._mpi_==P.LI.G_of_R2(x)._mpi_

@pytest.mark.parametrize('backend',['mp','decimal'])
def test_interval_transcendentals(backend):
    import mpmath as m
    for x in (Q(1,100),Q(2),Q(37,10)):
        H=P.Backend('mp',384)
        e_ref=H.bounds(m.iv.exp(H.lift(x)))
        s_ref=H.bounds(m.iv.sqrt(H.lift(x)))
        B=P.Backend(backend,128)
        for v,ref in ((B.exp(B.lift(x)),e_ref),(B.sqrt(B.lift(x)),s_ref)):
            lo,hi=B.bounds(v)
            assert lo<=ref[0]<=ref[1]<=hi

def test_compiler_exact_symbolic_identity():
    import sympy as s
    x=s.symbols('x',positive=True)
    cv=lambda v:s.Rational(v.numerator,v.denominator)
    expr=lambda D:sum(cv(a)*x**i for i,a in D.items())
    groups,tail,num,den,dn,k,c=P.PROGRAM
    original_tail=0
    for j,(name,(short,(eta,C,ka))) in enumerate(P.L.COMPONENTS.items()):
        for z,(alpha,D) in enumerate(short.values()):
            assert s.expand(s.diff(expr(D),x)-cv(alpha)*expr(D)-expr(groups[3*j+z][1]))==0
        exponential_part=0
        for kk,cc in C.items():
            n=2*kk+ka
            S=sum((cv(eta)*x)**i/s.factorial(i) for i in range(n+1))
            # Independently differentiate the positive exponential term in V.
            q=cv(cc)*S*x**(-2*kk)
            exponential_part+=s.diff(q,x)-cv(eta)*q
            if not(kk==min(C) and name in ('BO','REL')):
                original_tail+=2*kk*cv(cc)*x**(-2*kk-1)
        assert s.expand(exponential_part-expr(groups[3*j+2][1]))==0
    assert s.expand(original_tail-expr(tail))==0
    assert s.expand(s.diff(expr(num),x)*expr(den)-expr(num)*s.diff(expr(den),x)-expr(dn))==0
