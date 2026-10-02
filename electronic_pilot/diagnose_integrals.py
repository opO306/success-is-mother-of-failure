"""Arithmetic diagnostic; does not accept a failed solver point."""
import json
import numpy as np
from scipy.linalg import eigh, cholesky, solve_triangular
from pyscf import gto, ao2mo, lib
from electronic_pilot.solver import singlet_matrix

lib.num_threads(1)
for basis in ("cc-pVTZ", "cc-pVQZ"):
    mol = gto.M(atom=[("H",(0,0,-0.2)),("H",(0,0,0.2))],basis=basis,unit="Bohr",verbose=0)
    s=mol.intor("int1e_ovlp")
    w,u=eigh(s)
    for label,c in (("symmetric",u@np.diag(w**-0.5)@u.T),
                    ("canonical",u@np.diag(w**-0.5)),
                    ("cholesky",solve_triangular(cholesky(s,lower=True).T,np.eye(len(s)),lower=False))):
        h=c.T@(mol.intor("int1e_kin")+mol.intor("int1e_nuc"))@c
        e=ao2mo.kernel(mol,c,compact=False).reshape((len(c),)*4)
        mat,*_=singlet_matrix(h,e)
        print(json.dumps(dict(basis=basis,transform=label,Smin=float(w[0]),Scond=float(w[-1]/w[0]),
                              orth=float(np.linalg.norm(c.T@s@c-np.eye(len(c)),ord=2)),
                              h_asym=float(np.max(abs(h-h.T))),max_matrix=float(np.max(abs(mat))),
                              matrix_asym=float(np.max(abs(mat-mat.T))))),flush=True)
