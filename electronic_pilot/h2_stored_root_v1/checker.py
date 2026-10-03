"""Own parser and exact dyadic operations; no imports from previous evaluators."""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import struct
import subprocess
import time

LADDER = ((80,266),(120,399),(160,532),(240,798))
CASES = ('H2.0.1.1.6_h-h+', 'H2.1.1.1.3_jc_sym', 'H2.1.1.1.6_h2_sym',
         'H2.1.1.2.3_jc_asym', 'H2.1.1.2.6_general')
OLD_RAW = Path('runs/h2_representation_pilot1/internal_convergence_v0_20261003')
RAW = Path('runs/h2_representation_pilot1/stored_root_v1_20261003')
DOC = Path('docs/active/h2_stored_root_v1')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=True)+'\n',encoding='utf8')

def dyadic(m,e):
    return Fraction(m<<e) if e>=0 else Fraction(m,1<<-e)

def pair(x):
    x=Fraction(x); d=x.denominator
    if d&(d-1): raise ValueError('not dyadic')
    return x.numerator,-(d.bit_length()-1)

def record(words):
    if len(words)!=9: raise ValueError('record size')
    bits,sign,exp,*limbs=words
    if bits not in (320,384): raise ValueError('unsupported precision')
    sign &= (1<<32)-1
    if sign not in (1,(1<<32)-1): raise ValueError('sign')
    active=bits//64
    if any(limbs[active:]): raise ValueError('inactive limb')
    m=sum((v&((1<<64)-1))<<(64*i) for i,v in enumerate(limbs[:active]))
    if exp==-(1<<63)+1:
        if m: raise ValueError('noncanonical zero')
        return Fraction(0)
    if not -100000<exp<100000 or m.bit_length()!=bits: raise ValueError('invalid exponent/mantissa')
    return dyadic(m if sign==1 else -m,exp-bits)

def records(data,offset,count):
    return [record(struct.unpack_from('<9q',data,offset+i*72)) for i in range(count)]

def read_hs(path):
    data=Path(path).read_bytes()
    if len(data)<72: raise ValueError('short HS')
    magic,ver,n,ln,limbs,ndigits,nmax,omega,itmax=struct.unpack_from('<9q',data)
    if magic!=0x4832534155445630 or ver!=1 or not 0<n<=1000 or ln!=n*(n+1)//2 or limbs!=6:
        raise ValueError('HS header')
    if len(data)!=72+2*ln*72: raise ValueError('HS length')
    vals=records(data,72,2*ln)
    prec=Counter(struct.unpack_from('<q',data,72+i*72)[0] for i in range(2*ln))
    return n,vals[:ln],vals[ln:],dict(dimension=n,packed_length=ln,precision_counts=dict(prec),
        NDIGITS=ndigits,NMAX=nmax,OMEGA=omega,ITMAX=itmax,layout='lower triangle by row; exact dyadics; mirror only')

def read_ev(path,n):
    data=Path(path).read_bytes()
    if len(data)!=32+(n+1)*72 or struct.unpack_from('<4q',data)!=(0x4832564155445630,1,n,6):
        raise ValueError('EV header/length')
    vals=records(data,32,n+1)
    return vals[0],vals[1:],dict(Counter(struct.unpack_from('<q',data,32+i*72)[0] for i in range(n+1)))

def read_observed(path):
    values={}
    for line in Path(path).read_text().splitlines():
        words=line.split()
        if len(words)>=2 and words[0]=='VALUE' and words[1] in ('initial_EN','wa1'):
            if words[1] in values: raise ValueError('duplicate observed value')
            values[words[1]]=record(tuple(map(int,words[2:])))
    if values.keys()!={'initial_EN','wa1'}: raise ValueError('missing observed value')
    if values['wa1'].denominator!=1: raise ValueError('noninteger WA1')
    return values['initial_EN'],int(values['wa1'])

def linux(path):
    p=Path(path).resolve().as_posix()
    if p[1:3]!=':/': raise ValueError('Windows absolute path required')
    return '/mnt/'+p[0].lower()+p[2:]

def matrix_file(path,n,a):
    if len(a)!=n*(n+1)//2: raise ValueError('matrix shape')
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('w',encoding='ascii',newline='\n') as f:
        f.write(str(n)+'\n')
        for x in a:
            m,e=pair(x); f.write(f'{m} {e}\n')

def parse_backend(text,n):
    pivots=[];direction=[];summary=None;lower=None;env=None;seconds=None
    for line in text.splitlines():
        w=line.split()
        if w[0]=='PIVOT':
            k,s=int(w[1]),int(w[2]);lo=dyadic(int(w[3]),int(w[4]));hi=dyadic(int(w[5]),int(w[6]))
            if k!=len(pivots) or lo>hi or s not in (-1,0,1): raise ValueError('pivot order/sign')
            if s!=(1 if lo>0 else -1 if hi<0 else 0): raise ValueError('pivot sign enclosure')
            pivots.append(dict(index=k,sign=s,lower_pair=[w[3],int(w[4])],upper_pair=[w[5],int(w[6])]))
        elif w[0]=='RESULT':
            if summary is not None: raise ValueError('duplicate RESULT')
            status=w[1];neg,pos,unc,done,dim=map(int,w[2:])
            if dim!=n or status not in ('COMPLETE','NOT_SPD','UNCERTAIN'): raise ValueError('result status')
            summary=dict(status=status,negative=neg,positive=pos,uncertain=unc,completed_pivots=done,dimension=dim)
        elif w[0]=='DIRECTION':
            if int(w[1])!=len(direction): raise ValueError('direction order')
            direction.append([w[2],int(w[3])])
        elif w[0]=='LAMBDA_MIN_LOWER': lower=[w[1],int(w[2])]
        elif w[0]=='ENV': env=w[1:]
        elif w[0]=='SECONDS': seconds=float(w[1])
        else: raise ValueError('unknown backend line')
    if summary is None or env is None or seconds is None: raise ValueError('incomplete backend')
    signs=[p['sign'] for p in pivots]
    if summary['negative']!=signs.count(-1) or summary['positive']!=signs.count(1) or summary['uncertain']!=signs.count(0):
        raise ValueError('count mismatch')
    if summary['status']=='COMPLETE' and (len(pivots)!=n or 0 in signs or summary['completed_pivots']!=n):
        raise ValueError('false complete')
    if summary['status']=='NOT_SPD' and (not signs or signs[-1]!=-1): raise ValueError('false NOT_SPD')
    if summary['status']=='UNCERTAIN' and (not signs or signs[-1]!=0): raise ValueError('false uncertain')
    return dict(**summary,pivots=pivots,direction_pairs=direction,lambda_min_lower_pair=lower,environment=env,seconds=seconds,
        count_scope='full matrix' if summary['status']=='COMPLETE' else 'resolved leading prefix only')

def factor(path,n,bits,mode,output):
    argv=['wsl','-e','/usr/bin/timeout','600',linux(RAW/'interval_ldl'),linux(path),str(bits),mode]
    start=time.monotonic()
    p=subprocess.run(argv,capture_output=True,text=True,encoding='utf8',timeout=620)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.with_suffix('.stdout').write_text(p.stdout,encoding='utf8')
    output.with_suffix('.stderr').write_text(p.stderr,encoding='utf8')
    write(output.with_suffix('.process.json'),dict(argv=argv,exit=p.returncode,wall_seconds=time.monotonic()-start))
    if p.returncode or p.stderr: raise RuntimeError('backend failure; preserve output and stop')
    result=parse_backend(p.stdout,n);write(output.with_suffix('.json'),result)
    return result

def ladder(n,a,mode,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    path=directory/'matrix.dyadic';matrix_file(path,n,a);attempts=[]
    for dps,bits in LADDER:
        result=factor(path,n,bits,mode,directory/f'p{dps}')
        attempts.append(dict(decimal_digits=dps,bits=bits,result=result))
        if result['status']!='UNCERTAIN': break
    return dict(attempts=attempts,final=attempts[-1]['result'],matrix_sha256=sha(path))

def qform(a,x):
    # Exact integer accumulation after a single shared dyadic denominator.
    n=len(x); powers=[pair(v)[1] for v in x]; ex=min(powers,default=0)
    xx=[pair(v)[0]<<(pair(v)[1]-ex) for v in x]
    ap=[pair(a[i*(i+1)//2+j]) for i in range(n) for j in range(i+1)]
    ae=min((p[1] for p in ap),default=0);total=0;k=0
    for i in range(n):
        for j in range(i+1):
            m,e=ap[k];k+=1;total+=(m<<(e-ae))*xx[i]*xx[j]*(1 if i==j else 2)
    return dyadic(total,ae+2*ex)

def exact_direction(a,result):
    x=[dyadic(int(m),e) for m,e in result['direction_pairs']]
    if not x: return None
    q=qform(a,x);norm=sum(v*v for v in x)
    return dict(length=len(x),q_pair=[str(pair(q)[0]),pair(q)[1]],norm_pair=[str(pair(norm)[0]),pair(norm)[1]],
        negative_witness=q<0,direction_RQ=decimal(q/norm),scope='one Schur direction; RQ upper bound on lambda_min; not its value')

def decimal(x,digits=85):
    import mpmath as mp
    with mp.workdps(digits+10): return mp.nstr(mp.mpf(x.numerator)/x.denominator,digits)

def measured(n,h,s,e,v,spd):
    import mpmath as mp
    with mp.workdps(240):
        cv=lambda a:mp.mpf(a.numerator)/a.denominator
        hh=list(map(cv,h));ss=list(map(cv,s));vv=list(map(cv,v));ee=cv(e)
        hv=[mp.mpf(0) for _ in v];sv=[mp.mpf(0) for _ in v];k=0
        for i in range(n):
            for j in range(i+1):
                hv[i]+=hh[k]*vv[j];sv[i]+=ss[k]*vv[j]
                if i!=j: hv[j]+=hh[k]*vv[i];sv[j]+=ss[k]*vv[i]
                k+=1
        residual=[a-ee*b for a,b in zip(hv,sv)]
        ns=mp.fsum(a*b for a,b in zip(vv,sv)); rq=mp.fsum(a*b for a,b in zip(vv,hv))/ns
        result=dict(grade='MEASURED_ONLY_NO_ACCEPTANCE_THRESHOLD',decimal_digits=240,
            E_returned=mp.nstr(ee,180),residual_L2=mp.nstr(mp.sqrt(mp.fsum(t*t for t in residual)),90),
            residual_Linf=mp.nstr(max(map(abs,residual)),90),nS=mp.nstr(ns,180),
            normalization_error=mp.nstr(abs(ns-1),90),E_RQ=mp.nstr(rq,180),RQ_minus_E=mp.nstr(rq-ee,90),
            transformed_residual=None,transformed_status='NOT_EXECUTED_S_NOT_SPD')
        if spd:
            # Independent HP solve. No native/vendor factors used.
            sm=mp.matrix(n)
            for i in range(n):
                for j in range(i+1): sm[i,j]=sm[j,i]=ss[i*(i+1)//2+j]
            z=mp.cholesky_solve(sm,mp.matrix(residual))
            q=mp.fsum(residual[i]*z[i] for i in range(n))
            if ns<=0 or q<0: raise ValueError('transformed metric inconsistency')
            result.update(transformed_residual=mp.nstr(mp.sqrt(q/ns),100),transformed_status='MEASURED_S_SPD_CONFIRMED')
        return result

def root(n,h,s,e,directory):
    delta=Fraction(1,1<<64);low=e-delta;high=e+delta;trace=[]
    def count(sig,label):
        r=ladder(n,[a-sig*b for a,b in zip(h,s)],'INERTIA',Path(directory)/label)
        trace.append(dict(label=label,shift_pair=[str(pair(sig)[0]),pair(sig)[1]],shift=decimal(sig),
            negative=r['final']['negative'] if r['final']['status']=='COMPLETE' else None,
            status=r['final']['status'],ladder=r))
        return trace[-1]['negative']
    a=count(low,'low');b=count(high,'high')
    if (a,b)!=(0,1): return dict(status='LOWEST_TRANSITION_FAILED',trace=trace,low=decimal(low),high=decimal(high),
        width=decimal(high-low),inertia_low=a,inertia_high=b,E_inside=True)
    # Avoid sigma=E midpoint: quarter offset first, thereafter deterministic midpoint.
    for iteration in range(8):
        mid=(3*low+high)/4 if iteration==0 else (low+high)/2
        c=count(mid,f'bisect{iteration}')
        if c not in (0,1): return dict(status='INERTIA_UNRESOLVED',trace=trace)
        if c==0: low=mid
        else: high=mid
        if not low<=e<=high:
            return dict(status='RETURNED_E_OUTSIDE',trace=trace,low=decimal(low),high=decimal(high),E_inside=False)
        if high-low<=Fraction(1,1<<70): break
    return dict(status='LOWEST_ROOT_ENCLOSED',trace=trace,low=decimal(low),high=decimal(high),
        low_pair=[str(pair(low)[0]),pair(low)[1]],high_pair=[str(pair(high)[0]),pair(high)[1]],
        width=decimal(high-low),inertia_low=0,inertia_high=1,E_inside=True)
