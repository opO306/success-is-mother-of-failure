"""Guard and physical-state measurements; no energy constructor imports."""
from fractions import Fraction
from pathlib import Path
import numpy as np
import mpmath as mp
from electronic_pilot.adversarial_v0.symmetry import operators,spin_action


def retained_rank(c):
    n=len(c)
    triangular=np.count_nonzero(np.tril(c,-1))==0 or np.count_nonzero(np.triu(c,1))==0
    if c.shape!=(n,n) or not triangular or not np.isfinite(c).all() or not np.all(np.diag(c)!=0):
        raise ValueError('full retained rank not proved by triangular nonzero diagonal')
    return dict(actual_retained_rank=n,proof='exact dyadic triangular matrix with every diagonal nonzero',deleted_columns=0)


def exact_guard(s,c,threshold=1e-10):
    try:
        from gmpy2 import mpq as rational
    except ImportError:
        rational=Fraction
    n=len(s);S=[[rational(float(x)) for x in row] for row in s];C=[[rational(float(x)) for x in row] for row in c]
    SC=[[sum(S[i][k]*C[k][j] for k in range(n)) for j in range(n)] for i in range(n)]
    R=[[sum(C[k][i]*SC[k][j] for k in range(n))-(i==j) for j in range(n)] for i in range(n)]
    upper_sq=sum(x*x for row in R for x in row)
    lower_sq=max(sum(R[i][j]**2 for i in range(n)) for j in range(n))
    t=rational(float(threshold));status='PASS' if upper_sq<=t*t else ('FAIL' if lower_sq>t*t else 'UNRESOLVED')
    mp.mp.dps=80
    def to_mp(x):
        num,den=x.as_integer_ratio() if hasattr(x,'as_integer_ratio') else (x.numerator,x.denominator)
        return mp.mpf(int(num))/int(den)
    roots=[]
    for dps in (80,100):
        with mp.workdps(dps):roots.append(dict(decimal_digits=dps,Frobenius_upper=str(mp.sqrt(to_mp(upper_sq))),column_lower=str(mp.sqrt(to_mp(lower_sq)))))
    return dict(status=status,norm='absolute operator 2-norm, no relative normalization',root_measurements=roots,
                exact_Frobenius_upper_squared=str(upper_sq),exact_column_l2_lower_squared=str(lower_sq),
                exact_threshold_squared=str(t*t),Frobenius_upper=str(mp.sqrt(to_mp(upper_sq))),
                column_l2_lower=str(mp.sqrt(to_mp(lower_sq))),arithmetic='exact rational on unchanged binary64 inputs')


def own_c(s):
    values=[];previous=None
    for dps in (60,80):
        with mp.workdps(dps):
            S=mp.matrix(s.tolist());L=mp.cholesky(S);C=(L**-1).T
            shift=None if previous is None else max(abs(C[i,j]-previous[i,j]) for i in range(len(s)) for j in range(len(s)))
            values.append(dict(decimal_digits=dps,change_max_abs=None if shift is None else str(shift)))
            previous=C.copy()
    if mp.mpf(values[-1]['change_max_abs'])>mp.mpf('1e-45'):raise ValueError('own C precision convergence failed')
    c=np.array([[float(previous[i,j]) for j in range(len(s))] for i in range(len(s))])
    return c,values


def state_symmetry(s,c,vector,definition):
    J,G,F=operators(definition);n=len(s);order=list(zip(*np.triu_indices(n)));result=[]
    for dps in (80,100):
        with mp.workdps(dps):
            C=mp.matrix(c.tolist());S=mp.matrix(s.tolist());V=mp.zeros(n)
            for amplitude,(i,j) in zip(vector,order):
                x=amplitude if isinstance(amplitude,mp.mpf) else mp.mpf(str(amplitude))
                if i==j:V[int(i),int(j)]=x
                else:V[int(i),int(j)]=V[int(j),int(i)]=x/mp.sqrt(2)
            W=C*V*C.T
            def norm(a):
                b=S*a.T*S;x=mp.fsum(b[i,j]*a[j,i] for i in range(n) for j in range(n))
                if x<0:raise ValueError('negative S metric square')
                return mp.sqrt(x)
            j,g,f=map(lambda a:mp.matrix(a.tolist()),(J,G,F))
            metrics=dict(inversion=norm(j.T*W*j-W),reflection=norm(f.T*W*f-W),Sigma_generator=norm(g.T*W+W*g),exchange=norm(W.T-W))
            for denominator in (7,5,2):
                D=mp.eye(n);angle=mp.pi/denominator
                for i in range(n):
                    for k in range(i+1,n):
                        if G[i,k]:
                            m=abs(int(G[i,k]));D[i,i]=D[k,k]=mp.cos(m*angle);D[i,k]=mp.sign(G[i,k])*mp.sin(m*angle);D[k,i]=-D[i,k]
                metrics['rotation_pi_over_'+str(denominator)]=norm(D.T*W*D-W)
            result.append(dict(decimal_digits=dps,residuals={k:str(x) for k,x in metrics.items()},state_norm=str(norm(W))))
    spin={k:spin_action(np.array([float(x) for x in vector]),order,k=='raising') for k in ('raising','lowering')};spin['Sz']=0
    guards={k:('PASS' if mp.mpf(x)<=mp.mpf(float(1e-10)) else 'FAIL') for k,x in result[-1]['residuals'].items()}
    guards.update({k:('PASS' if x<=1e-10 else 'FAIL') for k,x in spin.items()})
    return dict(measurements=result,spin=spin,guards=guards,precision='remeasurement of numerical S/C/v; not higher-accuracy AO',rigorous_enclosure=False)
