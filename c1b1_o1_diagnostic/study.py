"""Single-input observation-only cause study with immutable evidence binding."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
import mpmath as m
from c1b1_o1.model import MASS, DE, SOURCE
from .kdk import Lang, relative, step, angle_difference, isolate

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT/'runs/c1b1_o1_20261001_v1/boundary_pass'
OUT = ROOT/'runs/c1b1_o1_cause_isolation_20261001_v1'
SEAL = ROOT/'docs/active/C1B1_O1_CAUSE_ISOLATION_SEAL_V1.json'
PROTOCOL = ROOT/'docs/active/C1B1_O1_CAUSE_ISOLATION_PROTOCOL_V1.md'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def verify_artifacts(artifacts):
    for path, row in artifacts.items():
        if sha(ROOT/path) != row['sha256']:
            raise ValueError('evidence hash mismatch: '+path)


def original_evidence():
    results = read(ROOT/'docs/active/C1B1_O1_RESULTS_V1.json')
    verify_artifacts(results['artifacts'])
    sealed = read(ROOT/'docs/active/C1B1_O1_INPUTS_V1.json')
    payload = sealed['payload']
    if hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest() != sealed['payload_sha256']:
        raise ValueError('original input payload seal mismatch')
    for path, want in {**payload['protected_sources'], **payload['independent_sources'], 'tools/c1b1_o1_study.py': payload['driver_sha256'], str(SOURCE): payload['public_source_sha256']}.items():
        if sha(ROOT/path) != want:
            raise ValueError('original source hash mismatch: '+path)
    row = next(r for r in payload['inputs'] if r['id'] == 'boundary_pass')
    state = read(OLD/'states.json')
    confirmation = read(OLD/'confirmed.json')
    observation = read(OLD/'observation.json')
    reference = read(OLD/'independent_80.json')
    if row['raw'] != state['states'][0] or row != observation['input'] or observation['verdict'] != 'DISAGREE' or confirmation['confirmation'] != 'CONFIRMED' or confirmation['evidence'] != 'REPLAY_VERIFIED':
        raise ValueError('original raw/provenance mismatch')
    if row['initial_validation']['validation_status'] != 'unsupported':
        raise ValueError('existing D_valid classification changed')
    with m.workdps(80):
        q0, p0 = relative(row['raw']); qf, pf = relative(state['states'][-1])
        direction = m.atan2(pf[1], pf[0]); initial_direction = m.atan2(p0[1], p0[0])
        chi = m.atan2(m.sin(direction-initial_direction), m.cos(direction-initial_direction))
        if angle_difference(chi, m.mpf(observation['A']['chi'])) > m.mpf('1e-14'):
            raise ValueError('stored production angle reproduction mismatch')
        mu = m.mpf(MASS.split('/')[0])/m.mpf(MASS.split('/')[1])/2
        v, _ = Lang().value_derivative(m.sqrt(sum(x*x for x in q0)))
        h = sum(x*x for x in p0)/(2*mu)+v
        l = q0[0]*p0[1]-q0[1]*p0[0]
        if abs(h-m.mpf(reference['H'])) > m.mpf('1e-70') or abs(l-m.mpf(reference['L'])) > m.mpf('1e-70'):
            raise ValueError('stored continuous initial invariants mismatch')
        radius = m.sqrt(sum(x*x for x in qf))
        v, _ = Lang().value_derivative(radius)
        g = 2*mu*(h-v)-l*l/radius**2
        direction_ref = m.atan2(m.sin(m.mpf(reference['sweep'])+m.atan2(l/radius, m.sqrt(g))), m.cos(m.mpf(reference['sweep'])+m.atan2(l/radius, m.sqrt(g))))
        if angle_difference(direction_ref, m.mpf(reference['direction'])) > m.mpf('1e-65'):
            raise ValueError('stored continuous direction reproduction mismatch')
        numerical_a = dict(chi=m.nstr(chi, 80), direction=m.nstr(direction, 80), r_exit_exact=m.nstr(radius, 80), stored_angle_difference=m.nstr(angle_difference(chi, m.mpf(observation['A']['chi'])), 35), continuous_direction_reproduction_error=m.nstr(angle_difference(direction_ref, m.mpf(reference['direction'])),40))
    return row, reference, observation, numerical_a


def seal():
    row, reference, observation, numerical_a = original_evidence()
    import subprocess
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    protected = {path: sha(ROOT/path) for path in tracked if path.startswith(('a_reference/', 'a_numeric/', 'c1b1_replay/', 'c1b1_o1/')) or path in ['tools/c1b1_o1_study.py', 'docs/active/C1B1_O1_INPUTS_V1.json', 'docs/active/C1B1_O1_PROTOCOL_V1.md', 'docs/active/C1B1_O1_RESULTS_V1.json', 'docs/active/C1B1_O1_INDEPENDENT_NUMERICAL_REPRODUCTION_V1.md']}
    files = list((ROOT/'c1b1_o1_diagnostic').glob('*.py'))+[PROTOCOL, ROOT/'tests/test_c1b1_o1_diagnostic.py']
    payload = dict(schema='c1b1-o1-cause-isolation-seal-v1', head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), input=row, original_reference=reference, original_A=observation['A'], reproduction=numerical_a, protected=protected, diagnostic={str(path.relative_to(ROOT)).replace('\\', '/'): sha(path) for path in files}, artifacts=read(ROOT/'docs/active/C1B1_O1_RESULTS_V1.json')['artifacts'], public_source_sha256=sha(SOURCE), allowed_dt=[40,20,10,5], precision=[40,60], observation_only=True, existing_O1='STOPPED / NOT PASSED')
    digest=hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    save_new(SEAL, dict(payload=payload, payload_sha256=digest))
    print('SEALED', digest, 'existing artifact hashes', len(payload['artifacts']), flush=True)


def load_seal():
    data = read(SEAL); p = data['payload']
    if hashlib.sha256(json.dumps(p, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest() != data['payload_sha256']:
        raise ValueError('diagnostic seal mismatch')
    for path, want in {**p['protected'], **p['diagnostic'], str(SOURCE):p['public_source_sha256']}.items():
        if sha(ROOT/path) != want:
            raise ValueError('sealed source mismatch: '+path)
    verify_artifacts(p['artifacts'])
    return p


def simulate(raw, dt, dps, mu_value, exit_radius, trace_path, pes_type=Lang):
    start = time.perf_counter(); cpu = time.process_time()
    with m.workdps(dps):
        mu, target, h, de = m.mpf(mu_value), m.mpf(exit_radius), m.mpf(dt), m.mpf(DE)
        q, p = relative(raw); initial_p = p[:]; pes = pes_type()
        cached_q = None; cached_v = None; cached_f = None
        def force(q):
            nonlocal cached_q, cached_v, cached_f
            if q != cached_q:
                radius = m.sqrt(sum(x*x for x in q))
                if radius < m.mpf('2.4'):
                    raise ValueError('diagnostic entered below existing r_min')
                cached_v, deriv = pes.value_derivative(radius)
                cached_f = [-deriv*x/radius for x in q]; cached_q = q[:]
            return cached_f
        force(q)
        h0 = sum(x*x for x in p)/(2*mu)+cached_v; l0 = q[0]*p[1]-q[1]*p[0]
        max_e = max_l = m.mpf(0); sweep = m.mpf(0)
        min_r = min_chord = m.sqrt(sum(x*x for x in q))
        trace_path = Path(trace_path); trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open('xb') as binary, gzip.GzipFile(fileobj=binary, mode='wb', mtime=0) as trace:
            def record(n, q, p):
                trace.write((json.dumps([n]+[m.nstr(x, dps) for x in q+p], separators=(',', ':'))+'\n').encode())
            record(0, q, p)
            for n in range(1,240001):
                old_q = q
                q, p = step(q, p, h, mu, force)
                radius = m.sqrt(sum(x*x for x in q)); min_r = min(min_r, radius)
                d = [q[i]-old_q[i] for i in range(2)]; dd = sum(x*x for x in d)
                t = max(m.mpf(0), min(m.mpf(1), -sum(old_q[i]*d[i] for i in range(2))/dd)) if dd else m.mpf(0)
                min_chord = min(min_chord, m.sqrt(sum((old_q[i]+t*d[i])**2 for i in range(2))))
                sweep += m.atan2(old_q[0]*q[1]-old_q[1]*q[0], sum(old_q[i]*q[i] for i in range(2)))
                energy = sum(x*x for x in p)/(2*mu)+cached_v
                max_e = max(max_e, abs(energy-h0)/de)
                max_l = max(max_l, abs(q[0]*p[1]-q[1]*p[0]-l0))
                record(n, q, p)
                if n % 5000 == 0:
                    print('HP-KDK', dt, dps, 'step', n, 'radius', m.nstr(radius, 9), flush=True)
                if radius >= target and sum(q[i]*p[i] for i in range(2)) > 0:
                    break
            else:
                raise ValueError('diagnostic step limit; STOP')
        direction = m.atan2(p[1], p[0]); initial = m.atan2(initial_p[1], initial_p[0])
        chi = m.atan2(m.sin(direction-initial), m.cos(direction-initial))
        values = dict(chi=chi, direction=direction, sweep=sweep, r_min_chord=min_chord, r_min_stored=min_r, r_exit=radius, time=n*h, H0=h0, L0=l0, energy_max_change_De=max_e, energy_final_change_De=(energy-h0)/de, angular_max_change=max_l, angular_final_change=q[0]*p[1]-q[1]*p[0]-l0)
        result = {k:m.nstr(v, dps) for k,v in values.items()}
        result.update(q_out=[m.nstr(x,dps) for x in q], p_out=[m.nstr(x,dps) for x in p], dt=dt, dps=dps, steps=n, trace_sha256=sha(trace_path), trace_path=str(trace_path.relative_to(ROOT)) if trace_path.is_relative_to(ROOT) else str(trace_path), cpu_seconds=time.process_time()-cpu, wall_seconds=time.perf_counter()-start)
        return result


def extend_reference(ref, base_radius, radius, mu, potential):
    h, l = m.mpf(ref['H']), m.mpf(ref['L'])
    g = lambda r: 2*mu*(h-potential(r))-l*l/(r*r)
    angle, ae = m.quad(lambda r:l/(r*r*m.sqrt(g(r))), [base_radius, radius], error=True)
    elapsed, te = m.quad(lambda r:mu/m.sqrt(g(r)), [base_radius, radius], error=True)
    correction = angle+m.atan2(l/radius,m.sqrt(g(radius)))-m.atan2(l/base_radius,m.sqrt(g(base_radius)))
    return dict(chi=m.nstr(m.mpf(ref['chi'])+correction, m.mp.dps), direction=m.nstr(m.mpf(ref['direction'])+correction,m.mp.dps), sweep=m.nstr(m.mpf(ref['sweep'])+angle,m.mp.dps), time=m.nstr(m.mpf(ref['time'])+elapsed,m.mp.dps), r_min=ref['r_min'], outlet_direction_correction=m.nstr(correction,m.mp.dps), local_quad_error=m.nstr(max(ae,te),m.mp.dps))


def run_one(dt, dps):
    p = load_seal(); key=f'hp_kdk_dt{dt}_dps{dps}'
    with m.workdps(dps):
        mu=m.mpf(MASS.split('/')[0])/m.mpf(MASS.split('/')[1])/2
        result = simulate(p['input']['raw'],dt,dps,mu,m.mpf(p['reproduction']['r_exit_exact']),OUT/(key+'.jsonl.gz'))
        pes=Lang(); v=lambda r:pes.value_derivative(r)[0]
        ref=extend_reference(p['original_reference'],m.mpf(p['reproduction']['r_exit_exact']),m.mpf(result['r_exit']),mu,v)
        result['matched_continuous']=ref
        result['differences']={k:m.nstr(angle_difference(m.mpf(result[k]),m.mpf(ref[k])) if k in ('chi','direction') else abs(m.mpf(result['r_min_chord'])-m.mpf(ref['r_min'])),dps) for k in ('chi','direction','r_min')}
    save_new(OUT/(key+'.json'),result)
    print('RESULT',key,result['chi'],result['differences'],flush=True)
    return result


def forty():
    first=run_one(40,40); last=run_one(40,60); p=load_seal()
    with m.workdps(70):
        fields=['chi','direction','r_min_chord','energy_max_change_De','r_exit']
        changes={k:abs(m.mpf(first[k])-m.mpf(last[k])) for k in fields}
        changes.update({f'{kind}{i}':abs(m.mpf(a)-m.mpf(b)) for kind in ('q_out','p_out') for i,(a,b) in enumerate(zip(first[kind],last[kind]))})
        stable=max(changes.values()) <= m.mpf('1e-20')
        verdict=isolate(m.mpf(last['matched_continuous']['chi']),m.mpf(last['chi']),m.mpf(p['reproduction']['chi']),max(changes.values()))
        if last['steps'] != p['original_A']['steps'] or abs(m.mpf(last['r_exit'])-m.mpf(p['reproduction']['r_exit_exact']))>m.mpf('1e-8'):
            verdict=dict(verdict='UNRESOLVED_STOP',reason='production/HP40 endpoint mismatch')
        gate=dict(**verdict,precision_stable=stable,precision_changes={k:m.nstr(x,40) for k,x in changes.items()},fixed_point_aggregate_includes_observer=False,numerical_diagnostic=True,formal_certified=False)
    save_new(OUT/'dt40_gate.json',gate);print('GATE',gate,flush=True)


def reduce_dt():
    load_seal()
    gate=read(OUT/'dt40_gate.json')
    if gate['verdict'] != 'TIME_DISCRETIZATION_SUPPORTED' or not gate['precision_stable']:
        raise ValueError('dt reduction not authorized by diagnostic gate')
    previous=read(OUT/'hp_kdk_dt40_dps60.json'); rows=[previous]
    for dt in (20,10,5):
        row=run_one(dt,60); rows.append(row)
        if m.mpf(row['differences']['chi'])>=m.mpf(previous['differences']['chi']):
            save_new(OUT/'reduction_stop.json',dict(reason='angle error did not decrease',dt=dt))
            break
        previous=row
    rates=[]
    for a,b in zip(rows,rows[1:]):
        rate=math.log(float(a['differences']['chi'])/float(b['differences']['chi']),2)
        rates.append(dict(from_dt=a['dt'],to_dt=b['dt'],observed_angle_order=rate))
    save_new(OUT/'reduction_summary.json',dict(rows=rows,observed_rates=rates,numerical_diagnostic=True,production_changed=False,O1='STOPPED / NOT PASSED'))


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['seal','forty','reduce'])
    globals()[{'seal':'seal','forty':'forty','reduce':'reduce_dt'}[parser.parse_args().phase]]()
