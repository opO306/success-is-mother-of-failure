"""Sealed engineering criteria, not an error certificate."""
import math

def angle_difference(a,b):
    return abs(math.atan2(math.sin(float(a)-float(b)),math.cos(float(a)-float(b))))

def converged(levels):
    import mpmath as m
    if len(levels)!=3: return False
    with m.workdps(90):
        for row in levels:
            if m.mpf(row['quadrature_error'])>m.mpf(row['target']): return False
        return all(abs(m.mpf(levels[-1][k])-m.mpf(levels[-2][k]))<=m.mpf('1e-20')
                   for k in ('r_min','chi','sweep','direction','time'))

def classify(reference,actual,stable,*,confirmed=True):
    if not stable or not confirmed:
        return {'verdict':'UNRESOLVED','reason':'independent convergence or CONFIRMED provenance unavailable'}
    differences={k:angle_difference(reference[k],actual[k]) for k in ('chi','direction')}
    differences['sweep']=abs(float(reference['sweep'])-float(actual['sweep']))
    differences['r_min']=abs(float(reference['r_min'])-float(actual['r_min']))
    differences['energy']=abs(float(actual['energy']))
    limits=dict(chi=1e-5,direction=1e-5,sweep=1e-5,r_min=1e-5*float(reference['r_min']),energy=1e-3)
    failed=[k for k in limits if not math.isfinite(differences[k]) or differences[k]>limits[k]]
    return {'verdict':'DISAGREE' if failed else 'AGREE','differences':differences,'limits':limits,'failed':failed}
