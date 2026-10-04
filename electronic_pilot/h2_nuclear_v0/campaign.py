"""Seal one step, run exactly three new geometries, then STOP.

Prepare on Windows; execute in the existing WSL environment. Memory samples
sum Linux controller+descendant RSS every 20ms; no whole-host RAM claim.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from electronic_pilot.frontend_reference_v0.audit import read,write,sha
from .scalar import start,finish
from .check import check

DOC=Path('docs/active/h2_nuclear_1step_v0')
RAW=Path('runs/h2_nuclear_1step_v0_20261004')
OLD=Path('docs/active/h2_force_v0')
PYTHON='/home/otherside123/.venvs/h2-reference-pilot/bin/python'


def hostpath(value):
    value=str(value).replace('\\','/')
    if os.name!='nt' and len(value)>2 and value[1:3]==':/':
        value='/mnt/'+value[0].lower()+value[2:]
    return Path(value)


def verify(bindings):
    for key,expected in bindings.items():
        path=hostpath(key)
        if not path.is_file() or sha(path)!=expected:
            raise ValueError('hash/provenance mismatch '+key)


def prepare():
    if DOC.exists() or RAW.exists(): raise ValueError('exclusive capture only')
    old=read(OLD/'protocol.json')
    protected={**old['protected_sha256'],**old['implementation_sha256'],
               **read(OLD/'execution_seal.json')['bound_sha256']}
    # Current dashboards are intentionally mutable; historical evidence is not.
    for folder in ('electronic_pilot/h2_force_v0','tests/h2_force_v0','docs/active/h2_force_v0'):
        for p in Path(folder).glob('*'):
            if p.is_file(): protected[p.as_posix()]=sha(p)
    verify(protected)
    reused=[read(OLD/f'point_R{r}.json') for r in ('1.4','1.5','1.6')]
    mass=read('electronic_pilot/h2_nuclear_v0/mass.json')
    t=time.perf_counter();initial=start(*reused,mass['literal_value']);scalar_seconds=time.perf_counter()-t
    log=Path('runs/h2_nuclear_preflight_v2_20261004.log')
    import xml.etree.ElementTree as ET
    test=ET.parse('runs/h2_nuclear_preflight_v2_20261004.xml').getroot().find('testsuite')
    if int(test.attrib['failures']) or int(test.attrib['errors']) or int(test.attrib['skipped']): raise ValueError('preflight not clean')
    RAW.mkdir(); DOC.mkdir()
    definitions=RAW/'basis_definitions.json'
    original=Path('runs/h2_force_v0_20261004/basis_definitions.json')
    shutil.copyfile(original,definitions)
    source={p.as_posix():sha(p) for folder in ('electronic_pilot/h2_nuclear_v0','tests/h2_nuclear_v0')
            for p in Path(folder).glob('*') if p.is_file()}
    source[definitions.as_posix()]=sha(definitions)
    for p in ('electronic_pilot/ao_micro_v0/reuse.py','electronic_pilot/numerical_cause/core.py',
              'electronic_pilot/solver.py','electronic_pilot/ao_micro_v0/protocol.json',
              'electronic_pilot/h2_force_v0/interface.py','electronic_pilot/frontend_reference_v0/audit.py'):
        source[p]=sha(p)
    git={}
    for name,argv in [('HEAD',['git','rev-parse','HEAD']),('branch',['git','branch','--show-current']),
        ('status',['git','status','--porcelain']),('remote',['git','ls-remote','origin','refs/heads/master','refs/heads/codex/h2-representation-pilot1'])]:
        git[name]=subprocess.check_output(argv,text=True)
    protocol=dict(sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),git=git,
        physical='1D relative coordinate of equal proton masses / fixed COM / clamped-nuclei BO electronic ground-state approximation',
        units=dict(R='bohr',E='hartree',F='hartree/bohr',mass='electron mass',time='atomic time unit',P='atomic momentum unit'),
        mass=mass,initial_state=initial,prepare_scalar_integration_seconds=scalar_seconds,
        basis_definitions=definitions.as_posix(),reuse_paths=[(OLD/f'point_R{r}.json').as_posix() for r in ('1.4','1.5','1.6')],
        reuse_sha256={str(OLD/f'point_R{r}.json'):sha(OLD/f'point_R{r}.json') for r in ('1.4','1.5','1.6')},
        equations=['P_half=P0+dt*F0/2','R1=R0+dt*P_half/mu','F1=-(E(R1+h)-E(R1-h))/(2h)','P1=P_half+dt*F1/2'],
        derivation='R=zB-zA; COM0 => vA=-Rdot/2,vB=Rdot/2; K=m*Rdot^2/4; P=mu*Rdot; mu=m/2; pA=-P,pB=P',
        electronic='same raw cc-pV5Z AO110/full CI6105 / canonical reuse + Cholesky / evr lowest roots0,1 / unchanged numerical guards / binary64 / one thread',
        fixed_step_count=1,new_call_order=['left','center','right'],scalar_digits=80,
        scalar_validation='independent Fraction equations; absolute1e-75 bound for scalar rounding only',
        energy_diagnostic='MEASURED ONLY / no deltaH acceptance tolerance / no energy conservation certification',
        geometry='Decimal80 requested R -> nearest binary64 R -> zA=-R/2,zB=R/2; record actual PySCF coords and rounding; denominator remains fixed2h=.2',
        memory='Linux workflow controller+descendant sampled aggregate RSS20ms and each-call GNUtime maximum RSS; shared pages may be counted per process; Windows launcher/whole host not included',
        point_timeout_seconds=300,refusal='first blocker => H2_NUCLEAR_1STEP_BLOCKED / no substitutes / no retry',
        forbidden=['multi-step','formation','real-time electrons','rotation','3D','thermostat','adaptive timestep','fit/spline/analytic force','JC replacement','adaptive representation','merge/rebase/push'],
        frozen_calculator_stack='ELECTRONIC_CALC_STACK_V0 / NOT CERTIFIED / NOT PRODUCTION APPROVED',
        protected_sha256=protected,implementation_sha256=source,preflight_sha256={log.as_posix():sha(log)})
    write(DOC/'protocol.json',protocol)
    write(DOC/'protocol_seal.json',dict(sha256=sha(DOC/'protocol.json'),sealed_before_new_energies=True))
    shutil.copyfile(log,DOC/'preflight.log');shutil.copyfile('runs/h2_nuclear_preflight_v2_20261004.xml',DOC/'preflight.xml')
    shutil.copyfile('runs/h2_nuclear_preflight_20261004.log',DOC/'initial_preflight_failure.log')
    shutil.copyfile('runs/h2_nuclear_preflight_20261004.xml',DOC/'initial_preflight_failure.xml')
    print('SEALED',sha(DOC/'protocol.json'),'protected',len(protected),'R1',initial['requested_R1'],flush=True)


class Memory:
    def __enter__(self):
        self.stop=threading.Event();self.maximum=0;self.controller_maximum=0;self.samples=0
        pages=os.sysconf('SC_PAGE_SIZE');root=os.getpid()
        def rss(pid):
            try:return int(Path(f'/proc/{pid}/statm').read_text().split()[1])*pages
            except (FileNotFoundError,ProcessLookupError,PermissionError):return 0
        def tree(pid):
            try:children=Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
            except (FileNotFoundError,ProcessLookupError,PermissionError):children=[]
            return rss(pid)+sum(tree(int(c)) for c in children)
        def sample():
            while not self.stop.is_set():
                self.maximum=max(self.maximum,tree(root));self.controller_maximum=max(self.controller_maximum,rss(root));self.samples+=1
                self.stop.wait(.02)
        self.thread=threading.Thread(target=sample,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join()


def execute():
    if os.name=='nt':raise ValueError('execute in existing WSL environment for process-group RSS')
    if (RAW/'execution_start.json').exists():raise ValueError('exclusive one step; no rerun')
    q=read(DOC/'protocol.json')
    if sha(DOC/'protocol.json')!=read(DOC/'protocol_seal.json')['sha256']:raise ValueError('protocol drift')
    write(RAW/'execution_start.json',dict(protocol_sha256=sha(DOC/'protocol.json'),steps_requested=1))
    begin=time.perf_counter();validation=0.;scalar=0.;new=[];blocker=None;result={}
    with Memory() as memory:
        try:
            t=time.perf_counter();verify(q['protected_sha256']);verify(q['implementation_sha256']);verify(q['preflight_sha256']);validation+=time.perf_counter()-t
            reused=[read(hostpath(p)) for p in q['reuse_paths']]
            t=time.perf_counter();initial=start(*reused,q['mass']['literal_value']);scalar+=time.perf_counter()-t
            if initial!=q['initial_state']:raise ValueError('initial state preseal mismatch')
            for label in q['new_call_order']:
                process=RAW/('process_'+label);process.mkdir();output=RAW/label
                argv=['/usr/bin/time','-f','wall_seconds=%e\npeak_rss_kib=%M\nuser_seconds=%U\nsystem_seconds=%S',
                    '-o',str(process/'native.time'),'/usr/bin/timeout','300',sys.executable,'-m','electronic_pilot.h2_nuclear_v0.worker',
                    '--label',label,'--protocol',str(DOC/'protocol.json'),'--output',str(output)]
                env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
                t=time.perf_counter()
                with (process/'stdout').open('xb') as out,(process/'stderr').open('xb') as err:
                    p=subprocess.run(argv,stdout=out,stderr=err,env=env,timeout=330)
                outer=time.perf_counter()-t
                measured={}
                for line in (process/'native.time').read_text().splitlines():
                    if '=' in line:
                        k,v=line.split('=',1);measured[k]=float(v)
                metadata=dict(argv=argv,exit=p.returncode,outer_wall_seconds=outer,measurement=measured)
                write(process/'process.json',metadata)
                if p.returncode:raise ValueError('new electronic process failure '+label)
                row=read(output/'result.json');row['process']=metadata;new.append(row);write(DOC/('point_'+label+'.json'),row)
                print('POINT',label,row['numerical_guard_status'],row['total_energy_hartree'],flush=True)
                if not row['accepted']:raise ValueError('new geometry REFUSED '+label)
            t=time.perf_counter();result=finish(initial,*new);scalar+=time.perf_counter()-t
            t=time.perf_counter();result['independent_scalar_check']=check(result,reused,new,q['mass']['literal_value']);verify(q['protected_sha256']);verify(q['implementation_sha256']);validation+=time.perf_counter()-t
        except Exception as exc:
            blocker=repr(exc);result=dict(classification='H2_NUCLEAR_1STEP_BLOCKED',first_blocker=blocker,
                committed_nuclear_step=False,NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True)
        incremental=time.perf_counter()-begin
    historical=sum(row['process']['measurement']['wall_seconds'] for row in reused) if 'reused' in locals() else None
    result.update(new_points=new,first_blocker=blocker,incremental_one_step_wall_seconds=incremental,
        new_electronic_process_wall_sum_seconds=sum(x['process']['measurement']['wall_seconds'] for x in new),
        validation_wall_seconds=validation,scalar_integration_wall_seconds=scalar,
        workflow_sampled_aggregate_peak_rss_bytes=memory.maximum,controller_sampled_peak_rss_bytes=memory.controller_maximum,
        memory_samples=memory.samples,memory_scope=q['memory'],
        new_electronic_calls_completed=len(new),reused_electronic_points=3,new_initial_electronic_calls=0,
        cold_start_equivalent=dict(status='ESTIMATED_FROM_PREVIOUS_MEASURED_INITIAL_COST_PLUS_CURRENT_INCREMENTAL_NOT_FRESH_COLD_RUN',
            initial_three_process_wall_seconds=historical,equivalent_wall_seconds=None if historical is None else historical+incremental,
            caveat='previous same-host three process timings; run times differ, excludes old validation/startup cost; not a prediction bound'),
        protected_bindings_count=len(q['protected_sha256']),protected_unchanged=blocker is None,
        energy_error_bounds=False,force_error_bounds=False,production_approval=False,stop_after_one_step=True)
    write(DOC/'results.json',result)
    bindings={p.as_posix():sha(p) for p in RAW.rglob('*') if p.is_file()}
    bindings.update({p.as_posix():sha(p) for p in DOC.glob('*') if p.is_file()})
    write(DOC/'execution_seal.json',dict(bound_sha256=bindings,stopped_after_requested_one_step=True))
    print(result['classification'],'STOP / no second step',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','execute'))
    {'prepare':prepare,'execute':execute}[p.parse_args().stage]()
