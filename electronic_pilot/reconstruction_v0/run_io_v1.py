"""Fresh sealed two-arm reconstruction. Reference never enters constructors."""
from pathlib import Path
import argparse,subprocess,time,os,sys,resource,hashlib
import numpy as np
import mpmath as mp
from electronic_pilot.frontend_reference_v0.audit import read,write,sha,verify
from electronic_pilot.adversarial_v0.transform import four,diagnostic,difference
from electronic_pilot.adversarial_v0.native_input import export
from electronic_pilot.reconstruction_v0.measure import retained_rank,exact_guard,own_c,state_symmetry
from electronic_pilot.reconstruction_v0.policy import overall_status,compare_interval,classifications,signed_budget

MAIN=Path('/mnt/c/Users/zun24/성공은 실패의 어머니')
ROOT=Path.cwd()
OUT=ROOT/'runs/h2_reconstruction_v0/run_io_v1'
DEF=ROOT/'docs/active/h2_adversarial_v0/evidence/basis_definitions.json'


def array_sha(a):return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def canon_one(a):
    i,j=np.tril_indices(len(a));b=np.empty_like(a);b[i,j]=a[i,j];b[j,i]=a[i,j];return b


def canon_eri(a):
    n=len(a);pairs=list(zip(*np.tril_indices(n)));b=np.empty_like(a);packed=[]
    for p,(i,j) in enumerate(pairs):
        for k,l in pairs[:p+1]:
            value=a[i,j,k,l];packed.append(value)
            for u,v,w,x in ((i,j,k,l),(j,i,k,l),(i,j,l,k),(j,i,l,k),(k,l,i,j),(l,k,i,j),(k,l,j,i),(l,k,j,i)):
                b[u,v,w,x]=value
    return b,np.array(packed)


def precheck():
    seal=read(OUT/'execution_seal.json');verify(seal['bound_sha256'],ROOT,MAIN)
    old=np.load(MAIN/'runs/h2_qz44_sealed_v1/curve/R_0.4.npz');c=old['c'];s=old['s']
    rank=retained_rank(c);v=np.load(ROOT/'docs/active/h2_ground_state_audit_v0/evidence/v_direct_reproduced.npy')
    order=np.load(ROOT/'docs/active/h2_ground_state_audit_v0/evidence/direct_state_order.npy')
    H=np.load(ROOT/'runs/h2_ground_state_audit_v0/validation_v0/H_SC.npy',mmap_mode='r')
    if s.shape!=(60,60) or rank['actual_retained_rank']!=60 or v.shape!=(1830,) or H.shape!=(1830,1830) or not np.array_equal(order,np.array(list(zip(*np.triu_indices(60))))):raise ValueError('baseline retained space mismatch')
    definition=read(DEF)['records']['cc-pVQZ']
    if not definition['span']['equal_span'] or definition['orbital_count']!=60:raise ValueError('same basis span unavailable')
    write(OUT/'precheck.json',dict(status='PASS',baseline_actual=rank,actual_full_singlet_dimension=len(v),actual_H_shape=list(H.shape),actual_state_order='all upper-lex pairs',expected_AO=60,expected_singlet=1830,
          old_artifact_sha256=sha(MAIN/'runs/h2_qz44_sealed_v1/curve/R_0.4.npz'),basis_definition_sha256=sha(DEF),
          R_decimal_label='0.4',centers_binary64_hex=[float(-.2).hex(),float(.2).hex()],exact_center_separation=str(mp.mpf(float(.2))*2),old_nuclear_repulsion_binary64_hex=(1/.4).hex(),
          source_definition='BSE source strings plus exact-span comparison to actual PySCF definition; same supplied radial/polynomial dyadics for both engines'))
    write(OUT/'saved_guard.json',dict(layer='1 saved guard remeasurement only',exact=exact_guard(s,c),binary64=float(np.linalg.norm(c.T@s@c-np.eye(60),ord=2)),new_AO=False))
    return seal,definition


def compile_native():
    binary=Path('/home/otherside123/h2-reconstruction-io-v1/numeric');binary.parent.mkdir(exist_ok=False)
    command=['g++','-std=c++17','-O3','-fno-fast-math',str(ROOT/'electronic_pilot/reconstruction_v0/numeric_io_v1.cpp'),'-lquadmath','-o',str(binary)]
    with (OUT/'compile.log').open('x') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
    libint=Path('/home/otherside123/h2-adversarial-v0/libint_driver');lib=Path('/home/otherside123/h2-adversarial-v0/deps/unpacked/usr/lib/x86_64-linux-gnu/libint2.so.2.0.4')
    write(OUT/'runtime_seal.json',dict(binary=str(binary),binary_sha256=sha(binary),compile_command=command,gcc=subprocess.check_output(['g++','--version'],text=True),
          linkage=subprocess.check_output(['ldd',str(binary)],text=True),libint_executable_sha256=sha(libint),libint_library_sha256=sha(lib),
          numpy=np.__version__,actual_longdouble_significand_bits=np.finfo(np.longdouble).nmant+1,quad='GCC __float128 with quadmath, 113 significand bits, no fast math',threads=1))
    return binary,libint


def fresh_ao(arm,dest,definition,libint):
    from pyscf import gto,lib
    lib.num_threads(1);started=time.perf_counter()
    if arm=='L':
        mol=gto.M(atom=[('H',(0,0,-.2)),('H',(0,0,.2))],unit='Bohr',basis={'H':definition['raw_PySCF_H_basis']},cart=False,spin=0,symmetry=False,verbose=0)
        if mol.nao_nr()!=60 or mol.ao_labels()!=definition['ao_labels']:raise ValueError('fresh AO order mismatch')
        for sh,row in enumerate(definition['actual_shells']):
            if not np.array_equal(mol.bas_exp(sh),row['exponents']) or not np.array_equal(mol._libcint_ctr_coeff(sh),row['radial']):raise ValueError('fresh exponent/normalization mismatch')
        (dest/'mol_input.json').write_text(mol.dumps(),encoding='utf-8')
        data={key:mol.intor(op) for key,op in [('s','int1e_ovlp'),('t','int1e_kin'),('v','int1e_nuc')]};data['g']=mol.intor('int2e',aosym='s1')
        import pyscf
        engine=dict(name='PySCF/libcint',pyscf=pyscf.__version__,libcgto_path=gto.moleintor.libcgto._name,libcgto_sha256=sha(gto.moleintor.libcgto._name),arithmetic='binary64 double, 53 significand bits',screening='PySCF default integral engine settings; raw s1, no user screening override',linkage=subprocess.check_output(['ldd',gto.moleintor.libcgto._name],text=True))
    else:
        export(DEF,dest/'native');native=dest/'native'
        with (native/'native.log').open('x') as f:subprocess.run([str(libint),str(native/'shells.txt'),str(native)],stdout=f,stderr=subprocess.STDOUT,check=True)
        p=np.load(native/'cart_to_spherical.npy');nc=70
        data={key:p.T@np.fromfile(native/(key+'_cart.bin'),dtype='<f8').reshape(nc,nc)@p for key in ('s','t','v')}
        data['g']=four(np.fromfile(native/'eri_cart.bin',dtype='<f8').reshape((nc,)*4),p)
        engine=dict(name='Libint2',version='2.7.2 Ubuntu 2.7.2-1.1build1',arithmetic='double, binary64 53 significand bits',set_precision=0,screening='disabled by set_precision(0); no arithmetic precision promotion',normalization='embed OFF; standard Cartesian; externally supplied dyadic radial and spherical map',spherical_mapping='four binary64 explicit contractions of raw Cartesian integrals; arithmetic uncertainty remains',native=read(native/'native.json'),raw_input_hashes={q.name:sha(q) for q in (native/'shells.txt',native/'cart_to_spherical.npy')})
    for key,a in data.items():np.save(dest/('raw_'+key+'.npy'),a,allow_pickle=False)
    write(dest/'AO.json',dict(engine=engine,raw_one_body_asymmetry={k:float(abs(data[k]-data[k].T).max()) for k in ('s','t','v')},raw_ERI_symmetry=diagnostic(data['g']),raw_sha256={k:sha(dest/('raw_'+k+'.npy')) for k in data},runtime_seconds=time.perf_counter()-started,
          independent_permutations_before_reuse=True,independence='engine code differs; dyadic basis definition and verified spherical representation shared'))
    return data


def energy(H,guards):
    from scipy.linalg import eigh
    asym=float(abs(H-H.T).max())
    if asym>guards['H_asym_max'] or not np.isfinite(H).all():return dict(status='REFUSED',failure_stage='H_asym',energy=None),None,None
    w,q=np.linalg.eigh(H);other=eigh(H,subset_by_index=(0,1),driver='evr',eigvals_only=True)
    v=q[:,0];e=float(w[0]);res=float(np.linalg.norm(H@v-e*v));norm=float(abs(v@v-1))
    return dict(status='NUMERICAL_SOLVE_DIAGNOSTIC',electronic_energy=e,BO=e+2.5,eigen_residual_l2=res,vector_norm_error=norm,H_asym_max=asym,next_singlet_gap=float(w[1]-w[0]),full_roots=len(w),evr_lowest_two=other.tolist(),driver_difference=float(abs(other[0]-e)),lowest_root_evidence='hint-free complete syevd spectrum plus evr; numerical evidence, no formal root enclosure'),w,q


def arm_run(arm,definition,binary,libint,guards):
    start=time.perf_counter();dest=OUT/arm;dest.mkdir();data=fresh_ao(arm,dest,definition,libint)
    s=canon_one(data['s']);h=canon_one(data['t']+data['v']);g,g8=canon_eri(data['g']);del data['g']
    spectrum=np.linalg.eigvalsh(s);np.save(dest/'S_spectrum.npy',spectrum)
    c,c_precision=own_c(s);np.save(dest/'c.npy',c);np.save(dest/'s.npy',s);rank=retained_rank(c);guard=exact_guard(s,c)
    inp=dest/'fixed_input';inp.mkdir();g.tofile(inp/'g_canonical.bin');h.tofile(inp/'h_canonical.bin');c.tofile(inp/'c.bin')
    write(dest/'transform_input_seal.json',dict(bindings={str(p):sha(p) for p in inp.iterdir()},C_sha256=sha(dest/'c.npy'),AO_sha256=array_sha(g),own_S=True,C_generation=c_precision,orth_binary64=float(np.linalg.norm(c.T@s@c-np.eye(60),ord=2)),orth_exact=guard,
          Smin=float(spectrum[0]),condition=float(spectrum[-1]/spectrum[0]),retained=rank,canonical_ERI_symmetry=diagnostic(g),
          compact_and_direct_share_canonical_AO=True,canonical_zero_not_independent_validation=True))
    pre={'Smin':'PASS' if spectrum[0]>guards['Smin_floor'] else 'FAIL','orth':guard['status'],'rank':'PASS'}
    if 'FAIL' in pre.values() or 'UNRESOLVED' in pre.values():
        row=dict(arm=arm,status='REFUSED' if 'FAIL' in pre.values() else 'UNRESOLVED',pre_guards=pre,energy=None,failure_stage='orthogonalization',runtime_seconds=time.perf_counter()-start);write(dest/'result.json',row);return row
    from pyscf import ao2mo
    from electronic_pilot.solver import singlet_matrix
    compact=ao2mo.restore(1,ao2mo.incore.full(g8,c,compact=True),60);direct=four(g,c);hm=c.T@h@c
    pairs=[]
    for name,gm in [('compact',compact),('direct',direct)]:
        H=singlet_matrix(hm,gm)[0];asy=float(abs(H-H.T).max())
        pairs.append(dict(path=name,MO=diagnostic(gm),H_asym=asy,pre_guard='PASS' if asy<=guards['H_asym_max'] else 'FAIL',energy=None,eigensolver_called=False))
        np.save(dest/(name+'_53_g.npy'),gm)
    write(dest/'compact_direct_53.json',dict(paths=pairs,MO_difference=difference(compact,direct),same_AO=True,same_C=True,AO_compression_shared=True,unaligned_cross_arm_comparison=False))
    del compact,direct,gm,H,g,g8
    results=[];eig={}
    for bits in (64,113):
        target=dest/str(bits);target.mkdir()
        with (target/'native.log').open('x') as f:subprocess.run([str(binary),str(bits),str(inp),str(target),'60'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
        meta=read(target/'transform.json');H=np.fromfile(target/'singlet_matrix.bin',dtype='<f8').reshape(1830,1830)
        if mp.mpf(meta['H_asym_max'])>mp.mpf(float(guards['H_asym_max'])):
            r=dict(status='REFUSED',failure_stage='H_asym',energy=None);w=q=None
        else:
            from electronic_pilot.ground_state_audit_v0.operator import dense
            hm=np.fromfile(target/'one_body.bin',dtype='<f8').reshape(60,60);gm=np.fromfile(target/'g.bin',dtype='<f8').reshape((60,)*4)
            Hsc,states=dense(hm,gm);delta=float(abs(Hsc-H).max());sc_asy=float(abs(Hsc-Hsc.T).max())
            write(target/'independent_SC.json',dict(dimension=len(states),full_matrix_difference_max=delta,H_SC_asymmetry=sc_asy,
                 shared='same rounded high-precision MO; fermion action independent of native spatial pair assembler',threshold_source='existing H_asym guard used as additional CI agreement diagnostic'))
            if delta>guards['H_asym_max'] or sc_asy>guards['H_asym_max']:
                r=dict(status='REFUSED',failure_stage='independent_CI',energy=None);w=q=None
            else:r,w,q=energy(H,guards)
            del hm,gm,Hsc
        write(target/'eigensolve.json',r);results.append(dict(significand_bits=bits,transform=meta,eigensolve=r))
        if w is not None:eig[bits]=(w,q)
        print('ARM',arm,'BITS',bits,'H_asym',meta['H_asym_max'],'solve',r,flush=True)
    if 113 not in eig:
        row=dict(arm=arm,status='REFUSED',energy=None,pre_guards=pre,precision=results,failure_stage='H_asym');write(dest/'result.json',row);return row
    w,q=eig[113];refinements=[];vec=[format(float(x),'.17g') for x in q[:,0]];corr=np.zeros(1830);previous_e=None;last=None
    for iteration in range(5):
        target=dest/('refine_'+str(iteration));target.mkdir();(target/'singlet_matrix_higone_body.bin').symlink_to(dest/'113/singlet_matrix_higone_body.bin')
        (target/'vector.txt').write_text('\n'.join(vec)+'\n');corr.tofile(target/'correction.bin');result=target/'output';result.mkdir()
        subprocess.run([str(binary),'refine',str(target),str(result),'1830'],check=True)
        r=read(result/'refinement.json');refinements.append(r);e=mp.mpf(r['electronic_energy']);rnorm=mp.mpf(r['eigen_residual_l2']);last=result
        if previous_e is not None and abs(e-previous_e)<=mp.mpf('1e-24') and rnorm<=mp.mpf('1e-24'):break
        residual=np.fromfile(result/'residual.bin',dtype='<f8');corr=-q[:,1:]@((q[:,1:].T@residual)/(w[1:]-float(e)));vec=(result/'vector.txt').read_text().splitlines();previous_e=e
    np.save(dest/'ground_vector.npy',np.fromfile(last/'vector.bin',dtype='<f8'))
    with mp.workdps(100):vector=[mp.mpf(x) for x in (last/'vector.txt').read_text().splitlines()]
    symmetry=state_symmetry(s,c,vector,definition);write(dest/'symmetry.json',symmetry)
    numerical=dict(pre,H='PASS',eigen='PASS' if mp.mpf(r['eigen_residual_l2'])<=guards['eigen_l2_max'] else 'FAIL',norm='PASS' if mp.mpf(r['vector_norm_error'])<=guards['norm_max'] else 'FAIL')
    status=overall_status(numerical,symmetry['guards'])
    with mp.workdps(100):bo=str(mp.mpf(r['electronic_energy'])+mp.mpf('2.5'))
    converged=previous_e is not None and abs(e-previous_e)<=mp.mpf('1e-24') and rnorm<=mp.mpf('1e-24')
    precision_shift=None if 64 not in eig else float(w[0]-eig[64][0][0])
    row=dict(arm=arm,status=status,pre_guards=pre,numerical_guards=numerical,spatial_guards=symmetry['guards'],precision=results,refinements=refinements,
          diagnostic_electronic_energy=r['electronic_energy'],diagnostic_BO=bo,accepted_BO=bo if status=='ACCEPTED' else None,
          energy_provenance='actually computed after pre-guards; post-solve symmetry still mandatory',high_precision_diagonalization='113-bit residual correction; binary64 full-spectrum preconditioner, no formal lowest-root certificate',
          upstream_energy_error_bound=None,precision_convergence_bound_is_empirical=True,ground_refinement_converged=converged,
          energy_64_to_113_shift=precision_shift,empirical_energy_convergence=precision_shift is not None and abs(precision_shift)<=1e-12,
          runtime_seconds=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    write(dest/'result.json',row);print('ARM COMPLETE',arm,status,bo,symmetry['guards'],flush=True);return row


def main():
    mp.mp.dps=100
    seal,definition=precheck();binary,libint=compile_native();guards=seal['protocol']['guards'];rows=[]
    for arm in ('L','I'):
        verify(seal['bound_sha256'],ROOT,MAIN);rows.append(arm_run(arm,definition,binary,libint,guards))
    ao={k:difference(np.load(OUT/'L'/('raw_'+k+'.npy')),np.load(OUT/'I'/('raw_'+k+'.npy'))) for k in ('s','t','v','g')}
    write(OUT/'AO_cross_comparison.json',dict(unmodified_common_AO_representation=True,raw_S_difference_preserved=True,differences=ao,alignment='same verified supplied polynomial/radial dyadics and labels; Cartesian engine mapped into this AO convention',measurement_uncertainty='binary64 integral and Libint spherical-mapping error unbounded'))
    old='-.11803113362157003';reference='-.120230341178823';baselines={};budgets={}
    for row in rows:
        if row.get('diagnostic_BO') is not None:
            baselines[row['arm']]=compare_interval(old,row['diagnostic_BO']);budgets[row['arm']]=signed_budget(old,row['diagnostic_BO'],reference)
    inter=compare_interval(rows[0]['diagnostic_BO'],rows[1]['diagnostic_BO']) if all(r.get('diagnostic_BO') is not None for r in rows) else None
    sensitive=any(r.get('energy_64_to_113_shift') is not None and abs(r['energy_64_to_113_shift'])>1e-12 for r in rows)
    for a in ('L','I'):
        d=read(OUT/a/'compact_direct_53.json') if (OUT/a/'compact_direct_53.json').exists() else None
        if d and any(p['pre_guard']=='FAIL' for p in d['paths']) and any(p['transform']['H_asym_max'] is not None and mp.mpf(p['transform']['H_asym_max'])<1e-10 for p in next(r for r in rows if r['arm']==a).get('precision',[])):sensitive=True
    measured=classifications({r['arm']:r['status'] for r in rows},{k:v['measured_relation'] for k,v in baselines.items()},None if inter is None else inter['measured_relation'],sensitive)
    rigorous=classifications({r['arm']:r['status'] for r in rows},{k:v['uncertainty_relation'] for k,v in baselines.items()},None if inter is None else inter['uncertainty_relation'],sensitive)
    write(OUT/'summary.json',dict(arms=rows,baseline_comparisons=baselines,inter_arm_comparison=inter,signed_budgets=budgets,measured_classifications=measured,uncertainty_qualified_classifications=rigorous,
          remaining_reference_gap_is_pure_basis_error=False,reference_side='UNRESOLVED',same_basis_energy_criterion=1e-9,overall_accepted_count=sum(r['status']=='ACCEPTED' for r in rows),QZ44='historical FAIL unchanged',NOT_CERTIFIED=True,STOP=True))
    verify(seal['bound_sha256'],ROOT,MAIN);write(OUT/'preservation.json',dict(unchanged=True,bindings_checked=len(seal['bound_sha256'])))


if __name__=='__main__':main()
