"""Fail-closed provenance checks. A saved PASS flag has no authority."""
from __future__ import annotations
import hashlib
import json
import platform
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CLOSURE = ('primitives', 'structure', 'fixed', 'high', 'dataset', 'mutations')
PROMOTION = (*CLOSURE, 'audit', 'local_full', 'trajectory', 'benchmark')
CHECK_KEYS = {
    'primitives': {'primitive_comparisons'},
    'structure': {'a_live_ast_equal','b_live_ast_equal_modulo_certified_inverse_table','impulse_ast_equal_modulo_pair_unpack'},
    'fixed': {'endpoints_equal'}, 'high': {'endpoints_equal'},
    'dataset': {'all_input_profile_endpoint_and_raw_equal'},
    'mutations': {'every_fault_detected'},
    'audit': {'reviewed_source_matches','primitive_audit','repo_ast_equivalence'},
    'local_full': {'exit_zero','no_failures','no_errors','no_actual_skips','baseline_not_reduced'},
    'trajectory': {'all_impulses_equal','all_states_equal','same_refusal_step','scattering_completed'},
    'benchmark': {'completed','repeat_results_equal'},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_bytes(canonical(value) + b'\n')


def inventory(root=ROOT):
    # A source inventory is metadata only: do not scan ignored runs or open unrelated content.
    tracked = subprocess.check_output(['git','ls-files','-z'], cwd=root).decode('utf-8').split('\0')
    untracked = subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'], cwd=root).decode('utf-8').split('\0')
    suffixes = {'.py','.cpp','.cu','.cuh','.h','.hpp','.json','.toml'}
    paths = {root / rel for rel in (*tracked,*untracked) if rel and Path(rel).suffix in suffixes}
    paths.update((root / 'experiments/verified_superoptimizer_c1b1').glob('*.py'))
    paths.update((root / 'experiments/verified_superoptimizer_c1b1').glob('*.json'))
    paths.update((root / 'tests').glob('test_c1b1_candidate_b*.py'))
    paths.update((root / 'a_reference').glob('c1b1_fast*.py'))
    paths.update((root / 'a_reference').glob('c1b1_impulse_primitives.py'))
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(paths)}


def create_run(directory, input_path, required=CLOSURE):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    data = Path(input_path).read_bytes()
    (directory / 'inputs.json').write_bytes(data)
    sources = inventory()
    git = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    blobs = subprocess.check_output(['git', 'ls-files', '-s', 'a_reference', 'a_numeric'], cwd=ROOT, text=True)
    manifest = dict(run_id=str(uuid.uuid4()), git_commit=git, git_index_blobs=blobs,
                    source=sources, source_hash=digest(sources), input_hash=sha(directory / 'inputs.json'),
                    candidate_hash=sources['experiments/verified_superoptimizer_c1b1/candidate_b.py'],
                    checker_hash=sources['experiments/verified_superoptimizer_c1b1/checker.py'],
                    profile_version='c1b1-two-atom-v2 / half_even / original cap=16384',
                    environment=dict(python=sys.version, executable=sys.executable,
                                     platform=platform.platform(), machine=platform.machine()),
                    required=list(required), stages=[])
    write(directory / 'manifest.json', manifest)
    return manifest


def binding(m):
    return {k: m[k] for k in ('run_id', 'source_hash', 'input_hash', 'candidate_hash', 'checker_hash', 'profile_version')}


def _safe_file(directory, rel):
    path = (directory / rel).resolve()
    if not path.is_relative_to(directory.resolve()) or not path.is_file():
        raise ValueError('missing or escaped artifact')
    return path


def valid_payload(directory, name, payload):
    """Check retained coverage and comparisons, independently of saved PASS flags.

    This is a provenance/integrity check, not protection against a party forging
    every artifact and hash, and not a substitute for the mathematical checker.
    """
    import decimal
    from collections import Counter
    def read(path):
        return json.loads(Path(path).read_bytes(), parse_int=lambda s: int(decimal.Decimal(s)))
    def equal_values(values, expected):
        return set(values) == set(expected) and all(v == values['REF'] for v in values.values())
    if not payload:
        return False
    if name == 'primitives':
        return payload == dict(exp_with_independent_checker=648,independent_rounding=575,
                               inverse_table=160,mul_signed_grid=13068,positive_division=2970,radius=160,scale=792)
    if name == 'structure':
        return (all(payload.get(k) is True for k in CHECK_KEYS[name]) and
                payload.get('inverse_exponents_proved_symbolically') == [1,2,*range(4,18)] and
                len(payload.get('deleted_assignments',[])) == 2 and
                payload.get('checker_imports') == ['__future__','json','dataclasses','fractions','math','pathlib'])
    if name in ('fixed','high'):
        rows = read(directory / f'{name}.endpoints.json')
        tiers = (2048,4096,8192,16384) if name == 'high' else (128,256,512,1024)
        names = ('REF','A','B','FAST') if name == 'high' else ('REF','A','B','FAST','checker')
        return (rows == payload and len(rows) == (4 if name == 'high' else 80) and
                Counter(r['M'] for r in rows) == Counter({M:1 if name == 'high' else 20 for M in tiers}) and
                all(r['equivalent'] is True and equal_values(r['values'],names) for r in rows))
    if name == 'dataset':
        inputs = read(directory / 'inputs.json')
        records = inputs['impulses'] if isinstance(inputs,dict) else inputs
        default = [dict(kind='FX',width=64,frac=48),dict(kind='FX',width=128,frac=111),dict(kind='B64'),
                   dict(kind='CARRY',width=64,fine=111),dict(kind='FX',width=96,frac=80)]
        expected = Counter((r['id'],canonical(p)) for r in records for p in r.get('profiles',default))
        observed = Counter()
        count = 0
        with (directory / 'dataset.endpoints.jsonl').open('rb') as f:
            for line in f:
                row = json.loads(line,parse_int=lambda s: int(decimal.Decimal(s)))
                count += 1
                observed[row['id'],canonical(row['profile'])] += 1
                if row.get('equivalent') is not True or not equal_values(row['values'],('REF','A','B','FAST','checker')):
                    return False
        return observed == expected and count == payload.get('cases') and count > 0
    if name == 'mutations':
        rows = read(directory / 'mutations.witnesses.json')
        expected = {'exp_lower_-1','exp_lower_+1','sqrt_upper_minus_one','inverse_power_contaminated',
                    'multiplication_sign_branch_flipped','division_endpoint_direction_swapped','dV_term_deleted',
                    'REJECTED_rounded_reciprocal_recurrence'}
        return (rows == payload and len(rows) == 8 and {r['name'] for r in rows} == expected and
                all(r['detected'] is True and r['expected'] != r['mutant'] for r in rows))
    if name == 'audit':
        return (payload.get('primitive_audit') == 'PASS' and bool(payload.get('reviewed_sources')) and
                all(sha(ROOT / p) == h for p,h in payload['reviewed_sources'].items()))
    if name == 'local_full':
        import xml.etree.ElementTree as ET
        cases = ET.parse(directory / 'local_full.junit.xml').getroot().findall('.//testcase')
        good = sum(all(c.find(k) is None for k in ('failure','error','skipped')) for c in cases)
        return (good == payload.get('passed') and good >= 3289 and payload.get('returncode') == 0 and
                all(c.find('failure') is None and c.find('error') is None and
                    (c.find('skipped') is None or c.find('skipped').get('type') == 'pytest.xfail') for c in cases))
    if name == 'trajectory':
        import gzip
        inputs = read(directory / 'inputs.json')
        specs = [*inputs['trajectories'],*inputs['refusals']]
        success = {s['id'] for s in inputs['trajectories']}
        expected = {r['id']:r for r in payload}
        counts,impulses = Counter(),Counter()
        hashes = {r['id']:hashlib.sha256() for r in payload}
        initials = set()
        with gzip.open(directory / 'trajectory.witnesses.jsonl.gz','rb') as f:
            for line in f:
                row = json.loads(line)
                key = row['id']
                if 'initial' in row:
                    initials.add(key)
                    continue
                if (row['REF_state'] != row['FAST_state'] or row['REF_impulses'] != row['FAST_impulses'] or
                        row['REF_result'] != row['FAST_result']):
                    return False
                counts[key] += 1
                impulses[key] += len(row['REF_impulses'])
                hashes[key].update(line)
        return (initials == {s['id'] for s in specs} == set(expected) and
                all(counts[k] == r['records'] and impulses[k] == r['impulses'] and
                    (r['end'] == 'outgoing_R20' if k in success else r['end'] in ('refusal','halt')) and
                    hashes[k].hexdigest() == r['witness_sha256'] for k,r in expected.items()))
    if name == 'benchmark':
        inputs = read(directory / 'inputs.json')
        reps = inputs['benchmark']['repetitions']
        samples = payload.get('samples',[])
        keys = Counter((s['rep'],s['method'],s['workload'],s.get('id')) for s in samples)
        expected = Counter((r,m,w,i) for r in range(reps) for m in ('REF','FAST')
                           for w,i in [('impulse',None),('step',None),*[('trajectory',s['id']) for s in inputs['trajectories']]])
        return (reps >= 3 and keys == expected and
                all(s['cpu_seconds'] > 0 and s['wall_seconds'] > 0 and
                    all(p['result_sha256'] == s['result_sha256'] and p['calls'] == s['calls'] for p in samples
                        if p['workload'] == s['workload'] and p.get('id') == s.get('id')) for s in samples))
    return False


def check_run(directory, *, live=True, required=None):
    directory = Path(directory)
    errors, failures = [], []
    try:
        m = json.loads((directory / 'manifest.json').read_bytes())
        bind = binding(m)
        if digest(m['source']) != m['source_hash']:
            errors.append('source inventory hash mismatch')
        if live and inventory() != m['source']:
            errors.append('live source mismatch')
        if sha(directory / 'inputs.json') != m['input_hash']:
            errors.append('input hash mismatch')
        if m['candidate_hash'] != m['source']['experiments/verified_superoptimizer_c1b1/candidate_b.py']:
            errors.append('candidate hash mismatch')
        if m['checker_hash'] != m['source']['experiments/verified_superoptimizer_c1b1/checker.py']:
            errors.append('checker hash mismatch')
        # The caller fixes the gate set, not an editable saved manifest.
        needed = tuple(required or CLOSURE)
        records = m['stages']
        for name in needed:
            found = [r for r in records if r.get('stage') == name]
            if len(found) != 1:
                errors.append(f'{name}: missing/duplicate stage')
                continue
            r = found[0]
            if any(r.get(k) != v for k, v in bind.items()):
                errors.append(f'{name}: mixed binding')
            expected_command = [m['environment']['executable'], '-u', '-m',
                                'experiments.verified_superoptimizer_c1b1.stage',
                                '--run', str(directory.resolve()), '--stage', name]
            if r.get('command') != expected_command or r.get('executed') is not True:
                errors.append(f'{name}: no execution')
            expected_files = {f'{name}.json', f'{name}.log'}
            if name in ('fixed','high'):
                expected_files.add(f'{name}.endpoints.json')
            elif name == 'dataset':
                expected_files.add('dataset.endpoints.jsonl')
            elif name == 'mutations':
                expected_files.add('mutations.witnesses.json')
            elif name == 'local_full':
                expected_files.update(('local_full.pytest.log','local_full.junit.xml'))
            elif name == 'trajectory':
                expected_files.add('trajectory.witnesses.jsonl.gz')
            if not expected_files <= r['outputs'].keys():
                errors.append(f'{name}: required output missing')
            if r.get('returncode') != 0:
                failures.append(f'{name}: return code {r.get("returncode")}')
            for rel, expected in r['outputs'].items():
                if sha(_safe_file(directory, rel)) != expected:
                    errors.append(f'{name}: output hash mismatch {rel}')
            result = json.loads(_safe_file(directory, r['result']).read_bytes())
            if any(result.get(k) != v for k, v in bind.items()) or result.get('stage') != name:
                errors.append(f'{name}: stale result')
            checks = result.get('checks')
            if not isinstance(checks, dict) or checks.keys() != CHECK_KEYS.get(name):
                errors.append(f'{name}: wrong check schema')
            elif any(v is not True for v in checks.values()):
                failures.append(f'{name}: failed checks')
            if not valid_payload(directory, name, result.get('payload')):
                errors.append(f'{name}: incomplete or inconsistent witness coverage')
            if r['result'] not in r['outputs']:
                errors.append(f'{name}: unhashed result')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f'invalid evidence: {type(exc).__name__}: {exc}')
    return dict(status='FAIL' if failures else 'INCOMPLETE' if errors else 'PASS',
                errors=errors, failures=failures)


def run_stage(directory, name):
    directory = Path(directory).resolve()
    m = json.loads((directory / 'manifest.json').read_bytes())
    if inventory() != m['source'] or sha(directory / 'inputs.json') != m['input_hash']:
        raise ValueError('source/input changed before stage')
    if any(r['stage'] == name for r in m['stages']):
        raise ValueError('a stage may execute only once per run')
    command = [sys.executable, '-u', '-m', 'experiments.verified_superoptimizer_c1b1.stage',
               '--run', str(directory), '--stage', name]
    with (directory / f'{name}.log').open('wb') as log:
        rc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
    outputs = {p.name: sha(p) for p in directory.glob(f'{name}.*') if p.is_file()}
    m['stages'].append(dict(**binding(m), stage=name, executed=True, command=command,
                           returncode=rc, outputs=outputs, result=f'{name}.json'))
    write(directory / 'manifest.json', m)
    if inventory() != m['source']:
        raise ValueError('source changed during stage')
    return rc
