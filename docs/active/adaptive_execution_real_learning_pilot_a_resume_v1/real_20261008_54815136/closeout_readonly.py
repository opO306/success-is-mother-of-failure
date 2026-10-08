"""ADMINISTRATIVE evidence aggregation only: no project import/test/calculation.

Existing signatures are checked; this script creates no key, receipt, promotion,
approval, or new numerical verification. It does not contact or restart Vast.
"""
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
import hashlib, json, statistics, zipfile, xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
RUN = BASE / 'run_20261008_approved_3'
REC = RUN / 'recovered'
OUT = REC / 'output_actual'
A = OUT / 'A'

def pairs(items):
    obj = {}
    for k, v in items:
        if k in obj: raise ValueError('DUPLICATE_JSON_KEY:' + k)
        obj[k] = v
    return obj

def read(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def digest(obj): return hashlib.sha256(canonical(obj)).hexdigest()
def raw(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok, msg):
    if not ok: raise ValueError(msg)

def verify(key, domain, envelope):
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(
        bytes.fromhex(envelope['signature']), domain + canonical(envelope['body']))

def history(path):
    previous, events = 'GENESIS', []
    for i, p in enumerate(sorted(path.glob('event_*.json'))):
        event = read(p)
        require(p.name == f'event_{i:06d}.json' and event['index'] == i and event['previous'] == previous
                and digest({k: v for k, v in event.items() if k != 'sha256'}) == event['sha256']
                and p.read_bytes() == canonical(event), 'LEDGER_RAW_HASH_CHAIN')
        previous = event['sha256']; events.append(event)
    return events, previous

manifest = read(RUN / 'evidence_manifest.json')
files = manifest['files']
with zipfile.ZipFile(RUN / 'evidence.zip') as z:
    require(z.testzip() is None, 'ARCHIVE_CRC')
    require(set(z.namelist()) == set(files) | {'evidence_manifest.json'}, 'ARCHIVE_FILE_SET')
    for name, wanted in files.items():
        require(raw(REC / name) == wanted and hashlib.sha256(z.read(name)).hexdigest() == wanted,
                'RECOVERED_OR_ARCHIVED_RAW:' + name)
require(len(files) == 111, 'RECOVERY_111_FILES')

protocol_path = ROOT / 'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/protocol.json'
protocol = read(protocol_path)
session = read(A / 'session.json')
provision = read(OUT / 'provision.json')
roots = provision['roots']
require(roots['inspector'] != roots['manager'] and roots['mode'] == 'RESEARCH_ONLY', 'DISTINCT_RESEARCH_ROOTS')
require(session['resume_protocol_sha256'] == raw(protocol_path), 'SESSION_CURRENT_PROTOCOL')
seal_path = ROOT / 'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'
require(session['code_manifest_sha256'] == raw(seal_path), 'SESSION_CURRENT_SOURCE')
source = read(seal_path)
protected = read(ROOT / 'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/protected_history.json')
for label, mappings in [('source', source['files']), ('protected', protected['files'])]:
    for name, wanted in mappings.items(): require(raw(ROOT / name) == wanted, label + ':' + name)

receipts = {}
for operation, filename, names, verdict in [
    ('CHECK_FIRST', 'first_result_receipt.json', ['measurement/SERIAL_0.json'], 'REAL_SESSION_FIRST_RESULT_CHECKED'),
    ('INSPECT', 'receipt.json', [p.relative_to(A).as_posix() for p in sorted((A/'measurement').glob('*.json'))], 'REAL_SESSION_COST_CHECKED'),
    ('CHECK_NEXT', 'next_request_receipt.json', ['next_request/W6_5.json'], 'REAL_SESSION_RESULT_CHECKED')]:
    envelope = read(A / filename); body = envelope['body']
    verify(roots['inspector'], b'REAL_PILOT_RECEIPT\0', envelope)
    require(body['verdict'] == verdict and body['scope'] == 'RESEARCH_ONLY' and not body['errors']
            and body['session_sha256'] == digest(session) and body['code_manifest_sha256'] == raw(seal_path)
            and body['resume_protocol_sha256'] == raw(protocol_path)
            and body['formula_independence'] == 'UNRESOLVED_SHARED_RWFORCE', 'SIGNED_RECEIPT_BINDING')
    expected = {'session.json', 'replay.json'}
    for name in names:
        p = Path(name)
        expected.update((name, (p.parent/'evidence_metrics'/p.name).as_posix(),
                         (p.parent/'request_costs'/p.name).as_posix()))
    require(set(body['raw_files']) == expected, 'SIGNED_REQUIRED_FILE_SET:' + operation)
    for name, wanted in body['raw_files'].items(): require(raw(A/name) == wanted, 'SIGNED_RAW:' + name)
    receipts[operation] = {'verdict': verdict, 'sha256': raw(A/filename), 'raw_files': len(expected)}

events, tip = history(OUT / 'manager/events')
for event in events:
    verify(roots['manager'], b'REAL_PILOT_APPROVAL\0', event['payload'])
    require(event['payload']['body']['predecessor'] == event['previous'], 'APPROVAL_PREDECESSOR')
witness = read(OUT / 'controller_witness/signed_head.json')
verify(roots['manager'], b'REAL_PILOT_WITNESS\0', witness)
require(witness['body'] == {'count': len(events), 'tip': tip}, 'SIGNED_WITNESS')
require(len(events) == 2 and events[0]['payload']['body']['profile_id'] != 'LEGACY'
        and events[1]['payload']['body']['profile_id'] == 'LEGACY', 'SIGNED_ACTIVATION_ROLLBACK')
profiles = list((OUT / 'manager/profiles').glob('*.json'))
require(len(profiles) == 1, 'ONE_PROFILE')
profile = read(profiles[0])
require(profile['id'] == digest({k:v for k,v in profile.items() if k != 'id'})
        and profile['state'] == 'VERIFIED' and profile['mode'] == 'RESEARCH_ONLY'
        and profile['goal'] == 'WALL_MIN' and profile['session_sha256'] == digest(session)
        and profile['receipt'] == read(A/'receipt.json')
        and profile['rows'] == profile['receipt']['body']['rows']
        and profile['id'] == events[0]['payload']['body']['profile_id'], 'VERIFIED_PROFILE_BINDING')

record_rows, metrics_rows = [], []
reference_initial = None
for location in ('measurement', 'next_request'):
    for path in sorted((A/location).glob('*.json')):
        obj = read(path); metric_path = path.parent/'evidence_metrics'/path.name
        cost_path = path.parent/'request_costs'/path.name
        metric, cost = read(metric_path), read(cost_path)
        o = obj['observation']; s = obj['service']
        require(cost['session_sha256'] == obj['session_sha256'] == digest(session)
                and obj['session_id'] == session['session_id']
                and cost['code_manifest_sha256'] == obj['code_manifest_sha256'] == raw(seal_path)
                and cost['resume_protocol_sha256'] == raw(protocol_path)
                and cost['record_sha256'] == metric['raw_sha256'] == raw(path)
                and cost['metrics_sha256'] == raw(metric_path), 'COST_RAW_SESSION_SOURCE')
        require((cost['run_id'], cost['method'], cost['repeat']) == (obj['run_id'], obj['method'], obj['repeat'])
                and obj['run_id'] == session['session_id']+'/'+obj['method']+'/'+str(obj['repeat']), 'COST_RUN_ID')
        require(cost['end_wall_ns']-cost['start_wall_ns'] == cost['wall_ns']
                and sum(cost['cpu_deltas_ns'].values()) == cost['cpu_ns']
                and cost['wall_ns']-o['wall_ns'] == cost['additional_wall_ns']
                and cost['cpu_ns']-o['cpu_ns'] == cost['additional_cpu_ns'], 'COST_CLOCK_DELTA')
        require(0 <= metric['total_ns'] <= cost['additional_wall_ns']
                and 0 <= metric['save_reread_cpu_ns'] <= cost['additional_cpu_ns']
                and cost['additional_wall_ns']*100 <= o['wall_ns']
                and metric['physics_calls'] == metric['independent_replays'] == 0, 'LIGHT_BOUND')
        require(obj['state'] == 'CANDIDATE' and (s['N'],s['T'],s['final_p']) == (14,1000,163)
                and s['p_sequence'] == [163] and s['status'] == 'DECIDED', 'EXACT_REQUEST_PRECISION')
        initial = {k:obj[k] for k in ('initial_state','initial_sha256','initial_content_sha256','initial_content_version')}
        if reference_initial is None: reference_initial = initial
        require(initial == reference_initial, 'SAME_ORIGINAL_INITIAL')
        record_rows.append({'location':location,'method':obj['method'],'repeat':obj['repeat'],
            'full_wall_ns':cost['wall_ns'],'full_cpu_ns':cost['cpu_ns'],
            'calculation_wall_ns':o['wall_ns'],'calculation_cpu_ns':o['cpu_ns'],
            'final_p':s['final_p'],'status':s['status'],'state':obj['state'],
            'record_sha256':raw(path),'placement':s['passes'][0]['attempts'][0]['plan'],
            'profile_snapshot':obj['selection']['profile_snapshot']})
        metrics_rows.append({'record':path.relative_to(A).as_posix(),
            **{k:cost[k] for k in ('additional_wall_ns','additional_cpu_ns')},
            **{k:metric[k] for k in ('total_ns','save_reread_cpu_ns','canonical_hash_ns','legacy_hash_ns',
                'save_ns','reread_ns','lightweight_check_ns','rss_delta_bytes','additional_record_bytes','record_bytes')},
            'metrics_bytes':metric_path.stat().st_size,'request_cost_bytes':cost_path.stat().st_size,
            'wall_percent':str(Decimal(cost['additional_wall_ns'])*100/Decimal(o['wall_ns']))})
require(len(record_rows) == 11, 'ELEVEN_CANDIDATES')
measured = [r for r in record_rows if r['location'] == 'measurement']
methods = {}
for method in ('SERIAL','W6'):
    rows = [r for r in measured if r['method'] == method]
    require(len(rows) == 5, 'FIVE_PER_METHOD')
    summary = {'count':5}
    for key in ('full_wall_ns','full_cpu_ns','calculation_wall_ns','calculation_cpu_ns'):
        vals = [r[key] for r in rows]
        require(max(vals)*4 <= min(vals)*5, 'SPREAD_OVER_1_25')
        summary[key] = {'median':statistics.median(vals),'min':min(vals),'max':max(vals),
                        'max_min_ratio':str(Decimal(max(vals))/Decimal(min(vals))), 'sum':sum(vals)}
    methods[method] = summary
for row in profile['rows']:
    require(row['wall_ns'] == methods[row['method']]['full_wall_ns']['median']
            and row['cpu_ns'] == methods[row['method']]['full_cpu_ns']['median'], 'PROFILE_RAW_MEDIAN')
for name in ('legacy_selector_before.json','legacy_selector_after_rollback.json'):
    require(read(A/name)['backend'] == 'CPU_SERIAL', 'LEGACY_SELECTOR_PROBE')
require(len(read(A/'replay.json')) == 1 and not list(OUT.rglob('STOP.json')), 'ONE_FRESH_REPLAY_NO_STOP')

cost_events, _ = history(OUT/'costs')
category = defaultdict(lambda: {'count':0,'wall_ns':0,'cpu_ns':0})
for event in cost_events:
    p = event['payload']; c = category[p['category']]
    c['count'] += 1; c['wall_ns'] += p['wall_ns']; c['cpu_ns'] += p['cpu_ns']
closure = read(RUN/'closure.json'); report = read(OUT/'report.json'); stage = read(A/'stage_report.json')
require(report['status'] == stage['status'] == 'REAL_LEARNING_LOOP_VALIDATED'
        and closure['actual_shutdown'] in ('exited','stopped'), 'LOOP_AND_REAL_EXIT')
before = next(r for r in measured if r['method'] == 'SERIAL' and r['repeat'] == 0)
after = next(r for r in record_rows if r['location'] == 'next_request')
require(after['method'] == 'W6' and after['profile_snapshot'] == raw(profiles[0]), 'NEXT_REQUEST_VERIFIED_PROFILE_BYTES')
saving = before['full_wall_ns']-after['full_wall_ns']
allocation = closure['allocation_total_wall_ns']
overhead = allocation-before['full_wall_ns']-after['full_wall_ns']
require(saving > 0 and overhead >= 0, 'OBSERVED_IMPROVEMENT')
break_even = (overhead+saving-1)//saving
phases = []
for i in (1,2,3):
    r = BASE/f'run_20261008_approved_{i}'
    for line in (r/'events.jsonl').read_bytes().splitlines():
        e = json.loads(line)
        if e['status'] == 'PHASE_END':
            phases.append({'attempt':i,'phase':e['phase'],'wall_ns':e['end_ns']-e['start_ns']})
unclassified = allocation-sum(p['wall_ns'] for p in phases)
require(unclassified >= 0, 'EXCLUSIVE_OUTER_PHASE_TOTAL')
testroot = ET.fromstring((REC/'output_offline/junit.xml').read_bytes())
suite = testroot.find('testsuite')
require(suite is not None and suite.get('tests') == '254' and suite.get('failures') == '0'
        and suite.get('errors') == '0' and suite.get('skipped') == '0', '254_PASS_NO_SKIP')
light_wall = [m['additional_wall_ns'] for m in metrics_rows]
light_cpu = [m['additional_cpu_ns'] for m in metrics_rows]
result = {'schema':'A_RESUME_ADMINISTRATIVE_CLOSEOUT_V1',
    'authority':'AUTHOR_READ_ONLY_FILE_SIGNATURE_AND_COST_AGGREGATION; NO_NEW_INSPECTOR_RECEIPT_OR_PROMOTION',
    'project_imports':0,'project_tests':0,'physics_calls':0,'gpu_calls':0,'paid_actions':0,
    'loop_status':report['status'],'economics_status':'COST_NOT_YET_RECOVERED' if saving <= overhead else 'REAL_LEARNING_COST_USEFUL',
    'session_id':session['session_id'],'session_sha256':digest(session),'source_sha256':raw(seal_path),
    'verified_profile_id':profile['id'],'receipts':receipts,'distinct_roots':True,
    'signed_manager_events':2,'signed_witness_tip':tip,'raw_recovery_files':len(files),
    'source_files_unchanged':len(source['files']),'protected_files_unchanged':len(protected['files']),
    'offline':{'tests':254,'failures':0,'errors':0,'skips':0,'pytest_wall_seconds':suite.get('time'),
               'gate':read(REC/'output_offline/status.json'),'physics_guard':read(REC/'output_offline/physics_guard.json')},
    'records':record_rows,'methods':methods,'light_metrics':metrics_rows,
    'light_summary':{'count':11,'additional_wall_ns_sum':sum(light_wall),'additional_wall_ns_median':statistics.median(light_wall),
                    'additional_wall_ns_max':max(light_wall),'additional_cpu_ns_sum':sum(light_cpu),
                    'additional_cpu_ns_median':statistics.median(light_cpu),'additional_cpu_ns_max':max(light_cpu),
                    'wall_percent_max':str(max(Decimal(m['wall_percent']) for m in metrics_rows)),
                    'rss_delta_bytes_max':max(m['rss_delta_bytes'] for m in metrics_rows),
                    'rss_is_transient_peak':False,
                    'added_record_and_sidecar_bytes':sum(m['additional_record_bytes']+m['metrics_bytes']+m['request_cost_bytes'] for m in metrics_rows)},
    'cost_categories':dict(category),'cost_categories_overlap':'NESTED; DO_NOT_ADD_TO_JOB_TOTAL_OR_OUTER_ALLOCATION',
    'outer_phases':phases,'unclassified_outer_wait_and_gaps_ns':unclassified,
    'economics':{'scope':'ORIGINAL_FIRST_RESTART_CALL_THROUGH_FINAL_CONFIRMED_EXIT; INCLUDES_TWO_ADMIN_FAILURES_AND_STOPPED_GAPS',
        'allocation_ns':allocation,'baseline_full_wall_ns':before['full_wall_ns'],'learned_full_wall_ns':after['full_wall_ns'],
        'saving_per_observed_reuse_ns':saving,'observed_reuses':1,'learning_overhead_ns':overhead,
        'realized_saving_minus_overhead_ns':saving-overhead,'break_even_total_reuses':break_even,
        'additional_reuses_to_break_even':max(0,break_even-1),'future_reuses':'UNCONFIRMED; NOT_EXECUTED',
        'wall_ratio':str(Decimal(before['full_wall_ns'])/Decimal(after['full_wall_ns'])),
        'wall_reduction_percent':str(Decimal(saving)*100/Decimal(before['full_wall_ns'])),
        'baseline_full_cpu_ns':before['full_cpu_ns'],'learned_full_cpu_ns':after['full_cpu_ns'],
        'conservative_rate_window_estimate_usd':closure['estimated_rental_usd'],'invoice':'UNCONFIRMED',
        'allocation_host_cpu_and_energy':'UNMETERED; NO_CPU_MIN_OR_ENERGY_SUCCESS_CLAIM'},
    'closure':closure,'limitations':['UNRESOLVED_SHARED_RWFORCE','SAME_UID_NO_OS_ROLE_ISOLATION',
        'NO_PRODUCTION_CONNECTION','NO_N12_OR_GPU_OR_REAL_CPU_MIN_PILOT','NO_LONG_OUTAGE_OR_ACTUAL_PHYSICS_FAILED_SHUTDOWN_TEST']}
with (BASE/'author_closeout_analysis.json').open('xb') as f: f.write(canonical(result))
print(json.dumps({k:result[k] for k in ('loop_status','economics_status','raw_recovery_files','source_files_unchanged',
    'protected_files_unchanged','methods','light_summary','economics','cost_categories','outer_phases','unclassified_outer_wait_and_gaps_ns')},ensure_ascii=True))
