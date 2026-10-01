"""Run one preflighted portable package on one existing CPU node, then stop it."""
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.c1b1_dt40_package import portable_name,verify
OUT = ROOT/'runs/c1b1_dt40_portable_v2'
NODE = 52763629
REMOTE = '/workspace/c1b1_dt40_portable_130df0d_v2'


def instances():
    return json.loads(subprocess.check_output(['vastai','show','instances','--raw'],text=True))


def selected():
    return next(x for x in instances() if x['id']==NODE)


def public(x):
    keys=('id','actual_status','intended_status','cur_state','cpu_name','cpu_cores_effective','cpu_ram','dph_total')
    return {k:x.get(k) for k in keys}


def main():
    local=json.loads((OUT/'local_preflight.json').read_text())
    suites=ET.parse(OUT/'local_related_final.xml').getroot().findall('testsuite')
    if sum(int(s.get('tests','0')) for s in suites)!=22 or any(int(s.get(k,'0')) for s in suites for k in ('failures','errors','skipped')):
        raise ValueError('local package/related tests are not all passed')
    restored=ET.parse(OUT/'restored_related.xml').getroot().findall('testsuite')
    if local.get('restored_related_exit')!=0 or sum(int(s.get('tests','0')) for s in restored)!=49 or any(int(s.get(k,'0')) for s in restored for k in ('failures','errors','skipped')):
        raise ValueError('restored package related tests are not all passed')
    archive=OUT/'portable_package.tar.gz';bootstrap=ROOT/'tools/c1b1_dt40_remote.py'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=local['bundle_sha256']:
        raise ValueError('local package changed after preflight')
    if hashlib.sha256(bootstrap.read_bytes()).hexdigest()!=local['bootstrap_sha256']:
        raise ValueError('bootstrap changed after preflight')
    if verify(OUT/'fresh_unpack')!=local['verification']:
        raise ValueError('restored package preflight changed')
    before=selected()
    if any(x.get('actual_status')=='running' or x.get('intended_status')=='running' for x in instances()):
        raise ValueError('an instance is already running; no additional start')
    if before['dph_total']>1:
        raise ValueError('hourly cap exceeded')
    record=dict(instance=NODE,before=public(before),start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                bundle_sha256=local['bundle_sha256'],bootstrap_sha256=local['bootstrap_sha256'],compute_gpu=False,
                started_request=False,retrieved=False,push=False)
    start=time.monotonic();failure=None
    try:
        from vastai.sdk import VastAI
        record['started_request']=True
        response=VastAI(retry=1).start_instance(id=NODE)
        record['start_response']={k:response[k] for k in ('success','msg','error','message') if k in response}
        print('START RESPONSE',record['start_response'],flush=True)
        if response.get('success') is not True:
            raise ValueError('start not accepted; cancel queued state')
        for _ in range(20):
            current=selected()
            if current.get('actual_status')=='running':break
            time.sleep(5)
        else:raise ValueError('running not confirmed')
        record['running']=public(current)
        host=str(ipaddress.ip_address(current['public_ipaddr']))
        port=int(current['ports']['22/tcp'][0]['HostPort'])
        record['endpoint']=dict(host=host,port=port,source='live direct 22/tcp mapping')
        key=str(Path.home()/'.ssh/vast_ai')
        options=['-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','ConnectTimeout=15']
        ssh=['ssh','-i',key,'-p',str(port),*options,'-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3',f'root@{host}']
        probe=subprocess.run(ssh+['python3 -c "print(314159);import sys;print(sys.version)"'],capture_output=True,text=True,timeout=30)
        record['ssh_probe']=dict(exit=probe.returncode,stdout=probe.stdout,stderr=probe.stderr)
        if probe.returncode or '314159' not in probe.stdout:
            raise ValueError('remote command probe failed')
        scp=['scp','-O','-i',key,'-P',str(port),*options]
        base=f'root@{host}:/workspace/'
        subprocess.run(scp+[str(archive),base+'c1b1_dt40_portable_v2.tar.gz'],check=True,timeout=180)
        subprocess.run(scp+[str(bootstrap),base+'c1b1_dt40_portable_bootstrap_v2.py'],check=True,timeout=60)
        print('PACKAGE TRANSFERRED; REMOTE HASH PREFLIGHT NEXT',flush=True)
        command='python3 /workspace/c1b1_dt40_portable_bootstrap_v2.py /workspace/c1b1_dt40_portable_v2.tar.gz '+local['bundle_sha256']+' '+REMOTE+' /workspace/c1b1_dt40_portable_results_v2.tar.gz'
        with (OUT/'remote_control.log').open('x') as log:
            result=subprocess.run(ssh+[command],stdout=log,stderr=subprocess.STDOUT,timeout=3000)
        record['remote_exit']=result.returncode
        downloaded=OUT/'remote_results.tar.gz'
        subprocess.run(scp+[base+'c1b1_dt40_portable_results_v2.tar.gz',str(downloaded)],check=True,timeout=180)
        with tarfile.open(downloaded) as tf:
            for member in tf.getmembers():
                portable_name(member.name)
                if not (member.isfile() or member.isdir()):raise ValueError('nonregular result archive')
            tf.extractall(OUT,filter='data')
        manifest=json.loads((OUT/'remote_results/deployment_logs/artifact_manifest.json').read_text())
        for name,row in manifest.items():
            portable_name(name)
            path=OUT/'remote_results'/name
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256'] or path.stat().st_size!=row['bytes']:
                raise ValueError('result artifact hash: '+name)
        record.update(retrieved=True,verified_artifacts=len(manifest),results_archive_sha256=hashlib.sha256(downloaded.read_bytes()).hexdigest())
        print('RESULTS RETRIEVED AND HASH VERIFIED',len(manifest),flush=True)
        if result.returncode:raise ValueError('remote preflight/campaign failed; failure evidence retrieved')
    except BaseException as exc:
        failure=str(exc);record['failure']=failure
    finally:
        if record['started_request']:
            stopped=subprocess.run(['vastai','stop','instance',str(NODE)],capture_output=True,text=True,timeout=30)
            record['stop_exit']=stopped.returncode
            for _ in range(12):
                final=selected()
                if final.get('actual_status')=='exited' and final.get('intended_status')=='stopped':break
                time.sleep(5)
            record['final']=public(final)
            record['stopped_confirmed']=final.get('actual_status')=='exited' and final.get('intended_status')=='stopped'
        record['end_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        record['elapsed_seconds']=time.monotonic()-start
        record['rate_duration_proxy_usd']=record['elapsed_seconds']/3600*before['dph_total']
        record['cost_note']='Not an invoice; full control interval times API compute rate; transfer/storage excluded.'
        (OUT/'lifecycle.json').write_text(json.dumps(record,indent=2)+'\n')
        print('STOP CONFIRMED',record.get('stopped_confirmed'),'FAILURE',failure,flush=True)
    return 1 if failure else 0


if __name__=='__main__':
    raise SystemExit(main())
