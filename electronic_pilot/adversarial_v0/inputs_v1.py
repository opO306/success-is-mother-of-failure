"""Revised definition checker: distinguish columns from their exact span.

The initial strict-column checker and its refusal remain unchanged. This
revision precedes all new energy runs; no numerical tolerance is modified.
"""
import argparse
from fractions import Fraction
from pathlib import Path
import numpy as np
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from .inputs import columns,external_basis,uncontract,radial


def rank(rows):
    a=[[Fraction(x) for x in row] for row in rows]
    if not a:return 0
    pivot=0
    for col in range(len(a[0])):
        found=next((i for i in range(pivot,len(a)) if a[i][col]),None)
        if found is None:continue
        a[pivot],a[found]=a[found],a[pivot];value=a[pivot][col]
        a[pivot]=[x/value for x in a[pivot]]
        for i in range(len(a)):
            if i!=pivot:
                value=a[i][col];a[i]=[x-value*y for x,y in zip(a[i],a[pivot])]
        pivot+=1
        if pivot==len(a):break
    return pivot


def span(ours,external):
    result=[]
    for l in sorted({shell[0] for shell in ours+external}):
        exponents=sorted({Fraction(float(row[0])) for shell in ours+external if shell[0]==l for row in shell[1:]})
        def matrix(basis):
            vectors=[]
            for shell in basis:
                if shell[0]!=l:continue
                for col in range(1,len(shell[1])):
                    values={Fraction(float(row[0])):Fraction(float(row[col])) for row in shell[1:]}
                    vectors.append([values.get(ex,Fraction(0)) for ex in exponents])
            return [list(row) for row in zip(*vectors)]
        a=matrix(ours);b=matrix(external);joined=[x+y for x,y in zip(a,b)]
        ra,rb,rj=rank(a),rank(b),rank(joined)
        result.append(dict(l=l,primitive_exponents=[str(x) for x in exponents],ours_rank=ra,
                           external_rank=rb,union_rank=rj,equal_span=ra==rb==rj,
                           ours_coefficients=[[str(x) for x in row] for row in a],
                           external_coefficients=[[str(x) for x in row] for row in b]))
    return dict(equal_span=all(row['equal_span'] for row in result),per_angular=result,
                arithmetic='exact rational on stored binary64 exponent identities and coefficient dyadics; no cutoff')


def export(output,sources):
    from pyscf import gto,lib
    lib.num_threads(1)
    output=Path(output);output.mkdir(parents=True,exist_ok=False);sources=Path(sources);records={}
    for name in ('cc-pVDZ','cc-pVTZ','cc-pVQZ','cc-pV5Z'):
        ours=gto.basis.load(name,'H');data=read(sources/(name+'.json'));ext=external_basis(data)
        comparison=span(ours,ext)
        if not comparison['equal_span']:
            write(output/(name+'_SPAN_MISMATCH.json'),comparison);raise ValueError('basis span mismatch '+name)
        records[name]=dict(raw_PySCF_H_basis=ours,external_H_basis=ext,external_source_sha256=sha(sources/(name+'.json')),
            BSE_version=data['version'],columns_match_exact_binary64=columns(ours)==columns(ext),span=comparison)
    records['uncontracted-cc-pVQZ']=dict(raw_PySCF_H_basis=uncontract(records['cc-pVQZ']['raw_PySCF_H_basis']),
        definition='one primitive per distinct (l,exponent), coefficient 1; all original contracted functions in this span',
        no_exponent_threshold=True)
    for name,row in records.items():
        mol=gto.M(atom=[('H',(0,0,-.2)),('H',(0,0,.2))],basis={'H':row['raw_PySCF_H_basis']},unit='Bohr',
                  spin=0,charge=0,symmetry=False,cart=False,verbose=0)
        row.update(orbital_count=mol.nao_nr(),shell_count=mol.nbas,ao_labels=mol.ao_labels(),
                   nuclei=mol.atom_charges().tolist(),centers_bohr=mol.atom_coords().tolist(),cart=False,ghost=False,actual_shells=[])
        for sh in range(mol.nbas):
            l=mol.bas_angular(sh);ex=mol.bas_exp(sh);co=mol.bas_ctr_coeff(sh)
            matches=[item for item in row['raw_PySCF_H_basis'] if item[0]==l
                     and np.array_equal(sorted([part[0] for part in item[1:]],reverse=True),ex)]
            if len(matches)!=1:raise ValueError('ambiguous raw shell normalization definition')
            raw_rows=sorted(matches[0][1:],key=lambda part:part[0],reverse=True);raw_co=np.asarray(raw_rows)[:,1:]
            expected=radial(l,ex,raw_co);actual=mol._libcint_ctr_coeff(sh)
            row['actual_shells'].append(dict(l=l,nctr=mol.bas_nctr(sh),center=mol.atom_coord(mol.bas_atom(sh)).tolist(),
                atom=mol.bas_atom(sh),exponents=ex.tolist(),raw_coefficients=raw_co.tolist(),radial=actual.tolist(),
                normalization_max_relative=float(np.max(abs(expected-actual)/np.maximum(abs(actual),1e-300))),
                normalization_max_absolute=float(abs(expected-actual).max()),polynomial_map=gto.cart2sph(l).tolist()))
    write(output/'basis_definitions.json',dict(records=records,AO_calls=0,energy_calls=0,
        classification='BASIS_SPAN_EQUIVALENCE_SUPPORTED_UNDER_CHECKED_ASSUMPTIONS',
        initial_columns_refusal_preserved='runs/h2_adversarial_v0/definitions_v0/cc-pVDZ_MISMATCH.json',
        column_difference_not_mislabeled_span_mismatch=True,normalization_formula='independent Gamma radial primitive norm and analytic contracted self-overlap',
        independence='BSE vs exact coefficient-span proof and analytic normalization; shared real-spherical polynomial metadata'))
    print('DEFINITIONS VERIFIED',[(name,row['orbital_count']) for name,row in records.items()],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--sources',required=True)
    a=p.parse_args();export(a.output,a.sources)
