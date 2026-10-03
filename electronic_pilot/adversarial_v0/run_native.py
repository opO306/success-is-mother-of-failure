"""Native provenance acquisition and AO comparison, no electronic energies."""
from pathlib import Path
import subprocess,time
import numpy as np
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from .transform import four,diagnostic,difference

def main():
    from pyscf import gto,lib
    lib.num_threads(1);root=Path('runs/h2_adversarial_v0/libint_v0');deps=Path('/home/otherside123/h2-adversarial-v0/deps')
    executable=Path('/home/otherside123/h2-adversarial-v0/libint_driver')
    bindings={str(p):sha(p) for p in [executable,root/'shells.txt',root/'cart_to_spherical.npy',Path(__file__),
       Path('electronic_pilot/adversarial_v0/libint_driver.cpp'),Path('electronic_pilot/adversarial_v0/transform.py'),
       deps/'unpacked/usr/lib/x86_64-linux-gnu/libint2.so.2.0.4',*sorted(deps.glob('*.deb'))]}
    seal=root/'execution_seal.json'
    if seal.exists():raise ValueError('preserve native run')
    write(seal,dict(bindings=bindings,gcc=subprocess.check_output(['g++','--version'],text=True),
        linkage=subprocess.check_output(['ldd',str(executable)],text=True),engine='Libint2 2.7.2 Ubuntu binary, separate integral implementation',
        normalization_embedding=False,screening_precision=0,old_numeric_guards_unchanged=True))
    with (root/'native.log').open('w') as log:subprocess.run([str(executable),str(root/'shells.txt'),str(root)],stdout=log,stderr=subprocess.STDOUT,check=True)
    meta=read(root/'native.json');n=meta['ncart'];p=np.load(root/'cart_to_spherical.npy',allow_pickle=False)
    arrays={}
    for key in ('s','t','v'):
        cart=np.fromfile(root/(key+'_cart.bin'),dtype='<f8').reshape(n,n);arrays[key]=p.T@cart@p
        np.save(root/(key+'.npy'),arrays[key],allow_pickle=False)
    cart=np.fromfile(root/'eri_cart.bin',dtype='<f8').reshape((n,)*4)
    arrays['g']=four(cart,p);del cart;np.save(root/'g.npy',arrays['g'],allow_pickle=False)
    row=read('runs/h2_adversarial_v0/definitions_v1/basis_definitions.json')['records']['cc-pVQZ']
    mol=gto.M(atom=[('H',(0,0,-.2)),('H',(0,0,.2))],unit='Bohr',basis={'H':row['raw_PySCF_H_basis']},cart=False,spin=0,verbose=0)
    raw={key:mol.intor(op) for key,op in [('s','int1e_ovlp'),('t','int1e_kin'),('v','int1e_nuc')]}
    raw['g']=mol.intor('int2e',aosym='s1');comparison={key:difference(arrays[key],raw[key]) for key in arrays}
    for key in raw:np.save(root/('libcint_raw_'+key+'.npy'),raw[key],allow_pickle=False)
    write(root/'AO_comparison.json',dict(libint_vs_raw_libcint=comparison,
       libint_ERI_symmetry=diagnostic(arrays['g']),libcint_raw_ERI_symmetry=diagnostic(raw['g']),
       libint_one_body_asymmetry={k:float(abs(arrays[k]-arrays[k].T).max()) for k in ('s','t','v')},
       native=meta,shared_mapping='explicit real-spherical polynomial coefficients from verified PySCF basis metadata',
       distinct_integral_implementations=True,not_certified=True))
    assert bindings=={p:sha(p) for p in bindings}
    write(root/'postcheck.json',dict(unchanged=True,bindings=bindings))
    print('NATIVE AO',comparison,flush=True)

if __name__=='__main__':main()
