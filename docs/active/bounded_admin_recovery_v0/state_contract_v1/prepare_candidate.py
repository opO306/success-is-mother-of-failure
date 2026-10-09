"""Create a separate candidate from fixed failure code. Static construction only, no readiness seal."""
import ast
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
OLD=ROOT/'docs/active/bounded_admin_recovery_v0/target_54988176_b_v1'
NEW=BASE/'transport'
def replace(text,before,after):
    if text.count(before)!=1:raise ValueError('EXACT_PATCH_SITE_REQUIRED:'+before)
    return text.replace(before,after)

if __name__=='__main__':
    raise SystemExit('RETIRED_INITIAL_BUILDER_DO_NOT_RUN: initial construction retained as history; final sources and manifest are authoritative')
    for p in (OLD/'transport').iterdir():
        if p.is_file() and p.name not in ('controller.py','supervisor.py','transport_seal.json'):
            with (NEW/p.name).open('xb') as f:f.write(p.read_bytes())
    for name in ('target_protocol.json','budget_protocol.json'):
        with (BASE/name).open('xb') as f:f.write((OLD/name).read_bytes())
    text=(OLD/'transport/controller.py').read_text(encoding='utf-8')
    text=replace(text,'import zipfile','import zipfile\nfrom state_contract import inspect, decode')
    text=replace(text,'def local_preflight(approval):\n    global PRIOR_POLICY_FEE_BOUND', '''def local_preflight(approval):
    global PRIOR_POLICY_FEE_BOUND
    readiness = HERE.parent / 'state_contract_ready.json'
    if (not readiness.is_file() or approval.get('state_contract_ready_sha256') != sha(readiness.read_bytes())
            or approval.get('prior_B_prestart_failures') != 1):
        raise ValueError('STATE_CONTRACT_SIMULATION_AND_NEW_APPROVAL_REQUIRED')
    ready = load(readiness)
    if ready.get('status') != 'ADMIN_TRANSPORT_SIMULATED_VALIDATED' or ready.get('B95_passed') is not False:
        raise ValueError('ADMIN_SIMULATION_IS_NOT_B95_AUTHORITY')''')
    text=replace(text,'        self.index = 0','        self.index = 0\n        self.clock_fault = None')
    left=text.index('    def age(self):');right=text.index('    def emit(',left)
    text=text[:left]+'''    def measured_clocks(self):
        if self.start_ns is None:return 0, 0
        mono = (time.monotonic_ns() - self.start_ns) / 1e9
        wall = (datetime.now(timezone.utc) - datetime.fromisoformat(self.started_utc)).total_seconds()
        if mono < 0 or abs(mono - wall) > 2:
            self.clock_fault = 'ALLOCATION_CLOCK_DRIFT'
        return mono, wall

    def age(self):
        mono, wall = self.measured_clocks()
        if self.clock_fault:raise ValueError(self.clock_fault)
        return max(mono, wall)

    def cleanup_age(self):
        # Retain first monotonic clock for stop-only cleanup; drift never authorizes more work.
        mono, wall = self.measured_clocks()
        return max(0, mono) if self.clock_fault else max(mono, wall)

    def stop_control_check(self):
        if (self.supervisor is None or self.supervisor.poll() is not None
                or (self.out/'completion.json').exists() or (self.out/'supervisor_final.json').exists()
                or (self.out/'guardian/final.json').exists()):
            raise RuntimeError('OUTSIDE_STOP_CONTROL_LOST')
        if self.armed is not None:
            pid = load(self.out/'guardian_pid.json')['pid']
            if type(pid) is not int or pid < 1:raise ValueError('GUARDIAN_PID_REQUIRED')
            os.kill(pid, 0)

''' + text[right:]
    left=text.index('    def run(');right=text.index('    def show(',left)
    text=text[:left]+'''    def run(self, argv, name, timeout, input=None):
        self.index += 1
        prefix = self.out / ('%03d_' % self.index + name)
        child = None
        with prefix.with_suffix('.stdout').open('xb') as a, prefix.with_suffix('.stderr').open('xb') as b:
            try:
                if argv[0] in ('ssh', 'scp') and self.armed is not None:
                    self.stop_control_check()
                    child = subprocess.Popen(argv, stdin=subprocess.PIPE if input is not None else None, stdout=a, stderr=b)
                    limit = time.monotonic() + timeout
                    send = input
                    while True:
                        self.stop_control_check()
                        self.age()
                        remaining = limit - time.monotonic()
                        if remaining <= 0:raise subprocess.TimeoutExpired(argv, timeout)
                        try:
                            child.communicate(input=send, timeout=min(.5, remaining))
                            break
                        except subprocess.TimeoutExpired:
                            send = None
                    result = child
                else:
                    result = subprocess.run(argv, input=input, stdout=a, stderr=b, timeout=timeout)
            except BaseException as exc:
                if child is not None and child.poll() is None:
                    child.kill()
                    child.wait(timeout=2)
                self.emit('COMMAND_EXCEPTION', phase=name, error=repr(exc), log_prefix=str(prefix))
                raise
        self.emit('TRANSPORT_EXIT', phase=name, returncode=result.returncode, log_prefix=str(prefix))
        if result.returncode:raise RuntimeError('ADMIN_PHASE_FAILED:' + name)
        return prefix.with_suffix('.stdout').read_bytes()

''' + text[right:]
    left=text.index('    def show(');right=text.index('    def control(',left)
    text=text[:left]+'''    def show(self, name, timeout=12):
        roles = dict(initial_instance='initial', restart_status='restart', phase_control='control', final_instance='final')
        if name not in roles:raise ValueError('API_CALLSITE_ROLE_REQUIRED')
        raw = self.run([self.cli, '--raw', '--retry', '1', 'show', 'instance', str(self.auth['instance_id'])], name, timeout)
        record = decode(raw)
        state = inspect(record, self.auth, roles[name])
        if PRIOR_POLICY_FEE_BOUND + Decimal('0.25') * 600 / 3600 > Decimal('0.10'):
            raise ValueError('B_PLUS_A_EXECUTION_FEE_CAP_REQUIRES_REMAINING_RESERVE')
        self.emit('STATE_OBSERVED', phase=name, **state)
        return dict(record, _admin_state=state['state'], _ssh_ready=state['connection_ready'], _rate_within_cap=state['rate_within_cap'])

''' + text[right:]
    left=text.index('    def control(');right=text.index('    def handoff(',left)
    text=text[:left]+'''    def control(self, required_seconds):
        self.stop_control_check()
        handoff = self.handoff()
        if self.age() + required_seconds + 12 >= handoff:raise TimeoutError('ABSOLUTE_PHASE_TIME_RESERVE')
        observed = self.show('phase_control')
        # API latency is a state transition window: recheck control before any new SSH/SCP.
        self.stop_control_check()
        if self.age() + required_seconds + 12 >= handoff:raise TimeoutError('ABSOLUTE_PHASE_TIME_RESERVE')
        if observed['_admin_state'] != 'RUNNING' or not observed['_ssh_ready']:raise ValueError('INSTANCE_NOT_READY')
        if self.armed is not None and canonical(load(self.out/'guardian/armed.json')) != canonical(self.armed):
            raise ValueError('OUTSIDE_ARM_RECEIPT_CHANGED')

''' + text[right:]
    text=replace(text,"if ready.get('lease_sha256') != sha((self.out / 'supervisor_lease.json').read_bytes()):", "if (ready.get('lease_sha256') != sha((self.out / 'supervisor_lease.json').read_bytes())\n                    or ready.get('instance_id') != self.auth['instance_id'] or self.supervisor.poll() is not None):")
    text=replace(text,"if host['actual_status'] == 'running':", "if host['_admin_state'] == 'RUNNING' and host['_ssh_ready']:")
    text=replace(text,"write(self.out / 'final_instance.json', final)", "write(self.out / 'final_instance.json', final)\n                    if not final['_rate_within_cap']:\n                        trigger = 'FAILED'; failure = 'FINAL_PRICE_CAP_VIOLATION_OBSERVED'")
    left=text.index('        finally:',text.index('    def execute('))
    tail=text[left:].replace('self.age()', 'self.cleanup_age()')
    tail=replace(tail,"confirmed = bool(stop and stop['result']['status'] == 'STOP_CONFIRMED' and final", "if self.clock_fault:\n                trigger = 'FAILED'; failure = self.clock_fault\n            confirmed = bool(stop and stop['result']['status'] == 'STOP_CONFIRMED' and final")
    tail=replace(tail,"and final['actual_status'] in ('exited', 'stopped'))", "and final['_admin_state'] == 'STOPPED' and stop['result'].get('instance_id') == self.auth['instance_id'])")
    tail=replace(tail,"recovery_verified=self.recovered, actual_stop_confirmed=confirmed, allocation_start_utc=self.started_utc,", "recovery_verified=self.recovered, actual_stop_confirmed=confirmed, allocation_start_utc=self.started_utc,\n                  clock_fault=self.clock_fault, measured_mono_wall=self.measured_clocks(),")
    text=text[:left]+tail
    # Bind newly composed drivers into the outside stop lease; original guardian bytes stay unchanged.
    text=replace(text,"cli=self.cli, repo_root=str(ROOT), out=str(self.out))", "cli=self.cli, repo_root=str(ROOT), out=str(self.out),\n                         state_contract_sha256=sha((HERE/'state_contract.py').read_bytes()),\n                         guardian_driver_sha256=sha((HERE/'guardian_driver.py').read_bytes()))")
    with (NEW/'controller.py').open('xb') as f:f.write(text.encode())
    sup=(OLD/'transport/supervisor.py').read_text(encoding='utf-8')
    sup=replace(sup,'import json','import json\nfrom state_contract import CheckedCli')
    sup=replace(sup,'def main():','def main(argv=None):')
    sup=replace(sup,'args = parser.parse_args()','args = parser.parse_args(argv)')
    sup=replace(sup,"or lease['supervisor_sha256'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()):", "or lease['supervisor_sha256'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()\n            or lease['state_contract_sha256'] != hashlib.sha256((Path(__file__).parent/'state_contract.py').read_bytes()).hexdigest()\n            or lease['guardian_driver_sha256'] != hashlib.sha256((Path(__file__).parent/'guardian_driver.py').read_bytes()).hexdigest()):")
    sup=replace(sup,"return max((time.monotonic_ns() - start_ns) / 1e9,\n                   (datetime.now(timezone.utc) - start_utc).total_seconds())", "return (time.monotonic_ns() - start_ns) / 1e9\n    def clock_fault():\n        return abs(age() - (datetime.now(timezone.utc) - start_utc).total_seconds()) > 2")
    sup=replace(sup,"if marker.exists():\n                break", "if clock_fault():\n                raise ValueError('SUPERVISOR_ALLOCATION_CLOCK_DRIFT')\n            if marker.exists():\n                break")
    sup=replace(sup,"guardian = subprocess.Popen([sys.executable, '-B', str(guardian_path), '--authorization',", "guardian = subprocess.Popen([sys.executable, '-B', str(Path(__file__).parent/'guardian_driver.py'),\n                    '--guardian', str(guardian_path), '--authorization',")
    sup=replace(sup,"final = confirm_stop(Cli(lease['cli'], lease['instance_id']), lease['instance_id'], 'FAILED',", "final = confirm_stop(CheckedCli(lease['cli'], lease['instance_id'], lease), lease['instance_id'], 'FAILED',")
    with (NEW/'supervisor.py').open('xb') as f:f.write(sup.encode())
    for p in list(NEW.glob('*.py'))+list((BASE/'tests').glob('*.py')):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    print(json.dumps(dict(status='CANDIDATE_WRITTEN; NOT_STATIC_READY_OR_SIMULATED_VALIDATED',old_sources_unchanged=True)))
