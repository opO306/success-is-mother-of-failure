"""State-specific upstream influence; not an error bound or a new ground energy."""
from pathlib import Path
import time
import numpy as np
import mpmath as mp
from electronic_pilot.frontend_reference_v0.audit import read,write,sha


def main():
    root=Path('runs/h2_reconstruction_v0/run_io_v2');out=Path('runs/h2_reconstruction_v0/influence_v0');out.mkdir(exist_ok=False)
    files=[Path(__file__),root/'L/c.npy',root/'L/refine_1/output/vector.txt',root/'L/result.json',root/'I/result.json']
    files.extend(root/a/'fixed_input'/name for a in ('L','I') for name in ('h_canonical.bin','g_canonical.bin'))
    files.extend(root/a/'s.npy' for a in ('L','I'))
    binding={str(p):sha(p) for p in files};write(out/'seal.json',dict(bindings=binding,scope='fixed L physical AO wavefunction, overlap/one-body/ERI engine variations; no eigensolver, no accepted energy generated',precision='100-digit W construction then 64-bit significand long double propagation',selected_terms='largest 16 absolute weighted AO ERI differences, diagnostic selection only; no canonical rule change'))
    mp.mp.dps=100;n=60
    C=mp.matrix(np.load(root/'L/c.npy').tolist());vector=list(map(mp.mpf,(root/'L/refine_1/output/vector.txt').read_text().splitlines()));V=mp.zeros(n)
    for amplitude,(i,j) in zip(vector,zip(*np.triu_indices(n))):
        if i==j:V[int(i),int(j)]=amplitude
        else:V[int(i),int(j)]=V[int(j),int(i)]=amplitude/mp.sqrt(2)
    Wmp=C*V*C.T;W=np.array([[str(Wmp[i,j]) for j in range(n)] for i in range(n)],dtype=np.longdouble)
    S=[np.load(root/a/'s.npy').astype(np.longdouble) for a in ('L','I')];h=[np.fromfile(root/a/'fixed_input/h_canonical.bin',dtype='<f8').reshape(n,n).astype(np.longdouble) for a in ('L','I')]
    ds=S[1]-S[0];dh=h[1]-h[0]
    def bilinear(a,b):return np.sum((W.T@a@W)*b.T,dtype=np.longdouble)
    norm=bilinear(S[0],S[0]);dnorm=2*bilinear(ds,S[0])+bilinear(ds,ds)
    e1_h=2*bilinear(dh,S[0]);e1_s=2*bilinear(h[0],ds);cross=2*bilinear(dh,ds)
    g=[np.memmap(root/a/'fixed_input/g_canonical.bin',dtype='<f8',mode='r',shape=(n,)*4) for a in ('L','I')]
    dg=np.subtract(g[1],g[0],dtype=np.longdouble);weights=np.einsum('ab,cd->acbd',W,W);terms=weights*dg
    e2=np.sum(terms,dtype=np.longdouble);indices=np.argpartition(abs(terms).ravel(),-16)[-16:];selected=[]
    for flat in sorted(indices,key=lambda i:abs(terms.ravel()[i]),reverse=True):
        idx=np.unravel_index(int(flat),terms.shape);selected.append(dict(index=list(map(int,idx)),L=float(g[0][idx]),I=float(g[1][idx]),AO_delta=str(dg[idx]),weight=str(weights[idx]),signed_weighted_contribution=str(terms[idx])))
    EL=np.longdouble(read(root/'L/result.json')['diagnostic_electronic_energy']);EI=np.longdouble(read(root/'I/result.json')['diagnostic_electronic_energy'])
    fixed_shift=(e1_h+e1_s+cross+e2-EL*dnorm)/(norm+dnorm)
    write(out/'influence.json',dict(norm_L=str(norm),normalization_change=str(dnorm),h_integral_signed_effect=str(e1_h/norm),S_in_one_body_signed_effect=str(e1_s/norm),h_S_cross_effect=str(cross/norm),
       ERI_signed_effect=str(e2/norm),overlap_denominator_signed_effect=str(-EL*dnorm/norm),fixed_L_state_I_minus_L_Rayleigh_shift=str(fixed_shift),
       actual_ground_I_minus_L=str(EI-EL),actual_minus_fixed_state_shift=str((EI-EL)-fixed_shift),largest_16_weighted_AO_ERI_differences=selected,
       shared_data='fresh canonical AO fields and actual L reconstructed vector',alignment='same unchanged AO coordinates, no unaligned MO subtraction',
       first_meaningful_layer='AO engine/mapping variation has a measurable state-weighted energy effect after downstream 113-bit convergence; which AO implementation is more accurate is unresolved',
       measurement_uncertainty='no rigorous summation enclosure or full AO integral accuracy bound; state-specific empirical perturbation, not a ground-state error bound',
       error_cancellation_not_excluded=True,additional_eigensolver_calls=0,new_accepted_energies=0))
    if binding!={p:sha(p) for p in binding}:raise ValueError('influence inputs drift')
    write(out/'postcheck.json',dict(unchanged=True,bindings=binding))


if __name__=='__main__':main()
