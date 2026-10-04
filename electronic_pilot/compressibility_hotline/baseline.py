"""Guaranteed accounting prototype. Full checkpoints remain the authority."""
from fractions import Fraction
import time
import numpy as np


def F(x):return Fraction(float(x))


def encode(v):
    center = v.astype(np.complex64).astype(np.complex128)
    radius = sum((abs(F(a.real)-F(b.real))+abs(F(a.imag)-F(b.imag)) for a,b in zip(v,center)),Fraction())
    return center, radius


def transition(previous, radius, enter, exit_, safety):
    if radius > safety:return 'FULL','SAFETY_OVERRIDE'
    if radius > enter:return 'FULL','ERROR_BOUND'
    if previous == 'FULL' and radius >= exit_:return 'FULL','HYSTERESIS'
    return 'COARSE_CERTIFIED','RETURN_OR_STAY_COARSE'


def indices(n, kind):
    if kind == 'ascending':return list(range(n))
    if kind == 'descending':return list(range(n-1,-1,-1))
    return list(range(0,n,2))+list(range(1,n,2))


def enclosure(center, radii, op, slices):
    # Every ordered block pair is included, including cross coupling.
    pairs = []
    lengths=[sum((abs(F(z.real))+abs(F(z.imag)) for z in center[si]),Fraction()) for si in slices]
    for i, si in enumerate(slices):
        li = lengths[i]
        for j,sj in enumerate(slices):
            lj = lengths[j]
            assert not np.iscomplexobj(op), 'sealed operators are real'
            bound = F(np.max(abs(op[si,sj])))
            error = bound*(li*radii[j]+lj*radii[i]+radii[i]*radii[j])
            operations=8*(len(center[si])+len(center[sj])+1)
            gamma=Fraction(operations,2**52-operations)
            rounding=gamma*bound*li*lj+operations*Fraction(1,2**1074)
            error+=rounding
            mid = np.vdot(center[si],op[si,sj]@center[sj])
            pairs.append(dict(i=i,j=j,center_real=float(mid.real),center_imag=float(mid.imag),
                              radius_num=error.numerator,radius_den=error.denominator))
    return pairs


def run(waves, d, p, path, order):
    size=p['block_sizes'][d['label']]; n=waves.shape[1]
    slices=[slice(i,min(i+size,n)) for i in range(0,n,size)]
    status=['COLD_EXACT_STORAGE']*len(slices)
    trace=[]; outputs=[]; times=dict(baseline_cpu=0.,monitor_cpu=0.,refine_cpu=0.,conversion_cpu=0.,enclosure_cpu=0.)
    started=time.process_time(); checks=hot=refines=0
    for epoch, exact in enumerate(waves):
        base=time.process_time(); centers=[]; radii=[]
        for si in slices:
            a=time.process_time(); center,radius=encode(exact[si]); times['conversion_cpu']+=time.process_time()-a
            centers.append(center);radii.append(radius)
        times['baseline_cpu']+=time.process_time()-base
        records=[]
        for block in indices(len(slices),order):
            a=time.process_time(); old=status[block]
            input_radius=radii[block]
            new,reason=('FULL','REF_FULL') if path=='REF' else ('COARSE_CERTIFIED','BASELINE_ONLY')
            if path=='HOTLINE':
                new,reason=transition(old,radii[block],F(p['hot_enter_radius_l1']),
                                      F(p['cold_return_radius_l1']),F(p['safety_radius_l1']))
            times['monitor_cpu']+=time.process_time()-a;checks+=1
            if new=='FULL' and old!='FULL':hot+=1
            status[block]=new
            # FULL uses exact contribution; COARSE supplies a nonzero center and enclosure.
            if new=='FULL':centers[block]=exact[slices[block]].copy();radii[block]=Fraction()
            records.append(dict(block=block,epoch=epoch,updated=True,previous=old,status=new,reason=reason,
                                input_radius_num=input_radius.numerator,input_radius_den=input_radius.denominator,
                                source_real=exact[slices[block]].real.tolist(),source_imag=exact[slices[block]].imag.tolist(),
                                center_real=centers[block].real.tolist(),center_imag=centers[block].imag.tolist(),
                                radius_num=radii[block].numerator,radius_den=radii[block].denominator))
        center=np.concatenate(centers)
        a=time.process_time(); ops=[d['s'],d['h'],*d['dipoles']]
        accounts=[enclosure(center,radii,op,slices) for op in ops]
        times['enclosure_cpu']+=time.process_time()-a
        out=np.empty_like(exact)
        # An exact-coefficient decision is unavailable from any nonzero radius.
        # Restoration is mandatory, and never changes baseline coverage.
        for block in indices(len(slices),order):
            a=time.process_time(); out[slices[block]]=exact[slices[block]]
            if status[block]!='FULL':refines+=1
            times['refine_cpu']+=time.process_time()-a
        outputs.append(out);trace.append(dict(epoch=epoch,blocks=records,accounts=accounts,
                                              canonical_action='EXACT_RESTORE_ALL_NON_FULL'))
    times['total_cpu']=time.process_time()-started
    times['monitor_self_fraction']=times['monitor_cpu']/times['total_cpu'] if times['total_cpu'] else None
    times['monitor_with_acquisition_cpu']=times['monitor_cpu']+times['conversion_cpu']
    times['monitor_with_acquisition_fraction']=times['monitor_with_acquisition_cpu']/times['total_cpu'] if times['total_cpu'] else None
    times['monitor_per_block_check_cpu']=times['monitor_cpu']/checks
    times.update(checks=checks,HOT_transitions=hot,REFINE_operations=refines,
                 checkpoint_bytes=int(waves.nbytes),center_bytes=int(n*8),
                 monitor_full_component_reads=int(waves.size),
                 baseline_includes_conversion=True,enclosure_cost_separate=True)
    return dict(path=path,order=order,trace=trace,cost=times),np.array(outputs)


def controls(p, kind, order='ascending', thresholds=None):
    th=p['control_thresholds'] if thresholds is None else thresholds
    seq=p['hidden_radii'] if kind=='hidden' else p['thrash_radii']
    status=['COARSE_CERTIFIED']*3; rows=[]
    for epoch,r in enumerate(seq):
        # block 1 remains stable; block 2 has a constant small nonzero contribution.
        sources=[1+r,2.,3.0005]; centers=[1.,2.,3.]
        radii=[r,0.,.0005]; records=[]
        for i in indices(3,order):
            old=status[i]; status[i],reason=transition(old,radii[i],th['enter'],th['exit'],th['safety'])
            records.append(dict(block=i,epoch=epoch,updated=True,previous=old,status=status[i],reason=reason,
                                source=sources[i],center=centers[i],radius=radii[i]))
        rows.append(dict(epoch=epoch,blocks=records,result=sum(sources),coverage_center=sum(centers),
                         coverage_radius=sum(radii)))
    return dict(kind=kind,order=order,rows=rows,thresholds=th)
