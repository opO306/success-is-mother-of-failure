"""Mock-only checks for the V12.4 A package revision 2 gate: no network, no Vast CLI, no SSH, no physics.

Real files: the original tablet_814.zip and revision 2 must exist at their repository paths (byte-exact).
Run with --basetemp on a drive with ~1 GB free (forged packages are written there).
"""
import hashlib,importlib.util,json,subprocess,sys,textwrap,uuid,zipfile
from pathlib import Path
import pytest
import package_v2 as P

HERE=Path(__file__).resolve().parents[1]
CONTROLLER=HERE.parent/'revision_v12/transport/controller.py'
ORIGINAL_GUEST=HERE.parent/'revision_v12/transport/guest_source_verify.py'


def sha(data):return hashlib.sha256(data).hexdigest()


def load_controller(patch=True):
    spec=importlib.util.spec_from_file_location('ctl_'+uuid.uuid4().hex,CONTROLLER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return P.patch_controller(module) if patch else module


def run(body):
    code=textwrap.dedent(f'''
        import sys;sys.path.insert(0,{str(HERE)!r})
        import fresh_owned,package_v2
    ''')+textwrap.dedent(body)
    result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return result.stdout


def forge(tmp_path,changes,name):
    """Revision 2 with member replacements; returns (zip path, inventory path) with a consistent inventory."""
    old,new=P.bindings()
    out=tmp_path/name
    with zipfile.ZipFile(P.ROOT/new['A']['archive']) as z,zipfile.ZipFile(out,'x',zipfile.ZIP_STORED) as w:
        for info in z.infolist():w.writestr(info.filename,changes.get(info.filename,z.read(info.filename)))
    with zipfile.ZipFile(out) as z:
        files={i.filename:sha(z.read(i.filename)) for i in z.infolist()};size=sum(i.file_size for i in z.infolist())
    inventory=dict(json.loads((P.ROOT/new['A']['inventory']).read_bytes()),files=files,uncompressed_bytes=size,zip_sha256=sha(out.read_bytes()))
    inv=tmp_path/(name+'.inventory.json');inv.write_bytes(json.dumps(inventory,sort_keys=True,indent=2).encode())
    return out,inv


def point_at(module,zip_path,inv_path):
    module.SOURCE,module.INVENTORY=zip_path,inv_path
    module.ZIP_HASH,module.INVENTORY_HASH=sha(zip_path.read_bytes()),sha(inv_path.read_bytes())


def forge_all_pins(monkeypatch,tmp_path,zip_path,inv_path):
    """Forge every pin (bindings file, code seal, test hash) so only the exact-diff gate can still refuse."""
    old,new=P.bindings()
    with zipfile.ZipFile(zip_path) as z:code=sha(z.read(P.SEAL));test=sha(z.read(P.TEST))
    A=dict(new['A'],archive=str(zip_path),inventory=str(inv_path),zip_sha256=sha(zip_path.read_bytes()),
           inventory_sha256=sha(inv_path.read_bytes()),code_sha256=code)
    raw=json.dumps(dict(A=A,B=new['B'])).encode();path=tmp_path/'forged_bindings.json';path.write_bytes(raw)
    for name,value in (('V2_BINDINGS',path),('V2_BINDINGS_SHA256',sha(raw)),('V2_CODE',code),('V2_TEST',test)):
        monkeypatch.setattr(P,name,value)


def test_bindings_are_pinned_and_b_is_original(tmp_path,monkeypatch):
    old,new=P.bindings()
    assert new['B']==old['B'] and new['A']['code_sha256']==P.V2_CODE and old['A']['code_sha256']==P.ORIGINAL_CODE
    assert {k:new['A'][k] for k in ('protocol_sha256','case_inventory_sha256','addition_sha256','expected_tests','entries')}== \
           {k:old['A'][k] for k in ('protocol_sha256','case_inventory_sha256','addition_sha256','expected_tests','entries')}
    copy=tmp_path/'b.json';copy.write_bytes(P.V2_BINDINGS.read_bytes().replace(b'"expected_tests": 320',b'"expected_tests": 319'))
    monkeypatch.setattr(P,'V2_BINDINGS',copy)
    with pytest.raises(ValueError,match='REVISION_2_BINDINGS_DRIFT'):P.bindings()


def test_revision_files_and_original_package_pins():
    result=P.verify_revision_files()
    assert result['original_zip_sha256']=='be06c9a7b8cc31c1e414b03f85485a9bb5e9e69226e34f1917553fac2673f4ff'
    assert result['revision_2_zip_sha256']==P.bindings()[1]['A']['zip_sha256']


def test_controller_gate_accepts_revision_2():
    m=load_controller();m.configure('A')
    assert m.CODE==P.V2_CODE and m.SPEC==P.bindings()[1]['A'] and m.SOURCE.name=='tablet_814_v2.zip'
    result=m.verify_local_package()
    assert result['changed_members']==sorted((P.SEAL,P.TEST)) and result['revision_of_zip_sha256'].startswith('be06c9a7')


def test_unpatched_original_controller_still_refuses_revision_2():
    """The original V12 gate is not loosened: pointed at revision 2 it refuses (it requires the original seal)."""
    m=load_controller(patch=False);m.configure('A')
    _,new=P.bindings();point_at(m,P.ROOT/new['A']['archive'],P.ROOT/new['A']['inventory'])
    with pytest.raises(ValueError,match='PRESERVE_813_PLUS_EXACT_EXISTING_SEAL|INVENTORY_PACKAGE_SCOPE|PACKAGE_CRC'):m.verify_local_package()


def test_controller_gate_refuses_original_package():
    m=load_controller();m.configure('A')
    old,_=P.bindings();point_at(m,P.ROOT/old['A']['archive'],P.ROOT/old['A']['inventory'])
    with pytest.raises(ValueError,match='REVISION_2_CODE_SEAL_PIN'):m.verify_local_package()


def test_controller_gate_refuses_one_member_tamper(tmp_path):
    m=load_controller();m.configure('A')
    with zipfile.ZipFile(P.ROOT/P.bindings()[1]['A']['archive']) as z:data=z.read('a_numeric/exp.py')
    point_at(m,*forge(tmp_path,{'a_numeric/exp.py':data+b'\n'},'tamper.zip'))
    with pytest.raises(ValueError,match='PRESERVE_813_PLUS_EXACT_EXISTING_SEAL'):m.verify_local_package()


def test_exact_diff_gate_refuses_third_member_even_with_all_pins_forged(tmp_path,monkeypatch):
    _,new=P.bindings()
    with zipfile.ZipFile(P.ROOT/new['A']['archive']) as z:exp=z.read('a_numeric/exp.py');seal=z.read(P.SEAL)
    seal=seal.replace(sha(exp).encode(),sha(exp+b'\n').encode())
    zip_path,inv=forge(tmp_path,{'a_numeric/exp.py':exp+b'\n',P.SEAL:seal},'third.zip')
    forge_all_pins(monkeypatch,tmp_path,zip_path,inv)
    m=load_controller();m.configure('A')
    with pytest.raises(ValueError,match='REVISION_2_EXACT_TWO_MEMBER_DIFF'):m.verify_local_package()


def test_exact_diff_gate_refuses_other_test_edit_even_with_all_pins_forged(tmp_path,monkeypatch):
    _,new=P.bindings()
    with zipfile.ZipFile(P.ROOT/new['A']['archive']) as z:test=z.read(P.TEST);seal=z.read(P.SEAL)
    weaker=test.replace(b'    assert len(hits)==1 and accessed==[]\n',b'    assert len(hits)==1\n')
    assert weaker!=test
    zip_path,inv=forge(tmp_path,{P.TEST:weaker,P.SEAL:seal.replace(P.V2_TEST.encode(),sha(weaker).encode())},'weaker.zip')
    forge_all_pins(monkeypatch,tmp_path,zip_path,inv)
    m=load_controller();m.configure('A')
    with pytest.raises(ValueError,match='REVISION_2_APPROVED_TEST_BLOCK_ONLY'):m.verify_local_package()


def test_kind_b_keeps_original_configuration_and_gate():
    spec=importlib.util.spec_from_file_location('ctl_b',CONTROLLER)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.verify_local_package=lambda:'ORIGINAL_B_GATE'
    P.patch_controller(m);m.configure('B')
    assert m.SPEC==P.bindings()[0]['B'] and m.verify_local_package()=='ORIGINAL_B_GATE'


class Recorder:
    def __init__(self):self.calls=[]
    def control(self,required,phase_deadline=None):self.calls.append(('control',required))
    def run(self,argv,name,timeout,input=None):self.calls.append(('run',argv,name,timeout,input));return b'{}'


def bare(cls):
    t=object.__new__(cls);r=Recorder();t.control=r.control;t.run=r.run;t.ssh_argv=['ssh','-p','1','root@h']
    return t,r


def test_guest_verifier_redirect_keeps_original_command_shape():
    args=['/workspace/g','z','i','c','p','A']
    m=load_controller();m.configure('A');t,r=bare(m.Transport)
    t.py_once('guest_source_verify.py',args,'source_verify',25)
    o=load_controller(patch=False);o.configure('A');u,s=bare(o.Transport)
    u.py_once('guest_source_verify.py',args,'source_verify',25)
    assert r.calls[0]==s.calls[0]                                # same control budget
    assert r.calls[1][:4]==s.calls[1][:4]                        # same ssh argv, name, timeout
    assert r.calls[1][4]==P.GUEST_V2.read_bytes() and s.calls[1][4]==ORIGINAL_GUEST.read_bytes()
    t2,r2=bare(m.Transport);t2.py_once('guest_recover.py',['x'],'recover',10)
    assert r2.calls[1][4]==(CONTROLLER.parent/'guest_recover.py').read_bytes()   # other scripts untouched


def test_transport_binding_and_source_preflight_wrappers():
    out=run('''
        import campaign
        old,new=package_v2.bindings()
        keys=package_v2.BINDING_KEYS
        campaign.transport_binding=lambda policy,kind,owner,out,B:dict({k:old[kind][k] for k in keys},kind=kind)
        campaign.source_preflight=lambda policy:'ORIGINAL_CHECKED'
        package_v2.install_campaign(campaign);package_v2.install_campaign(campaign)
        a=campaign.transport_binding(None,'A',None,None,None);b=campaign.transport_binding(None,'B',None,None,None)
        assert {k:a[k] for k in keys}=={k:new['A'][k] for k in keys} and a['package_revision']=='TABLET_A_V2_ONE_TEST_ORDER_FIX'
        assert b==dict({k:old['B'][k] for k in keys},kind='B')
        assert campaign.source_preflight({})=='ORIGINAL_CHECKED'
        import importlib
        c=importlib.reload(campaign)
        c.transport_binding=lambda policy,kind,owner,out,B:dict({k:new['A'][k] for k in keys})
        package_v2.install_campaign(c)
        try:c.transport_binding(None,'A',None,None,None);print('accepted')
        except ValueError as e:print(e)''')
    assert out.strip()=='V12_ORIGINAL_BINDING_SHAPE'


def test_recovery_maps_original_a_to_revision_2_and_refuses_unknown():
    out=run('''
        import terminal_proof
        seen=[]
        terminal_proof.require_terminal=lambda files,*,writer_completion_verified,spec,original_case_ids=None:seen.append(spec) or 'ok'
        package_v2.install_recovery();package_v2.install_recovery()
        old,new=package_v2.bindings()
        assert terminal_proof.require_terminal({},writer_completion_verified=True,spec=old['A'])=='ok' and seen[-1]==new['A']
        assert terminal_proof.require_terminal({},writer_completion_verified=True,spec=old['B'])=='ok' and seen[-1]==old['B']
        for bad in (new['A'],{}):
            try:terminal_proof.require_terminal({},writer_completion_verified=True,spec=bad);print('accepted')
            except ValueError as e:print(e)''')
    assert out.split()==['V12_4_UNKNOWN_PACKAGE_SPEC']*2


def test_real_terminal_proof_uses_revision_2_code(tmp_path):
    """Original require_terminal + wrapper: a revision-2 status passes, an original-code status is refused."""
    out=run(r'''
        import json,terminal_proof
        from xml.sax.saxutils import quoteattr
        package_v2.install_recovery()
        old,new=package_v2.bindings()
        ids=json.loads(open(package_v2.ROOT/old['A']['case_inventory'],'rb').read())['ids']
        cases=''.join('<testcase classname=%s name=%s/>'%tuple(map(quoteattr,i.split('::',1))) for i in ids)
        def files(code):
            status=dict(status='PASS',tests=320,code_sha256=code,protocol_sha256=old['A']['protocol_sha256'],failed=0,errors=0,skipped=0,
                        physics_calls=0,gpu_calls=0,wall_ns=1,cpu_ns=1,benchmark_complete=True)
            bench=dict(complete=True,repeats=31,index_growth=[dict(records=n) for n in (100,1000,10000)],physics_calls=0,gpu_calls=0)
            return {'gate_exit.json':json.dumps(dict(returncode=0,error=None)).encode(),'output/status.json':json.dumps(status).encode(),
                    'output/junit.xml':('<testsuites><testsuite>'+cases+'</testsuite></testsuites>').encode(),
                    'output/physics_guard.json':json.dumps(dict(blocked_attempts=[],new_physics_calls=0,gpu_calls=0)).encode(),
                    'output/benchmark.json':json.dumps(bench).encode()}
        r=terminal_proof.require_terminal(files(package_v2.V2_CODE),writer_completion_verified=True,spec=old['A'],original_case_ids=ids)
        print(r['tests'])
        try:terminal_proof.require_terminal(files(package_v2.ORIGINAL_CODE),writer_completion_verified=True,spec=old['A'],original_case_ids=ids);print('accepted')
        except ValueError as e:print(e)''')
    assert out.split()==['320','IMPORTANT_FINAL_SOURCE_BINDING']


def test_watchdog_bridge_installs_recovery_and_v12_5_authority(tmp_path):
    fake=tmp_path/'fake_watchdog.py'
    fake.write_text('import terminal_proof,cleanup,lifecycle,execution_authority,authority,reads\n'
                    'print(getattr(terminal_proof.require_terminal,"v12_4_wrapped",False),getattr(cleanup.verify_admin,"v12_3_wrapped",False),'
                    'lifecycle.Provider is reads.ReadRetryProvider,execution_authority.require_claim is authority.require_claim,authority.SCHEMA)\n')
    out=run(f'''
        import process_bridge
        from pathlib import Path
        process_bridge.TARGETS['watchdog']=Path({str(fake)!r})
        sys.argv=['process_bridge.py','watchdog']
        process_bridge.main()''')
    assert out.split()==['True','True','True','True','V12_5_ACTUAL_BUNDLED_PAID_APPROVAL']


def test_full_preflight_through_campaign_loader():
    out=run('''
        campaign=fresh_owned.install_all()
        gate=package_v2.preflight(campaign,fresh_owned.CONTROLLER)
        print(gate['package']['zip_sha256']==package_v2.bindings()[1]['A']['zip_sha256'],len(gate['package']['changed_members']))
        spec=campaign.importlib.util.spec_from_file_location('delegated_transport',fresh_owned.CONTROLLER)
        m=campaign.importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure('A')
        print(m.Transport.__name__,[c.__name__ for c in m.Transport.__mro__][:3])''')
    first,second=out.strip().split('\n')
    assert first=='True 2'
    assert second.startswith("ReadTransport ['ReadTransport', 'ConfirmedDisconnectTransport', 'PackageRevision2Transport']")


GUEST_ARGS=lambda new:[new['zip_sha256'],new['inventory_sha256'],new['code_sha256'],new['protocol_sha256'],'A']


def guest(tmp_path,name,script,zip_path,inv_path,args):
    g=tmp_path/name;g.mkdir()
    (g/'source.zip').write_bytes(Path(zip_path).read_bytes());(g/'inventory.json').write_bytes(Path(inv_path).read_bytes())
    r=subprocess.run([sys.executable,'-B','-',str(g),*args],input=Path(script).read_bytes(),capture_output=True,cwd=g)
    return r.returncode,(r.stdout+r.stderr).decode(errors='replace')


def test_guest_v2_accepts_revision_2(tmp_path):
    _,new=P.bindings();A=new['A']
    code,text=guest(tmp_path,'g_ok',P.GUEST_V2,P.ROOT/A['archive'],P.ROOT/A['inventory'],GUEST_ARGS(A))
    assert code==0 and '"status": "RAW_SOURCE_VERIFIED"' in text,text


def test_guest_v2_refuses_original_package(tmp_path):
    old,_=P.bindings();A=old['A']
    code,text=guest(tmp_path,'g_orig',P.GUEST_V2,P.ROOT/A['archive'],P.ROOT/A['inventory'],GUEST_ARGS(A))
    assert code!=0 and 'APPROVED_REVISION_2_TABLET_CODE_SEAL_REQUIRED' in text,text


def test_guest_v2_refuses_tampered_member(tmp_path):
    _,new=P.bindings()
    with zipfile.ZipFile(P.ROOT/new['A']['archive']) as z:data=z.read('a_numeric/exp.py')
    zip_path,inv=forge(tmp_path,{'a_numeric/exp.py':data+b'\n'},'g_tamper.zip')
    args=[sha(zip_path.read_bytes()),sha(inv.read_bytes()),new['A']['code_sha256'],new['A']['protocol_sha256'],'A']
    code,text=guest(tmp_path,'g_tamper',P.GUEST_V2,zip_path,inv,args)
    assert code!=0 and 'REVISION_2_813_PLUS_ONE_ONLY' in text,text


def test_guest_v2_refuses_swapped_upload(tmp_path):
    old,new=P.bindings()
    code,text=guest(tmp_path,'g_swap',P.GUEST_V2,P.ROOT/old['A']['archive'],P.ROOT/old['A']['inventory'],GUEST_ARGS(new['A']))
    assert code!=0 and 'APPROVED_NEW_PACKAGE_RAW_PINS' in text,text


def test_original_guest_verifier_still_refuses_revision_2(tmp_path):
    _,new=P.bindings();A=new['A']
    code,text=guest(tmp_path,'g_old',ORIGINAL_GUEST,P.ROOT/A['archive'],P.ROOT/A['inventory'],GUEST_ARGS(A))
    assert code!=0 and 'ORIGINAL_TABLET_CODE_SEAL_REQUIRED' in text,text
