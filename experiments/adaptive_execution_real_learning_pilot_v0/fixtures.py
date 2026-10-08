"""Historical fixture rewrapping for contract tests only; no new computation or real session."""
from .common import ROOT,digest,read,ns
from .inspector import initial_state


def contract_panel(N=14,goal='WALL_MIN'):
    base=ROOT/'docs/active/adaptive_execution_v1/vast_evaluate/run_evaluate'
    session={'origin':'OFFLINE_CONTRACT_FIXTURE','session_id':'HISTORICAL_CONTRACT_ONLY',
             'env':read(base/'env.json')['env'],'N':N,'T':1000,'goal':goal,
             'methods':['SERIAL','W6'] if N==14 else ['SERIAL','GPU'],'code_manifest_sha256':'HISTORICAL_FIXTURE_NO_LIVE_CODE'}
    records=[]
    for repeat in range(5):
        for method in session['methods']:
            rid='R7' if N==14 else 'R1'
            s=read(base/f'services/r{repeat+1}/{rid}__FIXED_{method}.json.gz')
            records.append(dict(kind='OFFLINE_CONTRACT_FIXTURE',state='CANDIDATE',run_id=f'{method}/{repeat}',
                session_id=session['session_id'],session_sha256=digest(session),repeat=repeat,method=method,
                goal=session['goal'],code_manifest_sha256=session['code_manifest_sha256'],service=s,
                initial_state=initial_state(N),observation={'wall_ns':ns(s['service_wall_s']), 'cpu_ns':ns(s['service_cpu_s'])}))
    replays={f'{N}/1000/163':dict(origin='OFFLINE_CONTRACT_FIXTURE',session_sha256=digest(session),
                code_manifest_sha256=session['code_manifest_sha256'],result=read(base/f'replay/N{N}_T1000_p163.json'))}
    return records,session,replays
