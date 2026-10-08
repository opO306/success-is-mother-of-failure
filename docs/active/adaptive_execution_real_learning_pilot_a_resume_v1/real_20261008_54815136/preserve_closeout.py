"""Administrative byte-preserving packaging. No project imports or tests."""
from pathlib import Path
import hashlib, json
source = Path(__file__).resolve().parent
repo = source.parents[2]
destination = repo/'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1/real_20261008_54815136'
assert destination.resolve().is_relative_to((repo/'docs/active/adaptive_execution_real_learning_pilot_a_resume_v1').resolve())
if destination.exists(): raise ValueError('EXCLUSIVE_OUTPUT_REQUIRED')
source_files = sorted(p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
destination.mkdir(parents=True)
manifest = {}
total = 0
for path in source_files:
    name = path.relative_to(source).as_posix(); payload = path.read_bytes()
    target = destination/name; target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f: f.write(payload)
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    assert actual == hashlib.sha256(payload).hexdigest(), name
    manifest[name] = {'sha256':actual,'bytes':len(payload)}; total += len(payload)
record = {'schema':'A_RESUME_CLOSEOUT_PRESERVATION_MANIFEST_V1','authority':'RAW_BYTE_COPY_ONLY',
    'all_three_administrative_attempts_preserved':True,'recovered_original_files':111,
    'files':manifest,'file_count':len(manifest),'total_bytes':total,
    'excluded':['__pycache__'],'source_modifications':False,'project_imports':0,'project_tests':0,'physics_calls':0}
with (destination/'preservation_manifest.json').open('xb') as f:
    f.write(json.dumps(record,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
print(json.dumps({'destination':str(destination),'files':len(manifest),'bytes':total,
    'manifest_sha256':hashlib.sha256((destination/'preservation_manifest.json').read_bytes()).hexdigest()}))
