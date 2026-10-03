import json
import numpy as np
from electronic_pilot.ci_layer_audit_v0 import baseline,fermion
h=np.array([[1.,.125],[.125,2.]])
g=np.empty((2,)*4)
for p,q,r,s in np.ndindex(g.shape):
    a=sorted((p,q));b=sorted((r,s));g[p,q,r,s]=(1+2*a[0]+3*a[1]+5*b[0]+7*b[1])/32
states=[(0,0),(0,1),(1,1)];op=baseline.PriorAction(h,g)
unpacked,t,f=baseline.uncompressed_absorption(h,g)
result=[]
for ket in states:
    old=op([(ket,1)],states)
    for i,bra in enumerate(states):
        raw=fermion.value(h,g,bra,ket)
        before,_=fermion.e_product_element(unpacked,bra,ket)
        after,_=fermion.e_product_element(op.k,bra,ket)
        result.append(dict(bra=bra,ket=ket,raw=raw,old=float(old[i]),before=before,after=after))
print(json.dumps(dict(elements=result,trace=t.tolist(),f=f.tolist()),indent=2))
