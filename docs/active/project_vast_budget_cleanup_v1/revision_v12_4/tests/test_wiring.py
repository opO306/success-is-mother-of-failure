"""install_all mutates module globals, so each check runs in its own interpreter."""
import subprocess,sys,textwrap
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parents[1]


def run(body):
    code=textwrap.dedent(f'''
        import sys;sys.path.insert(0,{str(HERE)!r})
        import fresh_owned
    ''')+textwrap.dedent(body)
    result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    return result.stdout


def test_every_attachment_point_is_installed():
    out=run('''
        import campaign,cleanup,execution_authority,subprocess,authority
        from reads import ReadRetryProvider
        c=fresh_owned.install_all()
        assert c is campaign and campaign.Provider is ReadRetryProvider
        assert getattr(subprocess.Popen,'v12_3_dispatch',False)
        assert getattr(cleanup.verify_admin,'v12_3_wrapped',False)
        import terminal_proof
        assert getattr(terminal_proof.require_terminal,'v12_4_wrapped',False)
        assert getattr(campaign.source_preflight,'v12_4_wrapped',False) and getattr(campaign.transport_binding,'v12_4_wrapped',False)
        assert execution_authority.claim_paid_approval is authority.claim_paid_approval
        assert fresh_owned.install_all() is campaign  # idempotent, no double wrapping
        print('OK')''')
    assert out.strip()=='OK'


def test_remote_admin_order_is_fingerprint_original_then_v12_2_regression():
    out=run('''
        import campaign
        order=[]
        campaign.remote_admin=lambda *a:order.append('v12_original')
        fresh_owned.fingerprint=lambda *a:order.append('fingerprint')
        fresh_owned.v12_2_regression=lambda *a:order.append('v12_2_regression')
        fresh_owned.install_all()
        campaign.remote_admin('out','ssh','scp',{},None,{})
        print(','.join(order))''')
    assert out.strip()=='fingerprint,v12_original,v12_2_regression'


def test_controller_loaded_through_campaign_gets_read_retry_transport(tmp_path):
    fake=tmp_path/'controller.py'
    # V12.4: the wrap also applies package_v2.patch_controller, which requires configure/verify_local_package.
    fake.write_text('KIND=None\ndef configure(kind):pass\ndef verify_local_package():return "original"\n'
                    'class Transport:\n    def show(self,name,timeout=12):return "original"\n    def control(self,required_seconds,*,phase_deadline=None):return "control"\n')
    out=run(f'''
        import campaign
        fresh_owned.CONTROLLER={str(fake)!r}
        from pathlib import Path
        fresh_owned.CONTROLLER=Path(fresh_owned.CONTROLLER).resolve()
        fresh_owned.install_all()
        spec=campaign.importlib.util.spec_from_file_location('delegated_transport',{str(fake)!r})
        m=campaign.importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        print(m.Transport.__name__,m.Transport.__mro__[1].__name__,getattr(m,'v12_4_package_installed',False))
        other={str(fake.parent/'other.py')!r};open(other,'w').write('X=1\\n')
        s=campaign.importlib.util.spec_from_file_location('o',other);o=campaign.importlib.util.module_from_spec(s);s.loader.exec_module(o)
        print(type(s.loader).__name__)''')
    first,second=out.strip().split('\n')
    assert first=='ReadTransport PackageRevision2Transport True'
    assert second!='Loader'  # only the exact controller file is wrapped


def test_fingerprint_failure_is_recorded_but_watchdog_loss_is_raised(tmp_path):
    out=run(f'''
        import campaign
        from pathlib import Path
        class Watch:
            def __init__(self,alive):self.alive=alive
            def poll(self):return None if self.alive else 1
        def fail(*a,**k):raise ValueError('ADMIN_TRANSPORT_COMMAND_FAILED:fingerprint')
        campaign.command=fail
        out=Path({str(tmp_path)!r})
        fresh_owned.fingerprint(campaign,out,['ssh'],dict(instance_id=1),Watch(True))
        print((out/'v12_3_fingerprint_failure.json').exists())
        try:fresh_owned.fingerprint(campaign,out/'b',['ssh'],dict(instance_id=1),Watch(False));print('swallowed')
        except ValueError:print('raised')''')
    assert out.split()==['True','raised']
