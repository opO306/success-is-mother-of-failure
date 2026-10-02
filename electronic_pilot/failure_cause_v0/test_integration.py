"""WSL-only independent determinant-action check; no Windows skip."""
import numpy as np
from pyscf import ao2mo
from .same_basis import run_reference


def test_determinant_action_vs_direct_pair_on_full_small_singlet():
    n=3;s=np.eye(n);c=np.eye(n);h=np.diag([-1.,-.2,.5])
    a=np.array([[.7,.1,.2],[.1,.4,-.1],[.2,-.1,.6]])
    g=np.einsum('ij,kl->ijkl',a,a)*.3
    g8=ao2mo.restore(8,g,n)
    guard=dict(H_asym_max=1e-10,eigen_l2_max=1e-9,norm_max=1e-10)
    energies=[]
    for path in ('frozen_C_and_compact_transform','generalized_h_C_and_four_leg_numpy_transform'):
        row,_,_=run_reference(s,h,g8,c,path,guard)
        assert row['failure_stage'] is None
        assert max(row['determinant_vs_pair_action_l2'])<1e-13
        assert row['eigen_residual']<1e-13
        assert abs(row['wavefunction_spin_square'])<1e-13
        energies.append(row['energy'])
    assert abs(energies[0]-energies[1])<1e-13
