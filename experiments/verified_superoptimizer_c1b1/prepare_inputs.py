"""Deterministic stress inputs; synthetic dt values are diagnostics, not new physics."""
import json
import sys
from fractions import Fraction as Q
from . import evidence as E
import a_reference.c1b1_two_atom as C


def prepare():
    sys.set_int_max_str_digits(0)
    rows = json.loads((E.HERE / 'pilot_inputs.json').read_bytes())
    def add(dr, dt, tags, profiles=None):
        r = dict(id=f's{len(rows):04d}', dr=list(map(str,dr)), dt=str(dt), region='stress', tags=tags)
        if profiles:
            r['profiles'] = profiles
        rows.append(r)
    for r in (C.L.R_MIN_BOHR-Q(1,2**96), C.L.R_MIN_BOHR, C.L.R_MIN_BOHR+Q(1,2**160), Q(10240), Q(2**46)):
        for d in ((r,0,0),(0,r,0),(r,Q(1,2**160),-Q(1,2**200))):
            for sign in (-1,1):
                add(tuple(sign*Q(x) for x in d), Q(20), ['near_domain_or_long','sign_symmetry','axis_disparity'])
    for dt in (0,Q(1,2**100),Q(2**30),-20):
        add((Q(3),0,0), Q(dt), ['impulse_scale'])
    add((0,0,0),0,['domain_refusal_before_zero_dt'])
    spec = dict(kind='FX',width=96,frac=80)
    for M in (256,512,1024,16384):
        print('prepare midpoint M', M, flush=True)
        dv = C._model(Q(100),M,True)[1]
        force = Q(-dv[0]-dv[1],2*(1<<M))
        add((Q(10),0,0),Q(1,2**81)/force,['synthetic_midpoint',f'precision_target_{M}'],[spec])
    dv = C._model(Q(100),512,True)[1]
    force = Q(-dv[0]-dv[1],2*(1<<512))
    for raw in (-(1<<95),(1<<95)-1,1<<95):
        for delta in (Q(-3,4),Q(-1,4),Q(1,4),Q(3,4)):
            add((Q(10),0,0),(Q(raw)+delta)/2**80/force,['momentum_overflow_boundary'],[spec])
    trajectories = [dict(id='head_on',e='9',b_frac='0',cap=100000),
                    dict(id='oblique',e='1/2',b_frac='1',cap=100000),
                    dict(id='weak',e='1/100',b_frac='2',cap=100000)]
    E.write(E.HERE / 'promotion_inputs.json', dict(impulses=rows,trajectories=trajectories,
                                               refusals=[dict(id=k,refusal=k,cap=1) for k in
                                                         ('domain','impulse_overflow','momentum_overflow','position_overflow')],
                                               benchmark=dict(repetitions=3,warmup=1,threads=1)))
    print(len(rows), 'input records', flush=True)


if __name__ == '__main__':
    prepare()
