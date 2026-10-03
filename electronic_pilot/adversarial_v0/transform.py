"""Independent explicit four-index contraction; no PySCF AO2MO helpers."""
import numpy as np

def four(g,c):
    a=np.einsum('ap,abcd->pbcd',c,g,optimize=True)
    b=np.einsum('bq,pbcd->pqcd',c,a,optimize=True);del a
    a=np.einsum('cr,pqcd->pqrd',c,b,optimize=True);del b
    b=np.einsum('ds,pqrd->pqrs',c,a,optimize=True)
    return b

def diagnostic(a):
    output={}
    for name,other in [('ij',a.swapaxes(0,1)),('kl',a.swapaxes(2,3)),('pair',a.transpose(2,3,0,1))]:
        delta=abs(a-other);idx=np.unravel_index(int(delta.argmax()),a.shape)
        output[name]=dict(max_absolute=float(delta[idx]),index=list(map(int,idx)),value=float(a[idx]),counterpart=float(other[idx]))
    return output

def difference(a,b):
    delta=abs(a-b);idx=np.unravel_index(int(delta.argmax()),a.shape)
    return dict(max_absolute=float(delta[idx]),index=list(map(int,idx)),first=float(a[idx]),second=float(b[idx]),
                frobenius=float(np.linalg.norm(delta.ravel())))

def interaction(e00,e10,e01,e11):return e11-e10-e01+e00
