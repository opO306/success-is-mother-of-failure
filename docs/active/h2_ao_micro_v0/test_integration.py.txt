"""Real basis checks; run in existing WSL PySCF environment."""
import itertools
import mpmath as mp
import numpy as np
from pyscf import ao2mo
from scipy.linalg import eigh
from electronic_pilot.numerical_cause.core import ao_data,coordinates
from electronic_pilot.solver import singlet_matrix
from .gaussian import overlap,eri
from .prepare import orbitals,canonical,permutations
from .reuse import canonical_ao,one_electron_unique,transform


def test_high_precision_spherical_spots_all_angular_momenta():
    mol,s,h,g=ao_data('cc-pVQZ',1.)
    orbs=orbitals(mol)
    with mp.workdps(60):
        for a,b in ((1,1),(6,42),(14,55),(15,56),(29,29)):
            assert abs(float(overlap(orbs[a],orbs[b]))-s[a,b])<2e-14
        for indices in ((2,1,2,1),(6,6,1,1),(14,14,1,1),(29,29,1,1)):
            actual=float(eri(*(orbs[i] for i in indices)))
            assert abs(actual-g[indices])<2e-14


def test_canonical_permutation_and_packed_values():
    for t in ((5,1,3,2),(2,1,2,1),(1,1,1,1)):
        assert all(canonical(x)==canonical(t) for x in permutations(t))
    mol,s,h,g=ao_data('cc-pVDZ',1.4)
    ss,hh,g8=canonical_ao(mol); gg=ao2mo.restore(1,g8,len(s))
    assert np.array_equal(ss,ss.T) and np.array_equal(hh,hh.T)
    lower=np.tril_indices(len(s))
    assert np.array_equal(ss[lower],s[lower])
    assert np.array_equal(hh[lower],h[lower])
    for t in ((7,1,5,2),(2,1,2,1)):
        assert len({gg[x] for x in permutations(t)})==1
    assert abs(g-gg).max()<1e-14


def test_transform_against_independent_direct_einsum():
    mol,*_=ao_data('cc-pVDZ',1.4);s,h,g8=canonical_ao(mol); c=coordinates(s,h,'cholesky')
    g=ao2mo.restore(1,g8,len(s))
    direct=np.einsum('pqrs,pi,qj,rk,sl->ijkl',g,c,c,c,c,optimize=True)
    packed=ao2mo.restore(1,ao2mo.incore.full(g8,c,compact=True),len(s))
    assert abs(direct-packed).max()<1e-12
    hm=one_electron_unique(h,c)
    assert abs(hm-c.T@h@c).max()<1e-13
    # Independent first-quantized singlet projection, not singlet_matrix.
    product=np.kron(hm,np.eye(len(s)))+np.kron(np.eye(len(s)),hm)+direct.transpose(0,2,1,3).reshape(len(s)**2,len(s)**2)
    pairs=list(itertools.combinations_with_replacement(range(len(s)),2))
    P=np.zeros((len(s)**2,len(pairs)))
    for col,(i,j) in enumerate(pairs):
        if i==j: P[i*len(s)+j,col]=1
        else: P[i*len(s)+j,col]=P[j*len(s)+i,col]=1/np.sqrt(2)
    independent=P.T@product@P
    matrix=singlet_matrix(hm,packed)[0]
    assert abs(independent-matrix).max()<1e-12
    assert abs(eigh(independent,eigvals_only=True)[0]-eigh(matrix,eigvals_only=True)[0])<1e-12


def test_real_DZ_two_representation_energy_equivalence():
    mol,*_=ao_data('cc-pVDZ',1.4);s,h,g8=canonical_ao(mol)
    guard=dict(Smin_floor=1e-10,orth_l2_max=1e-10,H_asym_max=1e-10,eigen_l2_max=1e-9,norm_max=1e-10)
    a,_=transform(mol,s,h,g8,'AO_reuse_only',guard,solve=True)
    b,_=transform(mol,s,h,g8,'AO_and_MO_integral_reuse',guard,solve=True)
    assert a['accepted'] and b['accepted']
    assert a['basis_size']==b['basis_size']==10
    assert a['singlet_dimension']==b['singlet_dimension']==55
    assert abs(a['total_energy_hartree']-b['total_energy_hartree'])<1e-12
