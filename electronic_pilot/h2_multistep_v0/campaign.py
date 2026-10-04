"""Exactly five added steps; scheduled full provenance only start/end."""
import argparse,datetime,json,os,shutil,subprocess,sys,time
from pathlib import Path
from .scalar import drift,finish,diagnostic
from .kit import quick,diagnostic_check,decide,cadence,verify,persist,sha,hostpath,electronic
from electronic_pilot.h2_nuclear_v0.campaign import Memory

DOC=Path('docs/active/h2_multistep_layered_v0')
RAW=Path('runs/h2_multistep_layered_v0_20261004')
OLD=Path('docs/active/h2_nuclear_1step_v0')
PYTHON='/home/otherside123/.venvs/h2-reference-pilot/bin/python'

def read(path):return json.loads(hostpath(path).read_text(encoding='utf8'))

class ElectronicCallFailure(ValueError):
    def __init__(self,metadata):
        super().__init__('electronic process failure '+str(metadata.get('failure',metadata['exit'])))
        self.outer_wall_seconds=metadata['outer_wall_seconds']

def run_process(argv,folder,env=None,timeout=330,cwd=None):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();failure=None;launched=True;exit_code=None
    with (folder/'stdout').open('xb') as out,(folder/'stderr').open('xb') as err:
        try:exit_code=subprocess.run(argv,env=env,stdout=out,stderr=err,timeout=timeout,cwd=cwd or folder).returncode
        except subprocess.TimeoutExpired as exc:failure=repr(exc)
        except OSError as exc:failure=repr(exc);launched=False
    outer=time.perf_counter()-start;measurement={}
    if (folder/'native.time').exists():
        try:
            for line in (folder/'native.time').read_text().splitlines():
                if '=' in line:
                    key,value=line.split('=',1);measurement[key]=float(value)
        except Exception as exc:failure='timing parse failure '+repr(exc)
    metadata=dict(argv=argv,exit=exit_code,failure=failure,launched=launched,outer_wall_seconds=outer,measurement=measurement)
    persist(folder/'process.json',metadata)
    return metadata

def full_audit(bindings,receipts,c0=None,steps=None,mass=None,snapshot_root=None):
    start=time.perf_counter()
    try:
        count=verify(bindings)
        count+=verify({x['path']:x['sha256'] for x in receipts})
        if c0 is not None:
            previous=c0
            for step in steps:
                quick(previous,step,mass,snapshot_root);previous=step
        return dict(passed=True,checked_bindings=count,wall_seconds=time.perf_counter()-start,
            scalar_chain_replayed=0 if steps is None else len(steps),external_independent_audit=False)
    except Exception as exc:
        return dict(passed=False,failure=repr(exc),wall_seconds=time.perf_counter()-start,external_independent_audit=False)

def run_segment(c0,mass,c0_H,call,record,snapshot_root):
    steps=[];timings=[];diagnostics=[];receipts=[];previous=c0
    for index in range(1,6):
        elapsed=dict(quick=0.,scalar=0.,electronic=0.,center=0.);points=[];completed=False
        def timed(phase,function,*args):
            t=time.perf_counter()
            try:return function(*args)
            finally:elapsed[phase]+=time.perf_counter()-t
        def stencil_call(label,requested):
            t=time.perf_counter()
            try:row=call(index,label,requested)
            except Exception as exc:
                elapsed['electronic']+=getattr(exc,'outer_wall_seconds',time.perf_counter()-t);raise
            elapsed['electronic']+=row['process']['outer_wall_seconds'];return row
        try:
            half=timed('scalar',drift,previous,mass)
            for label in ('left','right'):
                row=stencil_call(label,half['requested_geometries'][label])
                points.append(row)
                timed('quick',electronic,row)
            state=timed('scalar',finish,previous,half,*points,mass)
            state['step_index']=index;state['previous_state']={k:previous[k] for k in ('R','P','F')}
            state['quick']=timed('quick',quick,previous,state,mass,snapshot_root)
            receipt=timed('quick',record,index,state)
            receipts.append(receipt);steps.append(state)
            if index in (3,5):
                def center_check():
                    center=call(index,'center',state['R']);diag=diagnostic(state,center,mass,c0_H)
                    diagnostic_check(state,center,mass,c0_H,diag,snapshot_root)
                    return center,diag
                center,diag=timed('center',center_check)
                diagnostics.append(dict(step_index=index,point=center,values=diag,wall_seconds=elapsed['center']))
            completed=True;previous=state
            print('STEP',index,'QUICK_KIT_PASS','R',state['R'],'P',state['P'],'SPECULATIVE',flush=True)
        except Exception as exc:
            return dict(steps=steps,timings=timings,diagnostics=diagnostics,receipts=receipts,quick_ok=False,
                event='QUICK_KIT_TRIGGERED_STOP',failed_step_index=index,failure=repr(exc))
        finally:
            timings.append(dict(step_index=index,completed=completed,electronic_pair_wall_seconds=elapsed['electronic'],
                scalar_seconds=elapsed['scalar'],raw_dynamics_seconds=elapsed['electronic']+elapsed['scalar'],quick_kit_seconds=elapsed['quick'],
                checkpoint_center_and_diagnostic_seconds=elapsed['center'],
                electronic_pair_peak_rss_kib=max((x['process']['measurement'].get('peak_rss_kib',0) for x in points),default=0)))
    return dict(steps=steps,timings=timings,diagnostics=diagnostics,receipts=receipts,quick_ok=True)

def prepare():
    if DOC.exists() or RAW.exists():raise ValueError('exclusive new campaign required')
    start=time.perf_counter()
    import xml.etree.ElementTree as ET
    suite=ET.parse('runs/h2_multistep_preflight_v3_20261004.xml').getroot().find('testsuite')
    if any(int(suite.get(k)) for k in ('failures','errors','skipped')):raise ValueError('preflight not green')
    old=read(OLD/'protocol.json');result=read(OLD/'results.json')
    if result['classification']!='H2_BO_NUCLEAR_1STEP_SUPPORTED':raise ValueError('C0 unavailable')
    mutable={'CURRENT_STATE.md','REPO_MAP.md','docs/reference/VERIFICATION_LIMITS_AND_LESSONS.md'}
    protected={**old['protected_sha256'],**old['implementation_sha256'],**old['preflight_sha256'],
        **read(OLD/'execution_seal_rebound_v1.json')['bound_sha256'],
        **{p:h for p,h in read(OLD/'completion_seal.json')['bound_sha256'].items() if p not in mutable}}
    for folder in (str(OLD),'electronic_pilot/h2_nuclear_v0','tests/h2_nuclear_v0'):
        for p in Path(folder).glob('*'):
            if p.is_file():protected.setdefault(p.as_posix(),sha(p))
    c0=dict(R=result['R1_requested'],P=result['P1'],F=result['F1'],nuclei=result['nuclei'],
        H_total=result['H1'],E_center=result['E1'],K=result['K1'],state_status='CONFIRMED',
        scope='trusted checkpoint within exploratory Pilot only, not canonical A certification',
        actual_geometry=result['R1_actual'],source_result_sha256=sha(OLD/'results.json'))
    DOC.mkdir();RAW.mkdir();snapshot=RAW/'snapshot';snapshot.mkdir()
    source={p.as_posix():sha(p) for folder in ('electronic_pilot/h2_multistep_v0','tests/h2_multistep_v0')
        for p in Path(folder).glob('*') if p.is_file()}
    source['docs/superpowers/plans/2026-10-04-h2-layered-validation.md']=sha('docs/superpowers/plans/2026-10-04-h2-layered-validation.md')
    paths=[str(p) for p in Path('electronic_pilot/h2_multistep_v0').glob('*.py')]
    paths+=['electronic_pilot/'+name for name in ('__init__.py','solver.py','ao_micro_v0/__init__.py','ao_micro_v0/reuse.py',
        'numerical_cause/__init__.py','numerical_cause/core.py','h2_force_v0/__init__.py','h2_force_v0/interface.py',
        'h2_nuclear_v0/__init__.py','h2_nuclear_v0/scalar.py','h2_nuclear_v0/check.py','h2_nuclear_v0/campaign.py',
        'frontend_reference_v0/__init__.py','frontend_reference_v0/audit.py')]
    for name in paths:
        p=Path(name);target=snapshot/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    shutil.copyfile('electronic_pilot/h2_multistep_v0/launch.py',snapshot/'launch.py')
    (snapshot/'config').mkdir()
    shutil.copyfile('runs/h2_nuclear_1step_v0_20261004/basis_definitions.json',snapshot/'config/basis.json')
    shutil.copyfile('electronic_pilot/h2_nuclear_v0/mass.json',snapshot/'config/mass.json')
    persist(snapshot/'config/c0.json',c0);persist(DOC/'C0.json',c0)
    protocol=dict(sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),local_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        additional_steps=5,dt='1',h='0.1',precision=80,mass=read(snapshot/'config/mass.json'),
        C0=c0,C0_force_recalculated=False,new_stencil_calls=10,new_center_calls=2,center_steps=[3,5],
        domain=['1.2','1.6'],domain_scope='nuclear relative coordinate; sampled local domain is not interval certification',
        electronic='same cc-pV5Z/full singlet CI6105 / AO110 / canonical reuse / Cholesky / evr roots0,1 / binary64 / one thread / unchanged guards',
        snapshot_root=snapshot.as_posix(),protected_sha256=protected,implementation_sha256=source,
        exclusions_from_historical_dashboard_bindings=sorted(mutable),
        quick='guards/finite/domain/geometry/Fraction equations/COM/p sum/state roundtrip+hash only; no historical scan or pytest',
        medium='additional step3 center E+K+H+deltaH from C0; MEASURED only; no promotion',
        full='start/end historical+source+protocol+snapshot bytes; end includes new point/state hashes and whole scalar chain',
        authority='SPECULATIVE until final audit PASS; final failure leaves C0 authoritative and DISCARDED descendants preserved; no automatic retry',
        physical_certification=False,NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True,
        snapshot_limit='Python sources/raw basis/mass/protocol copied; external Python/PySCF/NumPy/SciPy/native libraries remain existing trusted runtime and registered historical hashes; no tamper-proof execution attestation',
        cadence_model='one measured end-audit cost/K with K1,5,10,50,100; start cost reported separately; not selected',
        forbidden=['more than5 added steps','adaptive dt/h','force formula changes','calculator optimization','JC/B2/adaptive representation','merge/rebase/push'])
    persist(DOC/'protocol.json',protocol);shutil.copyfile(DOC/'protocol.json',snapshot/'config/protocol.json')
    bindings={p.as_posix():sha(p) for p in snapshot.rglob('*') if p.is_file()}
    persist(DOC/'snapshot_seal.json',dict(bound_sha256=bindings,protocol_sha256=sha(DOC/'protocol.json'),sealed_before_new_energies=True))
    for name in ('h2_multistep_preflight_v3_20261004.log','h2_multistep_preflight_v3_20261004.xml','h2_multistep_kit_green_20261004.log','h2_multistep_kit_green_20261004.xml'):
        shutil.copyfile(Path('runs')/name,DOC/name)
    persist(DOC/'prepare_receipt.json',dict(wall_seconds=time.perf_counter()-start,snapshot_files=len(bindings),
        registered_historical_bindings=len(protected),no_new_electronic_calls=True,setup_excluded_from_execute_wall=True))
    print('SEALED SNAPSHOT',len(bindings),'HISTORICAL',len(protected),'C0 reused; new calls planned12',flush=True)

def execute(expected_seal_sha):
    if os.name=='nt':raise ValueError('execute in existing WSL runtime')
    if (RAW/'execution_start.json').exists():raise ValueError('exclusive execution; no rerun')
    if sha(DOC/'snapshot_seal.json')!=expected_seal_sha:raise ValueError('pre-dispatch snapshot seal drift')
    snapshot=(RAW/'snapshot').resolve();q=read(snapshot/'config/protocol.json');seal=read(DOC/'snapshot_seal.json')
    persist(RAW/'execution_start.json',dict(protocol_sha256=sha(snapshot/'config/protocol.json'),steps_requested=5))
    bindings={**q['protected_sha256'],**q['implementation_sha256'],**seal['bound_sha256'],
        (DOC/'protocol.json').as_posix():seal['protocol_sha256'],(DOC/'snapshot_seal.json').as_posix():expected_seal_sha,
        (DOC/'C0.json').as_posix():seal['bound_sha256'][(RAW/'snapshot/config/c0.json').as_posix()]}
    begin=time.perf_counter();call_receipts=[];calls=[];launches=[]
    with Memory() as memory:
        start_audit=full_audit(bindings,[])
        if start_audit['passed']:
            if sha(snapshot/'config/protocol.json')!=seal['protocol_sha256']:raise ValueError('snapshot protocol')
            def call(index,label,requested):
                folder=RAW/f'call_{index}_{label}';folder.mkdir();request=folder/'request.json'
                item=persist(request,dict(step_index=index,label=label,requested_R=requested));output=folder/'electronic'
                argv=['/usr/bin/time','-f','wall_seconds=%e\npeak_rss_kib=%M\nuser_seconds=%U\nsystem_seconds=%S','-o',str(folder/'native.time'),
                    '/usr/bin/timeout','300',sys.executable,'-I',str(snapshot/'launch.py'),'worker',
                    '--request',str(request),'--sha',item['sha256'],'--snapshot',str(snapshot),'--output',str(output)]
                env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
                meta=run_process(argv,folder,env=env,cwd=Path.cwd())
                launches.append(dict(step_index=index,label=label,process=meta))
                for path in folder.rglob('*'):
                    if path.is_file():call_receipts.append(dict(path=path.as_posix(),sha256=sha(path)))
                if meta['exit']!=0 or meta['failure']:raise ElectronicCallFailure(meta)
                row=read(output/'result.json');row['process']=meta;calls.append(row)
                call_receipts.append(persist(DOC/f'point_{index}_{label}.json',row))
                print('CALL',index,label,row['numerical_guard_status'],flush=True)
                return row
            def record(index,state):
                return persist(RAW/f'state_{index}.json',state)
            segment=run_segment(q['C0'],q['mass']['literal_value'],q['C0']['H_total'],call,record,snapshot.as_posix())
            end_audit=full_audit(bindings,call_receipts+segment['receipts'],q['C0'],segment['steps'],q['mass']['literal_value'],snapshot.as_posix())
            expected_calls=[[i,label] for i in range(1,6) for label in (('left','right','center') if i in (3,5) else ('left','right'))]
            if segment['quick_ok'] and [[x['step_index'],x['label']] for x in calls]!=expected_calls:
                end_audit.update(passed=False,failure='actual call sequence/count mismatch')
        else:
            segment=dict(steps=[],timings=[],diagnostics=[],receipts=[],quick_ok=False,event='START_AUDIT_FAILED',failure=start_audit.get('failure'))
            end_audit=dict(passed=False,wall_seconds=0.,not_run='start audit failed; electronic calls0')
        decision=decide(q['C0'],segment['steps'],end_audit['passed'],segment['quick_ok'])
        wall=time.perf_counter()-begin
    timings=segment['timings'];cost=dict(
        raw_dynamics_seconds=sum(x['raw_dynamics_seconds'] for x in timings),
        electronic_pair_seconds=sum(x['electronic_pair_wall_seconds'] for x in timings),
        scalar_seconds=sum(x['scalar_seconds'] for x in timings),quick_kit_seconds=sum(x['quick_kit_seconds'] for x in timings),
        medium_check_seconds=sum(x['checkpoint_center_and_diagnostic_seconds'] for x in timings if x['step_index']==3),
        final_checkpoint_seconds=sum(x['checkpoint_center_and_diagnostic_seconds'] for x in timings if x['step_index']==5),
        full_audit_start_seconds=start_audit['wall_seconds'],full_audit_end_seconds=end_audit['wall_seconds'],
        campaign_wall_seconds=wall,clock='time.perf_counter; outer wall includes process launch/capture; packaging/test/setup excluded')
    cost['other_seconds']=wall-sum(cost[k] for k in ('raw_dynamics_seconds','quick_kit_seconds','medium_check_seconds','final_checkpoint_seconds','full_audit_start_seconds','full_audit_end_seconds'))
    result=dict(classification='H2_MULTISTEP_LAYERED_VALIDATION_PILOT_SUPPORTED' if decision['promoted'] else 'H2_MULTISTEP_LAYERED_VALIDATION_BLOCKED',
        C0=q['C0'],segment=segment,decision=decision,start_full_audit=start_audit,end_full_audit=end_audit,
        actual_electronic_calls=sum(x['process']['launched'] for x in launches),electronic_results_completed=len(calls),
        process_launches=launches,actual_call_sequence=[[x['step_index'],x['label']] for x in launches],C0_force_recalculated=False,
        new_calls=calls,cost=cost,cadence_model=cadence(end_audit['wall_seconds']),final_K_selected=None,
        memory=dict(workflow_sampled_aggregate_peak_rss_bytes=memory.maximum,controller_sampled_peak_rss_bytes=memory.controller_maximum,
            samples=memory.samples,scope='20ms Linux controller+descendant RSS sum; shared-page double count possible, intervals may miss peaks; no Windows/whole-host claim'),
        controller_runtime_module_origins={name:Path(module.__file__).resolve().as_posix() for name,module in list(sys.modules.items())
            if name.startswith('electronic_pilot') and getattr(module,'__file__',None)},
        NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True,energy_conservation_tolerance=None,stop_after_five_additional_steps=True,
        physical_accuracy_equivalence_claim=False,old_comparison='historical one-step140.271748s/three calls87.506782s/validation52.684139s; two calls vs three and cadence both change; no controlled equivalence claim')
    persist(DOC/'results.json',result);persist(DOC/'authority_decision.json',decision)
    persist(DOC/'execution_seal.json',dict(bound_sha256={p.as_posix():sha(p) for folder in (RAW,DOC) for p in folder.rglob('*') if p.is_file()},
        preserve_SPECULATIVE_records=True,promotion_in_separate_decision=True,stopped=True))
    print(result['classification'],'STOP',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare']);p.parse_args();prepare()
