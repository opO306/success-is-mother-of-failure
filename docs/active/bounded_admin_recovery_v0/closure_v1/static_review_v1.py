"""Local stdlib read-only review. AST/raw bytes only, no project/transport imports."""
import ast
import hashlib
import json
from pathlib import Path
import stat
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
T = HERE/'transport'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())
def functions(path):
    tree=ast.parse(Path(path).read_bytes())
    return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def sequence_length(node):
    if isinstance(node,(ast.List,ast.Tuple)): return len(node.elts)
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
        return sequence_length(node.left)+sequence_length(node.right)
    raise ValueError('NON_LITERAL_STATIC_CASE_SEQUENCE')
def write(path,obj):
    with path.open('xb') as f: f.write((json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


def main():
    syntax=[]
    for path in sorted(HERE.rglob('*.py')):
        ast.parse(path.read_bytes(),filename=str(path)); syntax.append(path.relative_to(ROOT).as_posix())
    preservation=[]
    before=read(HERE/'preservation_before.json')
    for check in before['checks']:
        path=ROOT/check['manifest']; manifest=read(path)
        assert sha(path)==check['raw_sha256']
        base=path.parent if path.name=='transport_seal_v3.json' else ROOT
        bad=[n for n,h in manifest['files'].items() if sha(base/n)!=h]
        assert not bad
        preservation.append(dict(manifest=check['manifest'],files=len(manifest['files']),mismatches=bad))
    oldzip=ROOT/read(HERE/'scope_protocol.json')['original_package']['archive']
    assert sha(oldzip)==before['original_zip_sha256']
    packages=[]; bindings=read(T/'package_bindings.json')
    for kind in ('A','B'):
        spec=bindings[kind]; inv=read(ROOT/spec['inventory']); archive=ROOT/spec['archive']
        assert sha(archive)==spec['zip_sha256'] and sha(ROOT/spec['inventory'])==spec['inventory_sha256']
        with zipfile.ZipFile(archive) as z:
            names=z.namelist(); assert len(names)==spec['entries']==len(set(names))==len({n.casefold() for n in names})
            assert set(names)==set(inv['files']) and z.testzip() is None
            assert sum(i.file_size for i in z.infolist())==inv['uncompressed_bytes']
            for info in z.infolist():
                n=info.filename
                assert n and '\\' not in n and ':' not in n and '\x00' not in n and not n.startswith('/')
                assert all(p not in ('','.','..') for p in n.split('/'))
                assert not info.is_dir() and not info.flag_bits&1 and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG)
                assert hashlib.sha256(z.read(n)).hexdigest()==inv['files'][n]
            if kind=='A':
                with zipfile.ZipFile(oldzip) as old:
                    assert len(old.namelist())==813
                    assert set(names)-set(old.namelist())=={spec['addition_path']}
                    assert all(z.read(n)==old.read(n) for n in old.namelist())
                assert inv['files'][spec['addition_path']]==spec['addition_sha256']==sha(ROOT/spec['addition_path'])
                ids=read(ROOT/spec['case_inventory'])['ids']; assert len(ids)==len(set(ids))==320
                assert sha(ROOT/spec['case_inventory'])==spec['case_inventory_sha256']
            else:
                seal=read(ROOT/spec['local_code_seal']); assert sha(ROOT/spec['local_code_seal'])==spec['code_sha256']
                assert dict(seal['files'],**{'admin_policy/source_seal.json':spec['code_sha256']})==inv['files']
                for n in spec['original_policy_files']: assert z.read(n)==(ROOT/n).read_bytes()
                for n in ('offline.py','guard.py','pytest.ini'):
                    assert z.read('admin_policy/'+n)==(HERE/'policy_harness'/n).read_bytes()
        packages.append(dict(package_kind=kind,entries=spec['entries'],zip_sha256=spec['zip_sha256'],
                             inventory_sha256=spec['inventory_sha256'],raw_bytes_verified=inv['uncompressed_bytes']))
    gate=read(HERE/'package_A/package_gate_result.json')
    assert gate['status']=='COMPLETE_DECLARED_ONLY' and not gate['execution_authorized']
    transport_seal=read(T/'transport_seal.json')
    for n,h in transport_seal['files'].items(): assert sha(T/n)==h
    templates=[]
    for kind in ('A','B'):
        a=read(T/f'approval_UNAPPROVED_{kind}.json'); spec=bindings[kind]
        assert all(a[k] is False for k in ('explicit_user_approval','new_window_separately_authorized','restart_exact_instance_authorized','exclusive'))
        assert a['approval_reference'] is None and a['approved_utc'] is None and a['prior_failed_attempts']==3
        assert a['prior_tablet_gate_attempts']==1 and a['transport_seal_sha256']==sha(T/'transport_seal.json')
        assert a['zip_sha256']==spec['zip_sha256'] and a['inventory_sha256']==spec['inventory_sha256']
        templates.append(dict(kind=kind,status='UNAPPROVED_FALSE_BITS_CONFIRMED; NO_RUNTIME_CALL'))
    original=ROOT/'docs/active/adaptive_experience_tablet_v0/admin_transport_static_20261009'
    copies=[]
    for name in ('supervisor.py','guest_probe.py','guest_recover.py'):
        assert (T/name).read_bytes()==(original/name).read_bytes(); copies.append(dict(name=name,raw_sha256=sha(T/name)))
    oldf=functions(original/'controller.py'); newf=functions(T/'controller.py')
    retained=[n for n in ('utc','canonical','sha','write','load') if oldf[n]==newf[n]]
    assert len(retained)==5
    oldclass=next(n for n in ast.parse((original/'controller.py').read_bytes()).body if isinstance(n,ast.ClassDef))
    newclass=next(n for n in ast.parse((T/'controller.py').read_bytes()).body if isinstance(n,ast.ClassDef))
    methods=lambda c:{n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef)}
    method_retained=[n for n in ('run','py','upload') if methods(oldclass)[n]==methods(newclass)[n]]
    assert len(method_retained)==3
    generic=functions(ROOT/'experiments/adaptive_execution_real_learning_pilot_v0/guardian.py')
    supervisor=functions(T/'supervisor.py')
    assert all(generic[n]==supervisor[n] for n in ('Cli','confirm_stop'))
    oldgate=functions(ROOT/'experiments/bounded_admin_recovery_v0/package_gate.py')
    newgate=functions(HERE/'package_gate_v1.py')
    unchanged=[n for n in oldgate if n!='main' and oldgate[n]==newgate[n]]
    assert set(unchanged)==set(oldgate)-{'main'}
    test=ROOT/'tests/bounded_admin_recovery_v0/test_bounded_admin_recovery_v0.py'
    testtree=ast.parse(test.read_bytes()); case_rows=[]
    for n in testtree.body:
        if not isinstance(n,ast.FunctionDef) or not n.name.startswith('test_'): continue
        count=1
        for d in n.decorator_list:
            if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr=='parametrize':
                count*=sequence_length(d.args[1])
        case_rows.append(dict(function=n.name,static_expected_cases=count))
    assert len(case_rows)==17 and sum(r['static_expected_cases'] for r in case_rows)==95
    source=(T/'controller.py').read_text(encoding='utf-8')
    assert 'checks = local_preflight(approval)' in source and "if KIND == 'A': validate_policy_receipt(approval)" in source
    assert "'B_GATE_MUST_FINISH_BEFORE_A_APPROVAL'" in source and 'self.age() + 140 + 96 >= self.handoff()' in source
    assert "PRIOR_POLICY_FEE_BOUND + Decimal('0.25') * 600 / 3600" in source
    assert "campaign_total_cap_usd='0.05'" in source
    assert source.index('checks = local_preflight(approval)')<source.index('out.mkdir(exist_ok=False)')
    # Cross-file path contract: the raw retained probe accepts this prefix only.
    probe=(T/'guest_probe.py').read_text(encoding='utf-8')
    assert "'/workspace/tablet_v0_' + KIND.lower()" in source and "root.name.startswith('tablet_v0_')" in probe
    write(HERE/'static_review_result.json',dict(status='STATIC_CHECKS_MATCH_DECLARED_SCOPE',
          syntax_parsed_files=syntax,packages=packages,preservation=preservation,unapproved_templates=templates,
          verbatim_transport_files=copies,unchanged_controller_functions=retained,unchanged_controller_methods=method_retained,
          generic_guardian_Cli_confirm_stop_AST_unchanged=True,package_gate_core_AST_unchanged=unchanged,
          changed_controller_show_reason='Additional conservative B+A campaign fee bound; prior identity/rate checks preserved',
          policy_test_static_count=95,policy_test_functions=case_rows,
          official_dynamic_policy_passes=0,official_dynamic_tablet_passes=0,project_imports=0,local_project_tests=0,
          paid_actions=0,remote_calls=0,limitations='AST and raw hashes; does not demonstrate runtime refusal, shell/network behavior, OS isolation or termination'))
    print(json.dumps(dict(status='STATIC_CHECKS_MATCH_DECLARED_SCOPE',A_entries=814,B_entries=10,
                         static_policy_count=95,dynamic_tests=0,remote_calls=0)))


if __name__=='__main__': main()
