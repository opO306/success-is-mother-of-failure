"""Fresh potential implementation: automatic derivatives over isolated intervals."""
from fractions import Fraction as Q
from mpmath.ctx_iv import MPIntervalContext
from . import spec
from .types import Invalid, Refused

class Dual:
    __slots__ = ("value", "slope")
    def __init__(self,value,slope):
        self.value,self.slope=value,slope
    def __add__(self,other):
        if isinstance(other,Dual):
            return Dual(self.value+other.value,self.slope+other.slope)
        return Dual(self.value+other,self.slope)
    __radd__=__add__
    def __neg__(self):
        return Dual(-self.value,-self.slope)
    def __sub__(self,other):
        return self+-other
    def __mul__(self,other):
        if isinstance(other,Dual):
            return Dual(self.value*other.value,self.slope*other.value+self.value*other.slope)
        return Dual(self.value*other,self.slope*other)
    __rmul__=__mul__
    def __truediv__(self,other):
        if isinstance(other,Dual):
            return Dual(self.value/other.value,(self.slope*other.value-self.value*other.slope)/(other.value*other.value))
        return Dual(self.value/other,self.slope/other)

def endpoints(value):
    out=[]
    for sign,mantissa,exponent,bits in value._mpi_:
        if not mantissa and (sign,mantissa,exponent,bits)!=(0,0,0,0):
            raise Refused("non-finite interval endpoint")
        v=Q(mantissa<<exponent) if exponent>=0 else Q(mantissa,1<<-exponent)
        out.append(-v if sign else v)
    if out[0]>out[1]:
        raise Refused("invalid interval order")
    return tuple(out)

class Model:
    def __init__(self):
        self.contexts={}

    def context(self,bits):
        if bits not in self.contexts:
            ctx=MPIntervalContext()
            ctx.prec=bits
            cache={}
            self.contexts[bits]=(ctx,cache)
        return self.contexts[bits]

    def evaluate(self,r2,bits):
        ctx,cache=self.context(bits)
        def number(value):
            key=Q(value)
            if key not in cache:
                cache[key]=ctx.mpf(key.numerator)/ctx.mpf(key.denominator)
            return cache[key]
        zero,one=number(0),number(1)
        # State-dependent values must not enter the bounded specification cache.
        radius=ctx.sqrt(ctx.mpf(r2.numerator)/ctx.mpf(r2.denominator))
        r=Dual(radius,one)
        powers=[Dual(one,zero)]
        for _ in range(17):
            powers.append(powers[-1]*r)
        def exp(value):
            val=ctx.exp(value.value)
            return Dual(val,val*value.slope)
        total=Dual(zero,zero)
        for family in ("BO","REL","QED"):
            for alpha,coefficients in spec.SHORT[family].values():
                poly=Dual(zero,zero)
                for exponent,coefficient in coefficients.items():
                    term=powers[exponent] if exponent>=0 else powers[0]/r
                    poly+=term*number(coefficient)
                total+=exp(-r*number(alpha))*poly
            eta,coefficients,kadd=spec.LONG[family]
            x=r*number(eta)
            damping_exp=exp(-x)
            # all factorial-polynomial prefixes from a single recurrence.
            term=prefix=powers[0]
            prefixes=[prefix]
            for i in range(1,2*max(coefficients)+kadd+1):
                term=term*x/number(i)
                prefix=prefix+term
                prefixes.append(prefix)
            for k,coefficient in coefficients.items():
                tail=damping_exp*prefixes[2*k+kadd]
                if k==min(coefficients) and family=="REL":
                    damping=-tail
                elif k==min(coefficients) and family=="BO":
                    numerator=powers[0]
                    denominator=powers[0]
                    for i,a in enumerate(spec.RET_A,1):
                        numerator+=powers[i]*number(a)
                    for i,b in enumerate(spec.RET_B,1):
                        denominator+=powers[i]*number(b)
                    damping=numerator/denominator-tail
                else:
                    damping=powers[0]-tail
                total-=damping/powers[2*k]*number(coefficient)
        return total.value,total.slope,radius

    def check(self,dr,j,limits,budget,admission_kinetic=None):
        r2=sum(x*x for x in dr)
        if r2<spec.R_MIN2:
            raise Invalid("stored radius below r_min")
        for x,value in zip(dr,j):
            if x==0 and value!=0:
                raise Invalid("zero displacement component has nonzero J")
        bits=limits.start_bits
        while bits<=limits.max_bits:
            budget.evaluate(bits)
            potential,derivative,radius=self.evaluate(r2,bits)
            low,high=endpoints(-derivative/radius)
            undecided=False
            for x,value in zip(dr,j):
                if x==0:
                    continue
                multiplier=x*spec.HALF*(1<<80)
                a,b=sorted((low*multiplier,high*multiplier))
                left,right=Q(2*value-1,2),Q(2*value+1,2)
                if b<left or a>right or (value&1 and (b==left or a==right)):
                    raise Invalid("J enclosure disjoint from claimed rounding cell")
                if a<left or b>right or (value&1 and (a==left or b==right)):
                    undecided=True
            if admission_kinetic is not None:
                a,b=endpoints(potential)
                if a+admission_kinetic>10*spec.DE:
                    raise Invalid("initial relative energy exceeds 10 De")
                undecided |= b+admission_kinetic>10*spec.DE
            if not undecided:
                return
            bits*=2
        raise Refused("precision cap cannot decide enclosure/rounding")
