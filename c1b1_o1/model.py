"""Public Lang decimal specification, independently parsed and evaluated.

No force from the executor. No published binary64 underflow shortcuts either.
"""
import hashlib
import re
from pathlib import Path
import mpmath

SOURCE = Path('D:/reference/ar2_lang2024/S2_ar2_pot.f90')
MASS = '399623831237000000/5485799090441'
DE = '0.000451995775'

def parse(path=SOURCE):
    text = '\n'.join(line.split('!')[0] for line in path.read_text(encoding='utf-8').splitlines())
    text = re.sub(r'&\s*\n\s*', ' ', text)
    result = {}
    for match in re.finditer(r'real\(prec\),parameter\s*::\s*(\w+)(?:\([^)]*\))?\s*=\s*([^\n]+)', text):
        name, rhs = match.groups()
        result[name] = re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?(?=_prec)', rhs)
    required = {'alpha_BO':2,'a_BO':8,'C_BO':6,'eta_BO':1,
                'alpha_REL':2,'a_REL':6,'C_REL':3,'eta_REL':1,
                'alpha_QED':2,'a_QED':6,'C_QED':2,'eta_QED':1,'A':5,'B':6}
    for name,count in required.items():
        if len(result.get(name,[])) != count:
            raise ValueError('public parameter shape: '+name)
    return {name:result[name] for name in required}

class Potential:
    def __init__(self, params=None, ctx=None):
        self.ctx = ctx or mpmath.mp
        self.params = parse() if params is None else params
        self.p = {k:[self.ctx.mpf(v) for v in vs] for k,vs in self.params.items()}

    def __call__(self,r):
        c, p = self.ctx,self.p
        total = 0
        for name,imin,kmin,kadd in [('BO',-1,3,1),('REL',0,2,0),('QED',0,3,0)]:
            coeff = p['a_'+name]; count=len(coeff)//2
            for j,al in enumerate(p['alpha_'+name]):
                total += c.exp(-al*r)*sum(coeff[j*count+i]*r**(imin+i) for i in range(count))
            x=p['eta_'+name][0]*r
            for i,coef in enumerate(p['C_'+name]):
                k=kmin+i; n=2*k+kadd
                term=series=1
                for j in range(1,n+1):
                    term=term*x/j; series+=term
                damping=1-c.exp(-x)*series
                if i==0 and name=='BO':
                    numerator=1+sum(a*r**(j+1) for j,a in enumerate(p['A']))
                    denominator=1+sum(b*r**(j+1) for j,b in enumerate(p['B']))
                    damping+=numerator/denominator-1
                if i==0 and name=='REL':
                    damping-=1
                total -= coef*damping/r**(2*k)
        return total

    def source_hash(self):
        return hashlib.sha256(SOURCE.read_bytes()).hexdigest()
