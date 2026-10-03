"""Separately sealed post-acquisition alignment and independent AO spots."""
from pathlib import Path
import json,struct,time
import numpy as np
import mpmath as mp
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from electronic_pilot.ao_micro_v0.gaussian import overlap,eri


def orbitals(definition):
    result=[]
    for sh in definition['actual_shells']:
        l=sh['l'];powers=[(x,y,l-x-y) for x in range(l,-1,-1) for y in range(l-x,-1,-1)]
        p=np.array(sh['polynomial_map']);rad=np.array(sh['radial'])
        for ctr in range(sh['nctr']):
            for m in range(2*l+1):
                result.append(dict(center=sh['center'],exponents=sh['exponents'],radial=rad[:,ctr].tolist(),
                         polynomial=[dict(powers=powers[q],coefficient=float(p[q,m])) for q in range(len(p)) if p[q,m]!=0]))
    return result


def quadruple(data,index):
    low,high=map(int,data[index]);bits=low+(high<<64);sign=-1 if bits>>127 else 1
    exponent=(bits>>112)&32767;fraction=bits&((1<<112)-1)
    if exponent==32767:raise ValueError('nonfinite quad')
    significand=fraction if exponent==0 else fraction+(1<<112)
    return sign*mp.mpf(significand)*mp.power(2,(1 if exponent==0 else exponent)-16383-112)


def manifest(definition):
    def numeric(a):
        if isinstance(a,float):return dict(decimal_roundtrip=repr(a),hex=a.hex(),exact_integer_ratio=list(a.as_integer_ratio()))
        if isinstance(a,list):return [numeric(x) for x in a]
        if isinstance(a,dict):return {k:numeric(x) for k,x in a.items()}
        return a
    return dict(definition=definition,binary64_interpretation=numeric(definition),AO_mapping='identity between arm spherical coefficient vectors; Libint Cartesian-to-spherical P explicitly recorded',
                same_space='actual input definition and exact contraction-span/rank evidence, not basis name or AO count alone',
                normalization='stored independently verified radial coefficients and actual real spherical polynomials define the reproduction basis; higher-precision recomputation does not renormalize or change the span')


def main():
    root=Path('runs/h2_reconstruction_v0/run_io_v1');out=Path('runs/h2_reconstruction_v0/post_v0');out.mkdir(exist_ok=False)
    definition_path=Path('docs/active/h2_adversarial_v0/evidence/basis_definitions.json');definition=read(definition_path)['records']['cc-pVQZ']
    paths=[Path(__file__),Path('electronic_pilot/ao_micro_v0/gaussian.py'),definition_path,Path('electronic_pilot/reconstruction_v0/execution.json')]
    paths.extend(p for arm in ('L','I') for p in (root/arm/'c.npy',root/arm/'s.npy',root/arm/'113/g_high.bin',root/arm/'result.json',root/arm/'raw_s.npy',root/arm/'raw_g.npy'))
    bindings={str(p):sha(p) for p in paths};write(out/'seal.json',dict(bindings=bindings,selected_common_MO_indices=[[0,0,0,0],[50,50,39,50],[59,59,59,59],[23,23,53,53]],no_unaligned_MO_subtraction=True,AO_spots=read('electronic_pilot/reconstruction_v0/execution.json')['AO_spots']))
    write(out/'input_manifest.json',manifest(definition))
    mp.mp.dps=100
    CL=mp.matrix(np.load(root/'L/c.npy').tolist());CI=mp.matrix(np.load(root/'I/c.npy').tolist());U=CL**-1*CI
    mapping_res=max(abs(x) for x in CL*U-CI);SL=mp.matrix(np.load(root/'L/s.npy').tolist());SI=mp.matrix(np.load(root/'I/s.npy').tolist())
    residual=CI.T*(SL-SI)*CI
    write(out/'alignment.json',dict(C_L_U_equals_C_I_max=str(mapping_res),arithmetic_decimal_digits=100,
           U_nonzero_count=sum(x!=0 for x in U),metric_difference_Frobenius=str(mp.sqrt(mp.fsum(x*x for x in residual))),
           raw_S_difference_sha256=[sha(root/a/'raw_s.npy') for a in ('L','I')],
           S_difference_not_hidden=True,interpretation='Common orbital functions C_I; U is a coefficient transformation, not assumed unitary when numerical S differs',
           verified_mapping_scope='numerical high-precision correspondence of stored dyadic C; no formal floating-point enclosure'))
    GL=np.memmap(root/'L/113/g_high.bin',dtype='<u8',mode='r',shape=(60,60,60,60,2));GI=np.memmap(root/'I/113/g_high.bin',dtype='<u8',mode='r',shape=(60,60,60,60,2))
    selected=[];started=time.perf_counter()
    for idx in ((0,0,0,0),(50,50,39,50),(59,59,59,59),(23,23,53,53)):
        columns=[[(i,U[i,j]) for i in range(60) if U[i,j]!=0] for j in idx];value=mp.mpf(0)
        for i,a in columns[0]:
            for j,b in columns[1]:
                for k,c in columns[2]:
                    for l,d in columns[3]:value+=a*b*c*d*quadruple(GL,(i,j,k,l))
        other=quadruple(GI,idx);selected.append(dict(index=idx,L_in_C_I=str(value),I_in_C_I=str(other),L_minus_I=str(value-other)))
    write(out/'common_MO_selected.json',dict(elements=selected,selected_max_abs=str(max(abs(mp.mpf(x['L_minus_I'])) for x in selected)),
           full_tensor_maximum=None,full_tensor_comparison_performed=False,precision_bits_of_saved_MO=113,alignment_decimal_digits=100,runtime_seconds=time.perf_counter()-started,
           uncertainty='empirical common-representation diagnostics; AO integral precision and unsampled tensor maximum unbounded'))
    orbs=orbitals(definition);schedule=read('electronic_pilot/reconstruction_v0/execution.json')['AO_spots'];spot=[]
    for kind,indices in schedule.items():
        for idx in indices:
            values=[]
            for digits in (60,80):
                with mp.workdps(digits):
                    function=overlap if kind=='overlap' else eri
                    # Every related ordered integral is independently evaluated.
                    permutations=[idx,list(reversed(idx))] if kind=='overlap' else [idx,[idx[2],idx[3],idx[0],idx[1]],[idx[1],idx[0],idx[2],idx[3]]]
                    values.append(dict(decimal_digits=digits,independent_values=[str(function(*(orbs[i] for i in p))) for p in permutations]))
            with mp.workdps(100):
                high=list(map(mp.mpf,values[-1]['independent_values']));low=list(map(mp.mpf,values[0]['independent_values']));change=max(abs(a-b) for a,b in zip(low,high))
                rawfile='raw_s.npy' if kind=='overlap' else 'raw_g.npy'
                errors={a:str(mp.mpf(float(np.load(root/a/rawfile,mmap_mode='r')[tuple(idx)]))-high[0]) for a in ('L','I')}
                spot.append(dict(kind=kind,index=idx,measurements=values,precision_60_80_max=str(change),independent_permutation_spread=str(max(high)-min(high)),AO_engine_signed_errors=errors,internal_convergence_pass=change<=mp.mpf('1e-45')))
    write(out/'AO_spots.json',dict(layer='3 AO integrals newly recomputed from dyadic Gaussian definition',spots=spot,full_AO_recalculated=False,
           scope='one overlap class and two ERI classes only; no full T/V/ERI high-precision engine or energy bound',
           primitive_radial_spherical_inputs_promoted_exactly=True,lost_binary64_integral_digits_not_restored_by_layer2=True,not_certified=True))
    if bindings!={p:sha(p) for p in bindings}:raise ValueError('post input/source drift')
    write(out/'postcheck.json',dict(unchanged=True,bindings=bindings))


if __name__=='__main__':main()
