"""Separate formulas; never import tensor, baseline, or campaign implementations.

Author-written numerical checker, not an external independent audit.
"""
from fractions import Fraction
import numpy as np
from scipy.linalg import expm


def _f(z):return Fraction(float(z))


def _radius(v,c):
    parts=[]
    for k in range(len(v)):
        parts.extend([abs(_f(v[k].real)-_f(c[k].real)),abs(_f(v[k].imag)-_f(c[k].imag))])
    return sum(parts,Fraction())


def _next(old,r,th):
    if r>th[2]:return 'FULL','SAFETY_OVERRIDE'
    if r>th[0]:return 'FULL','ERROR_BOUND'
    if old=='FULL' and r>=th[1]:return 'FULL','HYSTERESIS'
    return 'COARSE_CERTIFIED','RETURN_OR_STAY_COARSE'


def electronic(receipt, waves, d, p, outputs):
    n=len(waves[0]); size=p['block_sizes'][d['label']]
    ranges=[slice(i,min(i+size,n)) for i in range(0,n,size)]
    previous=['COLD_EXACT_STORAGE']*len(ranges)
    last=[-1]*len(ranges)
    if len(receipt['trace'])!=len(waves):raise ValueError('epochs')
    for epoch,(row,exact) in enumerate(zip(receipt['trace'],waves)):
        seen={}; centers=[]; radii=[]
        for record in row['blocks']:
            i=record['block']
            if i in seen or i not in range(len(ranges)):raise ValueError('block coverage')
            seen[i]=record
        for i,si in enumerate(ranges):
            if i not in seen:raise ValueError('starvation / missing update')
            r=seen[i]
            if r['epoch']!=epoch or not r['updated']:raise ValueError('stale epoch')
            last[i]=epoch
            src=np.array(r['source_real'])+1j*np.array(r['source_imag'])
            if not np.array_equal(src,exact[si]):raise ValueError('stale source')
            coarse=np.asarray(exact[si],dtype=np.complex64).astype(complex)
            rad=_radius(exact[si],coarse)
            if rad!=Fraction(r['input_radius_num'],r['input_radius_den']):raise ValueError('stale bound')
            if receipt['path']=='HOTLINE':
                want,reason=_next(previous[i],rad,[_f(p[k]) for k in
                     ['hot_enter_radius_l1','cold_return_radius_l1','safety_radius_l1']])
            elif receipt['path']=='REF':want,reason='FULL','REF_FULL'
            else:want,reason='COARSE_CERTIFIED','BASELINE_ONLY'
            if r['status']!=want or r['reason']!=reason or r['previous']!=previous[i]:raise ValueError('trigger/hysteresis')
            previous[i]=want
            cen=np.array(r['center_real'])+1j*np.array(r['center_imag'])
            expected=exact[si] if want=='FULL' else coarse
            if not np.array_equal(cen,expected):raise ValueError('cold contribution corrupted')
            delta=Fraction(r['radius_num'],r['radius_den'])
            if delta!=(0 if want=='FULL' else rad):raise ValueError('enclosure radius')
            centers.append(cen);radii.append(delta)
        if any(epoch-t>=p['scheduler_K'] for t in last):raise ValueError('starvation')
        center=np.concatenate(centers)
        for op,pairs in zip([d['s'],d['h'],*d['dipoles']],row['accounts']):
            if {(v['i'],v['j']) for v in pairs}!={(i,j) for i in range(len(ranges)) for j in range(len(ranges))}:raise ValueError('coupling omitted')
            if len(pairs)!=len(ranges)**2:raise ValueError('coupling duplicated')
            for v in pairs:
                i,j=v['i'],v['j'];si,sj=ranges[i],ranges[j]
                li=sum([abs(_f(z.real))+abs(_f(z.imag)) for z in centers[i]],Fraction())
                lj=sum([abs(_f(z.real))+abs(_f(z.imag)) for z in centers[j]],Fraction())
                b=_f(np.max(np.abs(op[si,sj])))
                count=8*(len(centers[i])+len(centers[j])+1)
                predicted=b*(li*radii[j]+lj*radii[i]+radii[i]*radii[j])+Fraction(count,2**52-count)*b*li*lj+count*Fraction(1,2**1074)
                actual=Fraction(v['radius_num'],v['radius_den'])
                if actual!=predicted:raise ValueError('stale coupling bound')
                mid=complex(v['center_real'],v['center_imag'])
                direct=np.vdot(exact[si],op[si,sj]@exact[sj])
                if abs(mid-direct)>float(actual)+1e-14:raise ValueError('contribution outside enclosure')
        if not np.array_equal(outputs[epoch],exact):raise ValueError('canonical physics changed')
    return True


def control(receipt,p):
    kind=receipt['kind']; seq=p['hidden_radii'] if kind=='hidden' else p['thrash_radii']
    old=['COARSE_CERTIFIED']*3
    th=receipt['thresholds']
    for epoch,radius in enumerate(seq):
        row=receipt['rows'][epoch]; entries={r['block']:r for r in row['blocks']}
        if set(entries)!={0,1,2}:raise ValueError('starvation')
        expected_source=[1+radius,2.,3.0005]
        expected_radius=[radius,0.,.0005]
        for i in range(3):
            r=entries[i]
            if not r['updated'] or r['epoch']!=epoch:raise ValueError('stale baseline')
            if r['source']!=expected_source[i] or r['center']!=[1.,2.,3.][i] or r['radius']!=expected_radius[i]:raise ValueError('cold/bound corruption')
            want,why=_next(old[i],expected_radius[i],[th['enter'],th['exit'],th['safety']])
            if r['status']!=want or r['reason']!=why:raise ValueError('threshold or unsafe hysteresis')
            old[i]=want
        if row['result']!=sum(expected_source):raise ValueError('order changed result')
        if abs(row['result']-row['coverage_center'])>row['coverage_radius']+1e-14:raise ValueError('coverage failure')
    return True


def fock_matrix(v, electrons, cut):
    """Direct occupation-amplitude enumeration, independent of sector SVD."""
    amplitudes=[]
    if electrons==1:
        amplitudes=[((2*i,),v[i]) for i in range(len(v))]
    else:
        index=0
        for p in range(28):
            for q in range(p,28):
                if p==q:amplitudes.append(((2*p,2*p+1),v[index]))
                else:
                    amplitudes.extend([((2*p,2*q+1),v[index]/np.sqrt(2)),
                                       ((2*p+1,2*q),-v[index]/np.sqrt(2))])
                index+=1
    labeled=[]
    for occupied,a in amplitudes:
        labeled.append((tuple(k for k in occupied if k<2*cut),tuple(k for k in occupied if k>=2*cut),a))
    left=sorted({a for a,b,c in labeled});right=sorted({b for a,b,c in labeled})
    mat=np.zeros((len(left),len(right)),complex)
    for a,b,c in labeled:mat[left.index(a),right.index(b)]+=c
    return mat


def density(v,d):
    if d['electrons']==1:return np.real(v[:,None]*v.conj()[None,:])
    w=np.zeros((28,28),complex); k=0
    for i in range(28):
        for j in range(i,28):
            w[i,j]=w[j,i]=v[k]/(1 if i==j else np.sqrt(2));k+=1
    gamma=2*np.einsum('ik,jk->ij',w,w.conj())
    return np.real(np.einsum('ai,ij,bj->ab',d['c'],gamma,d['c']))


def physical(ref,test,d):
    dif=test-ref
    return dict(state_error_S=float(np.sqrt(max(0,np.vdot(dif,d['s']@dif).real))),
                energy_error=float(abs(np.vdot(test,d['h']@test)-np.vdot(ref,d['h']@ref))),
                density_error=float(np.max(abs(density(test,d)-density(ref,d)))),
                dipole_error=float(max(abs(np.vdot(test,o@test)-np.vdot(ref,o@ref)) for o in d['dipoles'])))


def unitary(d,dt):
    values,vectors=np.linalg.eigh(d['s'])
    root=(vectors*np.sqrt(values))@vectors.T; inverse=(vectors/np.sqrt(values))@vectors.T
    return inverse@expm(-1j*(inverse@d['h']@inverse)*dt)@root
