"""Select narrow AO classes using existing errors, never reference energies."""
import argparse
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

import numpy as np
from pyscf import ao2mo, gto
from electronic_pilot.numerical_cause.core import ao_data, coordinates, digest, symmetry
from electronic_pilot.solver import singlet_matrix


def permutations(t):
    i,j,k,l=map(int,t)
    return sorted({(a,b,c,d) for a,b in ((i,j),(j,i)) for c,d in ((k,l),(l,k))} |
                  {(c,d,a,b) for a,b in ((i,j),(j,i)) for c,d in ((k,l),(l,k))})


def canonical(t):
    i,j=sorted(t[:2],reverse=True); k,l=sorted(t[2:],reverse=True)
    return (i,j,k,l) if i*(i+1)//2+j>=k*(k+1)//2+l else (k,l,i,j)


def orbitals(mol):
    result=[]
    for sh in range(mol.nbas):
        angular=mol.bas_angular(sh)
        # Shared AO representation, not an integral calculation. 'None'
        # includes the Y00 and Y1m prefactors used with libcint radial norms.
        angular_map=gto.cart2sph(angular)
        powers=[(x,y,angular-x-y) for x in range(angular,-1,-1) for y in range(angular-x,-1,-1)]
        coeff=mol._libcint_ctr_coeff(sh)
        for ctr in range(mol.bas_nctr(sh)):
            for m in range(2*angular+1):
                result.append(dict(shell=sh,l=angular,center=mol.atom_coord(mol.bas_atom(sh)).tolist(),
                    exponents=mol.bas_exp(sh).tolist(),radial=coeff[:,ctr].tolist(),
                    polynomial=[dict(powers=p,coefficient=float(angular_map[q,m])) for q,p in enumerate(powers) if angular_map[q,m]!=0]))
    return result


def select(r,target):
    started=time.perf_counter()
    mol,s,h,g=ao_data('cc-pVQZ',r)
    c=coordinates(s,h,'cholesky')
    gm=ao2mo.kernel(g,c,compact=False).reshape(g.shape)
    mat,ii,jj,_=singlet_matrix(c.T@h@c,gm)
    a,b=np.unravel_index(abs(mat-mat.T).argmax(),mat.shape)
    i,j,k,l=map(int,(ii[a],jj[a],ii[b],jj[b]))
    norm=np.sqrt(2*(1+(i==j)))*np.sqrt(2*(1+(k==l)))
    right=[np.outer(c[:,u],c[:,v]) for u,v in ((j,l),(j,k),(i,l),(i,k))]
    maximum=-1.; chosen=None
    total=0.
    for p in range(len(s)):
        for q in range(len(s)):
            left=[c[p,u]*c[q,v] for u,v in ((i,k),(i,l),(j,k),(j,l))]
            weight=sum(x*y for x,y in zip(left,right))/norm
            term=weight*(g[p,q]-g[q,p].T)
            total+=float(term.sum())
            idx=np.unravel_index(abs(term).argmax(),term.shape)
            if abs(term[idx])>maximum:
                maximum=float(abs(term[idx])); chosen=(p,q,int(idx[0]),int(idx[1]))
    def weight(t):
        p,q,u,v=t
        return sum(c[p,x]*c[q,y]*c[u,z]*c[v,w] for x,y,z,w in ((i,k,j,l),(i,l,j,k),(j,k,i,l),(j,l,i,k)))/norm
    cls=permutations(chosen)
    contribution=sum(weight(t)*(float(g[t])-float(g[t[1],t[0],t[3],t[2]])) for t in cls)
    sa,sb=np.unravel_index(abs(s-s.T).argmax(),s.shape)
    row=dict(R_bohr=r,worst_coupling=dict(row=int(a),col=int(b),pair_a=[i,j],pair_b=[k,l],asymmetry=float(mat[a,b]-mat[b,a])),
             ERI_class=dict(canonical=canonical(chosen),largest_term=chosen,largest_term_abs=maximum,selected_class_signed_contribution=contribution,
                 raw_values=[dict(indices=t,value=float(g[t]),weight=weight(t)) for t in cls]),
             S_class=dict(indices=[int(sa),int(sb)],values=[float(s[sa,sb]),float(s[sb,sa])]),
             AO_symmetry=symmetry(g),AO_S_asymmetry=float(abs(s-s.T).max()),AO_h_asymmetry=float(abs(h-h.T).max()),
             binary64_AO_eri_propagation=total,AO_sha256={'s':digest(s),'h':digest(h),'eri':digest(g)},
             orbitals=orbitals(mol),labels=mol.ao_labels(),wall_seconds=time.perf_counter()-started,
             peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    np.savez_compressed(target/f'R_{r:g}.npz',s=s,h=h,eri=g,c=c)
    row['artifact_sha256']=hashlib.sha256((target/f'R_{r:g}.npz').read_bytes()).hexdigest()
    (target/f'R_{r:g}.json').write_text(json.dumps(row,indent=2)+'\n')
    print(r,'pair',row['worst_coupling'],'ERI class',row['ERI_class']['canonical'],'contribution',contribution,flush=True)
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    target=Path(args.output); target.mkdir(parents=True,exist_ok=False)
    protocol=Path(__file__).with_name('protocol.json')
    sources={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path(__file__).parent.glob('*') if x.is_file()}
    protected={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path('electronic_pilot').rglob('*') if x.is_file() and '__pycache__' not in x.parts and 'ao_micro_v0' not in x.parts}
    for folder in ('docs/active/h2_static_pilot_v2','docs/active/h2_numerical_cause_v1'):
        protected.update({str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in Path(folder).iterdir() if x.is_file()})
    seal=dict(protocol=json.loads(protocol.read_text()),sources=sources,protected=protected,git=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        packages=subprocess.check_output([__import__('sys').executable,'-m','pip','freeze'],text=True))
    (target/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    rows=[];started=time.perf_counter()
    for r in seal['protocol']['R_bohr']:
        # Selection only, no energy accepted or evaluated.
        rows.append(select(r,target))
        (target/'results.json').write_text(json.dumps(dict(rows=rows,wall_seconds=time.perf_counter()-started),indent=2)+'\n')

if __name__=='__main__': main()
