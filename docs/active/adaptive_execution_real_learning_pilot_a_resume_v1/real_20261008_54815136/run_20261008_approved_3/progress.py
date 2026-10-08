"""Read-only partial evidence observation, no project imports or verifier authority."""
from pathlib import Path
import json,subprocess,shlex
r=Path(__file__).resolve().parent
h=json.loads((r/'running_instance.json').read_bytes());g=json.loads((r/'guest_setup.json').read_bytes())['guest_root']
script="""
from pathlib import Path
import json
root=Path(%r)/'output_actual'; a=root/'A'
read=lambda p:json.loads(p.read_bytes()) if p.exists() else None
files=sorted((a/'measurement').glob('*.json'))
first=read(a/'first_result_receipt.json'); receipt=read(a/'receipt.json')
print(json.dumps({'records':[p.name for p in files],'cost_records':len(list((a/'measurement/request_costs').glob('*.json'))),
 'replay_exists':(a/'replay.json').exists(),'first_gate':None if first is None else first['body']['verdict'],
 'cost_receipt':None if receipt is None else receipt['body']['verdict'],'stop':read(root/'STOP.json'),
 'learned_records':[p.name for p in (a/'next_request').glob('*.json')],'stage_report':read(a/'stage_report.json')}))
"""%g
cmd=['ssh','-i','C:/Users/zun24/.ssh/vast_ai','-p',str(h['ssh_port']),'-o','BatchMode=yes','-o','ConnectTimeout=5','root@'+h['ssh_host'],'python3 -c '+shlex.quote(script)]
p=subprocess.run(cmd,capture_output=True,timeout=20)
print(p.stdout.decode());print('ADMIN_READ_RETURN_CODE',p.returncode)
