"""Reject byte-valid snapshots without completed producer and exact final evidence."""
from lifecycle import decode
import xml.etree.ElementTree as ET

def require_terminal(files, *, writer_completion_verified, spec, original_case_ids=None):
    if writer_completion_verified is not True:raise ValueError('IMPORTANT_WRITER_COMPLETION_UNCONFIRMED')
    required={'gate_exit.json','output/status.json','output/junit.xml','output/physics_guard.json'}
    if spec['expected_tests']==320:required.add('output/benchmark.json')
    if not required.issubset(files):raise ValueError('IMPORTANT_FINAL_FILES_MISSING')
    exit=decode(files['gate_exit.json']);status=decode(files['output/status.json'])
    if type(exit.get('returncode')) is not int or exit.get('returncode')!=0 or 'error' not in exit or exit['error'] is not None:raise ValueError('IMPORTANT_GATE_NOT_TERMINAL_SUCCESS')
    if status.get('status')!='PASS' or status.get('tests')!=spec['expected_tests']:raise ValueError('IMPORTANT_FINAL_STATUS')
    if status.get('code_sha256')!=spec['code_sha256'] or status.get('protocol_sha256')!=spec['protocol_sha256']:raise ValueError('IMPORTANT_FINAL_SOURCE_BINDING')
    if any(status.get(k)!=0 for k in ('failed','errors','skipped','physics_calls','gpu_calls')):raise ValueError('IMPORTANT_FINAL_SCOPE')
    if any(type(status.get(k)) is not int or not 0<=status[k]<=120*10**9 for k in ('wall_ns','cpu_ns')):raise ValueError('IMPORTANT_FINAL_RESOURCE_BOUND')
    if spec['expected_tests']==95 and (type(status.get('process_tree_peak_rss_bytes')) is not int or not 0<=status['process_tree_peak_rss_bytes']<=536870912):raise ValueError('IMPORTANT_FINAL_MEMORY_BOUND')
    if status.get('benchmark_complete') is not (spec['expected_tests']==320):raise ValueError('IMPORTANT_FINAL_BENCHMARK_STATUS')
    if spec['expected_tests']==95 and status.get('package_kind')!='B':raise ValueError('IMPORTANT_FINAL_B_PACKAGE_KIND')
    cases=ET.fromstring(files['output/junit.xml']).findall('.//testcase');ids=[c.attrib['classname']+'::'+c.attrib['name'] for c in cases]
    if len(ids)!=spec['expected_tests'] or len(set(ids))!=len(ids) or any(c.find(t) is not None for c in cases for t in ('failure','error','skipped')):raise ValueError('IMPORTANT_FINAL_JUNIT')
    if original_case_ids is not None and set(ids)!=set(original_case_ids):raise ValueError('IMPORTANT_ORIGINAL_CASE_IDS')
    guard=decode(files['output/physics_guard.json'])
    if guard.get('blocked_attempts')!=[] or guard.get('new_physics_calls')!=0 or guard.get('gpu_calls')!=0:raise ValueError('IMPORTANT_FINAL_GUARD')
    if spec['expected_tests']==320:
        benchmark=decode(files['output/benchmark.json'])
        if benchmark.get('complete') is not True or benchmark.get('repeats')!=31 or [r['records'] for r in benchmark.get('index_growth',[])]!=[100,1000,10000] or benchmark.get('physics_calls')!=0 or benchmark.get('gpu_calls')!=0:raise ValueError('IMPORTANT_FINAL_BENCHMARK')
    return dict(writer_completion_verified=True,final_files_verified=True,tests=len(ids))
