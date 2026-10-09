"""Stdlib AST/hash review only. Do not import or exercise project/transport functions."""
import ast
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=HERE.parent/'closure_v1'
T=HERE/'transport'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_bytes())
def dump(node): return ast.dump(node,include_attributes=False)
def named(nodes,kind): return {n.name:n for n in nodes if isinstance(n,kind)}
def write(path,obj):
    with path.open('xb') as f: f.write((json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())


class ShowCapOnly(ast.NodeTransformer):
    def visit_Constant(self,node):
        if node.value=='0.10': return ast.copy_location(ast.Constant(value='0.05'),node)
        return node


class ClosureFieldsOnly(ast.NodeTransformer):
    def visit_Call(self,node):
        self.generic_visit(node)
        if isinstance(node.func,ast.Name) and node.func.id=='dict' and any(k.arg=='gate_returncode' for k in node.keywords) and any(k.arg=='actual_stop_confirmed' for k in node.keywords):
            node.keywords=[k for k in node.keywords if k.arg not in ('prior_policy_actual_execution_fee_usd','budget_protocol_sha256','observed_utc')]
            for k in node.keywords:
                if k.arg=='campaign_total_cap_usd': k.value=ast.Constant(value='0.05')
        return node


def main():
    syntax=[]
    for p in sorted(HERE.rglob('*.py')):
        ast.parse(p.read_bytes(),filename=str(p)); syntax.append(p.relative_to(ROOT).as_posix())
    protocol=read(HERE/'budget_protocol.json'); seal=read(T/'transport_seal.json')
    assert sha(HERE/'budget_protocol.json')==read(HERE/'protocol_seal.json')['files']['budget_protocol.json']==seal['budget_protocol_sha256']
    assert sha(OLD/'closure_seal.json')==protocol['previous_closure_seal_sha256']
    oldclosure=read(OLD/'closure_seal.json')
    for name,h in oldclosure['files'].items(): assert sha(ROOT/name)==h,name
    for item in read(OLD/'preservation_before.json')['checks']:
        p=ROOT/item['manifest']; assert sha(p)==item['raw_sha256']
        anchor=p.parent if p.name=='transport_seal_v3.json' else ROOT
        for name,h in read(p)['files'].items(): assert sha(anchor/name)==h,name
    for name,h in seal['files'].items(): assert sha(T/name)==h,name
    assert seal['campaign_total_cap_usd']=='0.10' and seal['each_total_cap_usd']=='0.05' and seal['execution_authorized'] is False
    unchanged=[]
    for name in read(OLD/'transport/transport_seal.json')['files']:
        if name=='controller.py': continue
        assert (T/name).read_bytes()==(OLD/'transport'/name).read_bytes(),name
        unchanged.append(name)
    packages=[]
    bindings=read(T/'package_bindings.json')
    assert bindings==seal['packages']==read(OLD/'transport/package_bindings.json')
    for kind in ('A','B'):
        spec=bindings[kind]; inv=read(ROOT/spec['inventory'])
        assert sha(ROOT/spec['archive'])==spec['zip_sha256'] and sha(ROOT/spec['inventory'])==spec['inventory_sha256']
        with zipfile.ZipFile(ROOT/spec['archive']) as z:
            assert len(z.namelist())==spec['entries'] and set(z.namelist())==set(inv['files']) and z.testzip() is None
            for name,h in inv['files'].items(): assert hashlib.sha256(z.read(name)).hexdigest()==h,name
        packages.append(dict(kind=kind,entries=spec['entries'],raw_hashes_match=True,zip_sha256=spec['zip_sha256']))
    oldtree=ast.parse((OLD/'transport/controller.py').read_bytes())
    newtree=ast.parse((T/'controller.py').read_bytes())
    oldfunctions=named(oldtree.body,ast.FunctionDef); newfunctions=named(newtree.body,ast.FunctionDef)
    changed_functions=[]
    for name,node in oldfunctions.items():
        if dump(node)!=dump(newfunctions[name]): changed_functions.append(name)
    assert set(changed_functions)=={'local_preflight','validate_policy_receipt'}
    policy=copy.deepcopy(newfunctions['validate_policy_receipt'])
    assert dump(policy.body[-1])==dump(ast.parse('validate_B_cost_confirmation(approval, path, closure)').body[0])
    policy.body.pop(); assert dump(policy)==dump(oldfunctions['validate_policy_receipt'])
    oldmethods=named(named(oldtree.body,ast.ClassDef)['Transport'].body,ast.FunctionDef)
    newmethods=named(named(newtree.body,ast.ClassDef)['Transport'].body,ast.FunctionDef)
    changed_methods=[n for n in oldmethods if dump(oldmethods[n])!=dump(newmethods[n])]
    assert set(changed_methods)=={'show','execute'}
    assert dump(ShowCapOnly().visit(copy.deepcopy(newmethods['show'])))==dump(oldmethods['show'])
    assert dump(ClosureFieldsOnly().visit(copy.deepcopy(newmethods['execute'])))==dump(oldmethods['execute'])
    source=(T/'controller.py').read_text(encoding='utf-8')
    assert "if KIND == 'A': validate_policy_receipt(approval)" in source
    assert "PRIOR_POLICY_FEE_BOUND = max(PRIOR_POLICY_FEE_BOUND, actual)" in source
    assert "cost.get('human_confirmed') is not True" in source and "cost.get('cost_basis') != 'PROVIDER_REPORTED_EXECUTION_FEE'" in source
    assert "not closed <= confirmed <= approved" in source
    assert "not actual.is_finite() or not 0 <= actual <= Decimal('0.05')" in source
    assert source.index('checks = local_preflight(approval)')<source.index('out.mkdir(exist_ok=False)')
    templates=[]
    for kind in ('B','A'):
        a=read(T/f'approval_UNAPPROVED_{kind}.json')
        assert a['campaign_total_cap_usd']=='0.10' and a['total_cap_usd']=='0.05'
        assert a['transport_seal_sha256']==sha(T/'transport_seal.json') and a['budget_protocol_sha256']==sha(HERE/'budget_protocol.json')
        assert a['schema']=='PACKAGE_CLOSURE_BUDGET_SUPPLEMENT_V1_NEW_WINDOW_HUMAN_APPROVAL'
        for key in ('explicit_user_approval','new_window_separately_authorized','restart_exact_instance_authorized','exclusive'):
            assert a[key] is False
        for key,val in [('allocation_seconds',600),('compute_seconds',120),('aggregate_cpu_seconds',120),('cpu_affinity_count',1),('memory_bytes',536870912),('recovery_deadline_seconds',420),('stop_confirmation_seconds',180),('prior_failed_attempts',3),('prior_tablet_gate_attempts',1)]:
            assert a[key]==val
        if kind=='A':
            assert a['policy_gate_receipt'] is None and a['B_cost_confirmation'] is None and a['B_cost_confirmation_sha256'] is None
        templates.append(dict(kind=kind,sha256=sha(T/f'approval_UNAPPROVED_{kind}.json'),execution_authorized=False))
    cost=read(T/'B_cost_confirmation_UNCONFIRMED.json')
    assert cost['human_confirmed'] is False and cost['actual_execution_fee_usd'] is None and cost['raw_files']=={}
    worst=2*Fraction(25,100)*600/3600
    assert worst==Fraction(1,12) and worst<Fraction(10,100)
    write(HERE/'static_review_result.json',dict(status='BUDGET_SUPPLEMENT_STATIC_READY',
          budget_protocol_sha256=sha(HERE/'budget_protocol.json'),transport_seal_sha256=sha(T/'transport_seal.json'),
          old_closure_files_unchanged=len(oldclosure['files']),unchanged_transport_files=unchanged,packages=packages,
          changed_existing_function_copies=changed_functions,changed_Transport_methods=changed_methods,
          sole_added_runtime_function='validate_B_cost_confirmation',policy_gate_prefix_AST_unchanged=True,
          show_AST_only_campaign_cap_change=True,execute_AST_only_budget_receipt_fields_change=True,
          separate_false_approval_templates=templates,cost_confirmation_unconfirmed=True,
          exact_max_two_window_execution_fee_usd={'numerator':worst.numerator,'denominator':worst.denominator},
          each_seconds=600,campaign_cap_usd='0.10',each_cap_usd='0.05',syntax_parsed_files=syntax,
          local_project_dynamic_tests=0,paid_actions=0,remote_calls=0,
          limitations='AST and raw hash checks only; no runtime refusal, provider billing authentication, supervisor/guardian dynamics or remote test demonstrated'))
    print(json.dumps(dict(status='BUDGET_SUPPLEMENT_STATIC_READY',old_files_unchanged=len(oldclosure['files']),
                         dynamic_tests=0,paid_actions=0,exact_max_fee='1/12 USD < 0.10 USD')))


if __name__=='__main__': main()
