"""Transcribed frozen specification only; no evaluator shared with executor."""

from fractions import Fraction as Q

import hashlib

import json

CONTRACT_VERSION = 'c1a-ar2-lang2024-v1'

FROZEN_FINGERPRINT = 'ada6153be05af3e582139fdc81b5697fffaf18d12f9f2de6e8d5ac2fdfe0839e'

BOHR_ANGSTROM, R_MIN_ANGSTROM = (Q('0.529177210903'), Q('1.2'))

SHORT = {'BO': {1: ('6.92639712', {-1: '2.19578828e4', 0: '6.77672149e4', 1: '8.52129476e4', 2: '9.53252754e4'}), 2: ('2.34781022', {-1: '-2.16338828e4', 0: '3.18311293e4', 1: '-8.18603449e3', 2: '8.37564742e2'})}, 'REL': {1: ('1.66833595', {0: '-3.55673715e0', 1: '7.59367220e-1', 2: '-4.19874548e-2'}), 2: ('3.07137482', {0: '-2.83560129e1', 1: '1.64892143e1', 2: '7.19542232e0'})}, 'QED': {1: ('1.64936036', {0: '-1.2621862e-1', 1: '1.176436e-2', 2: '0'}), 2: ('2.29848003', {0: '0', 1: '0', 2: '6.921721e-2'})}}

LONG = {'BO': ('3.65946625', {3: '64.2295222', 4: '1503.45262', 5: '49033', 6: '1828012', 7: '81913453', 8: '4294913366'}, 1), 'REL': ('1.05249333', {2: '-9.43594504e-4', 3: '1.76276088e-1', 4: '3.99787449e-1'}, 0), 'QED': ('3.91638946', {3: '-1.949525e-2', 4: '-4.8877359e-1'}, 0)}

RET_A = ('3.064827731712776e-01', '4.843969950480238e-03', '7.793815409352866e-06', '1.031221966985517e-14', '4.204140311858030e-12')

RET_B = ('3.064827731712776e-01', '4.858660928580025e-03', '1.156839432134599e-05', '1.670845939899731e-08', '2.151070686307512e-17', '8.769598859882065e-15')

SIGMA = {'SIGMA_BO': (('1.9', '6.29130076e-1'), ('6.81313900e-1', '9.85423065e-1'), ('5.76343421e-3', '2.56799977e-8'), ('2.56907367e-2', '2.93856722e-6')), 'SIGMA_REL': (('1.05', '6.76919448e-5'), ('1.16451516e-2', '1.95220703e-8'), ('2.58221232e-1', '1.89517999e-3'), ('2.00658289e-3', '6.75730842e-10'))}


def potential_fingerprint():
    rows=[CONTRACT_VERSION,str(BOHR_ANGSTROM),str(R_MIN_ANGSTROM)]
    for name in ('BO','REL','QED'):
        for j,(alpha,cs) in sorted(SHORT[name].items()):
            rows.append(f'{name}.short.{j}:{Q(alpha)}:'+','.join(f'{i}={Q(c)}' for i,c in sorted(cs.items())))
        eta,cs,kadd=LONG[name]
        rows.append(f'{name}.long:{Q(eta)}:{kadd}:'+','.join(f'{k}={Q(c)}' for k,c in sorted(cs.items())))
    for name,vs in (('RET_A',RET_A),('RET_B',RET_B)):
        rows.append(name+':'+','.join(str(Q(v)) for v in vs))
    for name in ('SIGMA_BO','SIGMA_REL'):
        rows.append(name+':'+','.join(f'{Q(a)}/{Q(s)}' for a,s in SIGMA[name]))
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest()
MASS=Q('39.9623831237')/Q('5.485799090441e-4')
DT=Q(40)
HALF=DT/2
DE=Q('0.000451995775')
R_MIN2=(R_MIN_ANGSTROM/BOHR_ANGSTROM)**2
LOW=-(1<<95)
HIGH=(1<<95)-1
SPEC={'schema':'c1b1-replay-v1','executor':'c1b1-two-atom-v2','potential':FROZEN_FINGERPRINT,
      'species':['Ar40','Ar40'],'mass':str(MASS),'dt':str(DT),'position':[96,48],
      'momentum':[96,80],'rounding':'nearest-ties-even','drift':'v2',
      'retardation':True,'r_min2':str(R_MIN2),'initial_E_max':str(10*DE),'precision_cap':16384}
SPEC_FINGERPRINT=hashlib.sha256(json.dumps(SPEC,sort_keys=True,separators=(',',':')).encode()).hexdigest()
if potential_fingerprint()!=FROZEN_FINGERPRINT:
    raise ImportError('frozen potential specification fingerprint mismatch')
