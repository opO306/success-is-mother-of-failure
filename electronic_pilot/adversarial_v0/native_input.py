"""Exact actual AO definitions supplied to an independent native engine."""
import argparse
from pathlib import Path
import numpy as np
from electronic_pilot.frontend_reference_v0.audit import read,write,sha

def export(definitions,output):
    dest=Path(output);dest.mkdir(parents=True,exist_ok=False)
    row=read(definitions)['records']['cc-pVQZ'];shells=row['actual_shells']
    nc=sum(shell['nctr']*(shell['l']+1)*(shell['l']+2)//2 for shell in shells)
    mapping=np.zeros((nc,row['orbital_count']));ca=sa=0;lines=[str(sum(sh['nctr'] for sh in shells))]
    for sh in shells:
        poly=np.asarray(sh['polynomial_map']);rad=np.asarray(sh['radial']);ex=sh['exponents']
        for c in range(sh['nctr']):
            lines.append(' '.join(map(str,[sh['l'],len(ex),*sh['center']])))
            lines.extend(format(a,'.17g')+' '+format(float(co),'.17g') for a,co in zip(ex,rad[:,c]))
            mapping[ca:ca+len(poly),sa:sa+2*sh['l']+1]=poly;ca+=len(poly);sa+=2*sh['l']+1
    (dest/'shells.txt').write_text('\n'.join(lines)+'\n',encoding='ascii')
    np.save(dest/'cart_to_spherical.npy',mapping,allow_pickle=False)
    write(dest/'input_seal.json',dict(definitions_sha256=sha(definitions),shells_sha256=sha(dest/'shells.txt'),
        mapping_sha256=sha(dest/'cart_to_spherical.npy'),ncart=nc,nspherical=row['orbital_count'],
        shared='Actual basis coefficients and real spherical polynomial representation metadata; no integral values supplied',
        normalization='radial coefficients supplied; no angular/primitive normalization embedded by Libint',
        integral_engine='Libint2 2.7.2, independent of libcint'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--definitions',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();export(a.definitions,a.output)
