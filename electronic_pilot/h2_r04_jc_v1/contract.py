"""Energy-blind selection and fixed campaign rules. No reference values."""
from fractions import Fraction

SIZES = {'SMALL': 3, 'MEDIUM': 5, 'LARGE': 7}
NMAX = (60, 80, 100, 120)
NDIGITS = (60, 80)
STABILITY = Fraction(1, 10**10)
OPT_STEPS = (Fraction(1,4), Fraction(1,8), Fraction(1,16))
OPT_SEED = Fraction(1)
OPT_BOUNDS = (Fraction(1,2), Fraction(3,2))
MAX_EVALUATIONS = 7
MAX_ROOT_RETRIES = 1

def basis(omega):
    if not isinstance(omega,int) or not 1 <= omega <= 9:
        raise ValueError('energy-blind enumeration restricted to Omega 1..9')
    result=[]
    for degree in range(omega+1):
        for n1 in range(degree+1):
            for n2 in range(degree-n1+1):
                for n3 in range(degree-n1-n2+1):
                    for n4 in range(degree-n1-n2-n3+1):
                        n5=degree-n1-n2-n3-n4
                        if (n2+n3)%2==0 and (n2>n3 or n2==n3 and n4>=n5):
                            result.append((n1,n2,n3,n4,n5))
    return result

def input_bytes(omega,u,nmax,ndigits,en):
    if omega not in SIZES.values() or not OPT_BOUNDS[0]<=Fraction(u)<=OPT_BOUNDS[1]:
        raise ValueError('outside sealed representation/parameter domain')
    if nmax not in NMAX or ndigits not in NDIGITS:
        raise ValueError('outside sealed numerical ladder')
    from electronic_pilot.h2_stored_root_v1.checker import decimal
    # Dyadic u is exactly representable in REAL*16. EN is only a hint.
    values=['1','1','1','1','0.4','-1','-1',str(omega),str(nmax),str(ndigits),
            decimal(Fraction(en),40),'0.0','0.0',decimal(Fraction(u),40),decimal(Fraction(u),40)]
    labels=['ZA','ZB','IAB','IE','R','RESTRICT1','RESTRICT2','OMEGA','NMAX','NDIGITS','EN','Y','X','U','W']
    return ''.join(f'{v}  {k}\n' for v,k in zip(values,labels)).encode('ascii')

def choose_numeric(energies):
    """All four NMAX and both precision points required, same u and Omega."""
    e={k:Fraction(v) for k,v in energies.items()}
    if abs(e['n120d80']-e['n120d60'])>STABILITY:
        raise ValueError('NDIGITS ladder not stable; no automatic extension')
    if abs(e['n100d60']-e['n120d60'])>STABILITY:
        raise ValueError('NMAX ladder not stable; no automatic extension')
    n=80 if abs(e['n80d60']-e['n100d60'])<=STABILITY else 100
    return n,60

def acceptance(row):
    """Require the actual branch and independent stored-problem checks."""
    o=row['observation']
    if not row['SPD']:
        return 'REFUSED_SPD'
    if not o['inverse_iteration_supported'] or o['maxit_exhausted']:
        return 'REFUSED_ITERATION'
    r=row['root']
    if r.get('inertia_low') is not None and r['inertia_low']>0:
        return 'NOT_GROUND_ROOT'
    if r['status']!='LOWEST_ROOT_ENCLOSED' or not r.get('E_inside'):
        return 'REFUSED_ROOT'
    required=('RQ_inside','RQ_cauchy','residual_intersects','rho_contained')
    if row['WA1_status']!='MATCH' or not all(row['consistency'].get(k,False) for k in required):
        return 'REFUSED_CONSISTENCY'
    return 'ACCEPTED_FINITE_STORED_PROBLEM'
