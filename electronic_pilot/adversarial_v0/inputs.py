"""Definition-only export. Basis construction does not call an AO integral."""
import argparse
import math
from pathlib import Path
import numpy as np
from electronic_pilot.frontend_reference_v0.audit import read,write,sha


def columns(basis):
    result=[]
    for shell in basis:
        l=shell[0]
        for col in range(1,len(shell[1])):
            result.append((l,tuple(sorted((float(row[0]).hex(),float(row[col]).hex())
                                         for row in shell[1:] if row[col]!=0))))
    return sorted(result)


def external_basis(data):
    result=[]
    for shell in data['elements']['1']['electron_shells']:
        if len(shell['angular_momentum'])!=1:raise ValueError('combined angular shell not supported')
        l=shell['angular_momentum'][0]
        result.append([l]+[[float(ex)]+[float(col[p]) for col in shell['coefficients']]
                           for p,ex in enumerate(shell['exponents'])])
    return result


def uncontract(basis):
    distinct=sorted({(shell[0],float(row[0])) for shell in basis for row in shell[1:]})
    return [[l,[ex,1.0]] for l,ex in distinct]


def radial(l,ex,coeff):
    ex=np.asarray(ex);coeff=np.asarray(coeff)
    primitive=np.sqrt(2*(2*ex)**(l+1.5)/math.gamma(l+1.5))
    overlap=(2*np.sqrt(ex[:,None]*ex[None,:])/(ex[:,None]+ex[None,:]))**(l+1.5)
    norm=np.sqrt(np.einsum('pi,pq,qi->i',coeff,overlap,coeff))
    return primitive[:,None]*coeff/norm


def export(output,sources):
    from pyscf import gto
    output=Path(output);output.mkdir(parents=True,exist_ok=False);sources=Path(sources)
    records={}
    for name in ('cc-pVDZ','cc-pVTZ','cc-pVQZ','cc-pV5Z'):
        ours=gto.basis.load(name,'H');data=read(sources/(name+'.json'));ext=external_basis(data)
        if columns(ours)!=columns(ext):
            write(output/(name+'_MISMATCH.json'),dict(ours=ours,external=ext))
            raise ValueError('BASIS_DEFINITION_MISMATCH '+name)
        records[name]=dict(raw_PySCF_H_basis=ours,external_source_sha256=sha(sources/(name+'.json')),
                          BSE_version=data['version'],columns_match_exact_binary64=True)
    original=records['cc-pVQZ']['raw_PySCF_H_basis']
    records['uncontracted-cc-pVQZ']=dict(raw_PySCF_H_basis=uncontract(original),
        definition='one normalized primitive per distinct (l,exponent); all contracted columns are in this span',
        original_primitive_occurrences=sum(len(s)-1 for s in original),no_exponent_threshold=True)
    from pyscf import lib
    lib.num_threads(1)
    for name,row in records.items():
        mol=gto.M(atom=[('H',(0,0,-.2)),('H',(0,0,.2))],basis={'H':row['raw_PySCF_H_basis']},
                  unit='Bohr',spin=0,charge=0,symmetry=False,cart=False,verbose=0)
        row.update(orbital_count=mol.nao_nr(),shell_count=mol.nbas,ao_labels=mol.ao_labels(),
                   nuclei=mol.atom_charges().tolist(),centers_bohr=mol.atom_coords().tolist(),
                   cart=False,ghost=False,actual_shells=[])
        for sh in range(mol.nbas):
            l=mol.bas_angular(sh);ex=mol.bas_exp(sh);co=mol.bas_ctr_coeff(sh)
            matches=[item for item in row['raw_PySCF_H_basis'] if item[0]==l
                     and np.array_equal(sorted([part[0] for part in item[1:]],reverse=True),ex)]
            if len(matches)!=1:raise ValueError('ambiguous raw shell normalization definition')
            raw_rows=sorted(matches[0][1:],key=lambda part:part[0],reverse=True)
            raw_co=np.asarray(raw_rows)[:,1:]
            expected=radial(l,ex,raw_co);actual=mol._libcint_ctr_coeff(sh)
            row['actual_shells'].append(dict(l=l,nctr=mol.bas_nctr(sh),center=mol.atom_coord(mol.bas_atom(sh)).tolist(),
                atom=mol.bas_atom(sh),exponents=ex.tolist(),raw_coefficients=co.tolist(),radial=actual.tolist(),
                normalization_max_relative=float(np.max(abs(expected-actual)/np.maximum(abs(actual),1e-300))),
                normalization_max_absolute=float(abs(expected-actual).max()),
                polynomial_map=gto.cart2sph(l).tolist()))
    write(output/'basis_definitions.json',dict(records=records,AO_calls=0,energy_calls=0,
          normalization_formula='sqrt(2*(2*a)^(l+3/2)/Gamma(l+3/2)); contracted self-overlap from analytic primitive overlaps',
          independence='BSE exponents/contraction columns and independent analytic radial formula; spherical polynomial map is explicitly shared PySCF representation metadata'))
    print('DEFINITIONS VERIFIED',[(name,row['orbital_count']) for name,row in records.items()],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--sources',required=True)
    a=p.parse_args();export(a.output,a.sources)
