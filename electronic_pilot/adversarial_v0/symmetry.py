"""Independent physical symmetry action on the unchanged reproduced state.

All wavefunction differences use the AO S metric. MO label counting alone is
not a symmetry test. This is numerical evidence on saved dyadic C/S/v, not
high-precision evaluation of their underlying libcint integrals.
"""
import argparse
import math
from pathlib import Path
import numpy as np
import mpmath as mp
from electronic_pilot.frontend_reference_v0.audit import read,write,sha


def angular_generator(l):
    n=2*l+1;g=np.zeros((n,n));reflect=np.eye(n)
    if l==1:
        g[0,1]=-1;g[1,0]=1;reflect[1,1]=-1
    else:
        for m in range(1,l+1):
            g[l-m,l+m]=m;g[l+m,l-m]=-m;reflect[l-m,l-m]=-1
    return g,reflect


def coefficient_matrix(v,order,n):
    matrix=np.zeros((n,n))
    for amplitude,(i,j) in zip(v,order):
        if i==j:matrix[i,i]+=amplitude
        else:matrix[i,j]+=amplitude/math.sqrt(2);matrix[j,i]+=amplitude/math.sqrt(2)
    return matrix


def spin_action(v,order,raising):
    determinants={}
    for amp,(i,j) in zip(v,order):
        terms=[((2*i,2*i+1),amp)] if i==j else [((2*i,2*j+1),amp/math.sqrt(2)),((2*i+1,2*j),-amp/math.sqrt(2))]
        for occ,value in terms:determinants[occ]=determinants.get(occ,0)+value
    output={}
    for occ,amplitude in determinants.items():
        for q in occ:
            if q%2!=(1 if raising else 0):continue
            p=q-1 if raising else q+1;remaining=[x for x in occ if x!=q]
            if p in remaining:continue
            sign=(-1)**(sum(x<q for x in occ)+sum(x<p for x in remaining))
            key=tuple(sorted(remaining+[p]));output[key]=output.get(key,0)+sign*amplitude
    return math.sqrt(sum(value*value for value in output.values()))


def operators(definition):
    shells=definition['actual_shells'];n=definition['orbital_count']
    descriptors=[];G=np.zeros((n,n));F=np.eye(n);start=0
    for shell in shells:
        l=shell['l'];g,f=angular_generator(l)
        for ctr in range(shell['nctr']):
            size=2*l+1;G[start:start+size,start:start+size]=g;F[start:start+size,start:start+size]=f
            for m in range(size):descriptors.append((shell['atom'],l,ctr,tuple(shell['exponents']),m))
            start+=size
    J=np.zeros((n,n));lookup={key:i for i,key in enumerate(descriptors)}
    for i,(atom,l,ctr,ex,m) in enumerate(descriptors):J[i,lookup[(1-atom,l,ctr,ex,m)]]=(-1)**l
    return J,G,F


def inspect(definitions,original_npz,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    row=read(definitions)['records']['cc-pVQZ'];J,G,F=operators(row)
    base=Path('docs/active/h2_ground_state_audit_v0/evidence')
    vp=base/'v_direct_reproduced.npy';op=base/'direct_state_order.npy'
    v=np.load(vp,allow_pickle=False);order=np.load(op,allow_pickle=False)
    data=np.load(original_npz,allow_pickle=False);c=data['c'];s=data['s'];n=len(s)
    if n!=row['orbital_count'] or len(order)!=len(v):raise ValueError('saved-state dimension mismatch')
    V=coefficient_matrix(v,order,n);W=c@V@c.T;L=np.linalg.cholesky(s)
    def norm64(a):return float(np.linalg.norm(L.T@a@L))
    binary=dict(inversion_plus=norm64(J.T@W@J-W),reflection_plus=norm64(F.T@W@F-W),
                axial_generator=norm64(G.T@W+W@G),spatial_exchange_plus=norm64(W.T-W))
    mp.mp.dps=80
    C=mp.matrix(c.tolist());S=mp.matrix(s.tolist());Vhp=mp.zeros(n)
    for amplitude,(i,j) in zip(v,order):
        if i==j:Vhp[int(i),int(i)]+=mp.mpf(float(amplitude))
        else:
            value=mp.mpf(float(amplitude))/mp.sqrt(2);Vhp[int(i),int(j)]+=value;Vhp[int(j),int(i)]+=value
    Whp=C*Vhp*C.T
    def norm(a):
        left=S*a.T*S;value=mp.fsum(left[i,j]*a[j,i] for i in range(n) for j in range(n))
        if value<0:raise ValueError('negative S-metric norm square')
        return mp.sqrt(value)
    j=mp.matrix(J.tolist());g=mp.matrix(G.tolist());f=mp.matrix(F.tolist())
    results=dict(inversion_plus=norm(j.T*Whp*j-Whp),reflection_plus=norm(f.T*Whp*f-Whp),
                 axial_generator=norm(g.T*Whp+Whp*g),spatial_exchange_plus=norm(Whp.T-Whp))
    rotations={}
    for denominator in (7,5,2):
        angle=mp.pi/denominator;D=mp.eye(n)
        # Generator consists of disjoint sine/cosine 2x2 blocks.
        for i in range(n):
            for k in range(i+1,n):
                if G[i,k]:
                    m=abs(int(G[i,k]));D[i,i]=D[k,k]=mp.cos(m*angle)
                    D[i,k]=mp.sign(G[i,k])*mp.sin(m*angle);D[k,i]=-D[i,k]
        rotations['pi/'+str(denominator)]=str(norm(D.T*Whp*D-Whp))
    guard=read('electronic_pilot/ao_micro_v0/protocol.json')['guards']['norm_max']
    spin=dict(raising=spin_action(v,order,True),lowering=spin_action(v,order,False),Sz=0)
    passed=all(value<=guard for value in results.values()) and all(mp.mpf(value)<=guard for value in rotations.values()) and max(spin.values())<=guard
    write(output/'symmetry.json',dict(status='SUPPORTED UNDER CHECKED ASSUMPTIONS' if passed else 'UNRESOLVED_MEASUREMENT_OR_SYMMETRY_MISMATCH',
          claimed_irrep='1Sigma_g+' if passed else None,existing_norm_guard=guard,binary64_residuals=binary,
          high_precision_residuals={key:str(value) for key,value in results.items()},rotation_residuals=rotations,
          spin_action_norms=spin,normalization_S_metric=str(norm(Whp)),measurement_digits=80,
          high_precision_AO_integrals=False,vector_provenance='reproduced from sealed replay, unchanged',
          vector_sha256=sha(vp),order_sha256=sha(op),AO_artifact_sha256=sha(original_npz),
          independence='analytic angular/spin action, no CI builder/eigensolver; shares verified basis metadata and stored numerical C/S/v'))
    np.save(output/'inversion_AO.npy',J,allow_pickle=False);np.save(output/'axial_generator_AO.npy',G,allow_pickle=False)
    np.save(output/'reflection_AO.npy',F,allow_pickle=False)
    print('SYMMETRY',passed,{k:str(x) for k,x in results.items()},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--definitions',required=True);p.add_argument('--original-npz',required=True)
    p.add_argument('--output',required=True);a=p.parse_args();inspect(a.definitions,a.original_npz,a.output)
