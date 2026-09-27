"""Same-j trees, independent checker arithmetic, and output-changing faults."""
from copy import deepcopy
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import ast
import json

import pytest

from a_reference import c1b1_same_input_filter as S
from a_reference import c1b1_same_input_checker as C
from a_reference import c1b1_quotient_gap_survey as Q
from a_reference import c1b1_outer_bootstrap as O

ROOT = Path(__file__).resolve().parents[1]


def at(poly,j):
    return sum(c*j**k for k,c in poly.items())


def toy(count=9,m=2):
    p,q,v,b,c,a,r = {0:55,1:-4,2:1},{0:100},{0:100},{0:1},1,{0:1},{0:10,1:-8,2:2}
    problem = {'p':p,'q':q,'v':v,'b':b,'c':c,'a':a,'r':r,'count':count,'m':m}
    return (p,q,v,b,c,a,r,count,m),problem


def test_same_input_tree_removes_false_overlap_without_enumerating_all_points():
    args,p = toy()
    old = Q.range_exclusion(*args[:7],args[7],args[8])
    assert old['resolution'] == 'unresolved'
    result = S.filter_problem(*args)
    assert result['resolution'] == 'whole_class_lower_bound_candidate'
    assert C._verify_tree(p,result['tree']) == result['visited_nodes']
    leaves = []
    def walk(node):
        if node['method']=='split':
            for child in node['children']: walk(child)
        else: leaves.append(node)
    walk(result['tree'])
    assert any(x['j_domain'][1]>x['j_domain'][0] and x['method']=='joint_polynomial_sign' for x in leaves)
    assert len(leaves)<p['count']
    assert any(claim[2]=='quadratic_integer_min' for node in leaves for claim in node.get('h_signs',[]))
    for j in range(p['count']):
        assert min(abs(2*at(p['p'],j)-h*at(p['q'],j)) for h in range(-21,22,2))>=p['m']


@pytest.mark.parametrize('count,m',[(1,1),(2,2),(4,1),(9,2),(16,2),(17,2),(9,4),(37,2)])
def test_filter_never_promotes_overlap_or_partial_cover(count,m):
    args,p = toy(count,m)
    result = S.filter_problem(*args)
    gaps = [min(abs(2*at(p['p'],j)-h*at(p['q'],j)) for h in range(-101,102,2)) for j in range(count)]
    if result['tree'] is not None:
        assert min(gaps)>=m
        C._verify_tree(p,result['tree'])
    if result['actual_witness'] is not None:
        w=result['actual_witness']
        assert w['odd_h']%2==1 and 0<=w['j']<count
        assert 2*at(p['p'],w['j'])-w['odd_h']*at(p['q'],w['j'])==w['signed_gap']
        assert abs(w['signed_gap'])<m
    assert result['interval_overlap_implies_actual_input'] is False


@pytest.mark.parametrize('lo,hi,degree',[(0,8,2),(1,9,5),(8,8,6)])
def test_checker_integer_controls_match_independent_fraction_formula(lo,hi,degree):
    poly={0:7,1:-4,2:3}
    controls=C.scaled_controls(poly,lo,hi,degree)
    import math
    values=tuple(F(x,math.factorial(degree)) for x in controls)
    # Compare the independent checker to the existing Fraction range formula.
    shifted=Q.V._shift(poly,lo,1)
    assert values==Q.bernstein(shifted,hi-lo,degree)
    for n in range((hi-lo)*4+1):
        j=lo+F(n,4)
        assert min(values)<=at(poly,j)<=max(values)


def test_odd_h_and_noninvertible_multiplier_preserved():
    p,q,v,b,c,a,r,count,m = {0:2},{0:2},{0:2},{0:1},2,{0:4},{},10,1
    safe=S.filter_problem(p,q,v,b,c,a,r,count,m)
    assert safe['tree'] is not None
    C._verify_tree({'p':p,'q':q,'v':v,'b':b,'c':c,'a':a,'r':r,'count':count,'m':m},safe['tree'])
    tied=S.filter_problem({0:1},q,v,b,c,{0:2},r,count,m)
    assert tied['resolution']=='actual_small_gap_input'
    assert tied['actual_witness']['signed_gap']==0


def test_positive_denominator_is_not_guessed():
    result=S.filter_problem({0:1},{0:-2},{0:-2},{0:1},1,{0:-1},{},3,1)
    assert result['resolution']=='unresolved' and result['actual_witness'] is None


def test_negative_numerator_and_nonunit_multiplier_keep_exact_odd_gap():
    p,q,v,b,c,a,r = {0:-55,1:4,2:-1},{0:100},{0:100},{0:1},3,{0:-3},{0:-30,1:24,2:-6}
    result=S.filter_problem(p,q,v,b,c,a,r,9,2)
    assert result['tree'] is not None
    C._verify_tree({'p':p,'q':q,'v':v,'b':b,'c':c,'a':a,'r':r,'count':9,'m':2},result['tree'])


def test_quadratic_lemma_cannot_be_used_for_actual_higher_degree():
    args,p=toy()
    p=deepcopy(p)
    p['p'][3]=1
    p['r'][3]=2
    inv=C.odd_inventory(p,0,8)
    assert inv[2]>0
    forged={'j_domain':[0,8],'method':'joint_polynomial_sign','odd_h_inventory':list(inv),
            'h_signs':[[h,1,'quadratic_integer_min'] for h in range(inv[0],inv[1]+1,2)]}
    with pytest.raises(O.NotCertified,match='higher degree'):
        C._verify_tree(p,forged)


def test_work_budget_does_not_manufacture_a_certificate(monkeypatch):
    args,_=toy(m=4)
    monkeypatch.setitem(S.POLICY,'max_nodes',1)
    result=S.filter_problem(*args)
    assert result['resolution']=='unresolved' and result['tree'] is None


@pytest.mark.parametrize('piece',[2,3,4,5,6])
def test_cleared_identity_faults_fail_closed(piece):
    args,_=toy()
    values=list(args)
    values[piece]=values[piece]+1 if piece==4 else {0:99}
    with pytest.raises(O.NotCertified):
        S.filter_problem(*values)


def test_wrong_same_j_range_helper_changes_output_and_checker_detects(monkeypatch):
    args,p=toy(9,4)  # j=2 has gap 2; it must not prove gap>=4.
    correct=S.filter_problem(*args)
    assert correct['tree'] is None
    monkeypatch.setattr(S,'joint_sign',lambda *args:[1,'quadratic_integer_min'])
    mutant=S.filter_problem(*args)
    assert mutant['tree'] is not None
    with pytest.raises(O.NotCertified,match='gap sign bound not proved'):
        C._verify_tree(p,mutant['tree'])


@pytest.fixture(scope='module')
def stored():
    return json.loads((ROOT/'a_reference/fixtures/c1b1_same_input_survey_v1.json').read_bytes())


def test_real_inventory_keeps_every_original_obligation(stored):
    prior=json.loads((ROOT/C.PRIOR).read_bytes())
    expected={(g['shell_index'],row[0]):row for g in prior['groups'] for row in g['class_rows'] if row[1]=='unresolved'}
    actual={(row[0],row[1]):row for row in stored['class_rows']}
    assert len(actual)==len(stored['class_rows'])==8076
    assert actual.keys()==expected.keys()
    for key,row in actual.items():
        assert row[3]==expected[key][5] and row[4]==expected[key][3]
    assert stored['all_original_8076_classes_surveyed'] is True
    assert stored['coverage_modified'] is False and stored['new_certified_regions']==0
    assert stored['global_4_4b']=='NotCertified' and stored['precision_cap']==16384
    assert stored['prior_coverage']['used_regions']==11 and stored['prior_coverage']['gap_count']==84
    assert stored['rational_gap_bound_is_full_impulse_certificate'] is False


def test_real_proofs_all_pass_an_independent_checker(stored):
    for proof in stored['proof_objects']:
        checked=C.verify_certificate(proof,proof['target'])
        assert checked['normalized_gap_lower']==proof['claim']['required_normalized_gap']
        assert checked['region_certified'] is False
    assert len(stored['proof_objects'])==stored['independently_verified_new_class_bound_count']


@pytest.mark.parametrize('fault',['threshold','common_factor','class_index','class_hash','identity_hash','endpoint','missing_child','odd_inventory','wrong_method'])
def test_corrupted_real_proof_is_rejected(stored,fault):
    assert stored['proof_objects']
    proof=deepcopy(stored['proof_objects'][0])
    target=deepcopy(proof['target'])
    if fault=='threshold': proof['claim']['required_normalized_gap']+=1
    elif fault=='common_factor': proof['claim']['common_factor']+=1
    elif fault=='class_index': proof['target']['class_index']+=1
    elif fault=='class_hash': proof['source']['normalized_class_sha256']='0'*64
    elif fault=='identity_hash': proof['source']['identity_sha256']='0'*64
    elif fault=='endpoint': proof['tree']['j_domain'][1]-=1
    elif fault=='missing_child': proof['tree']['children'].pop()
    else:
        leaf=proof['tree']
        while leaf['method']=='split': leaf=leaf['children'][0]
        if fault=='odd_inventory': leaf['odd_h_inventory'][0]+=2
        else: leaf['method']='status_only_certified'
    with pytest.raises(O.NotCertified):
        C.verify_certificate(proof,target)


def test_checker_rejects_builder_status_as_authority(stored):
    proof=deepcopy(stored['proof_objects'][0])
    proof.update(status='certified',pass_flag=True)
    proof['tree']={'j_domain':[0,proof['claim']['input_count']-1],'method':'certified'}
    with pytest.raises(O.NotCertified):
        C.verify_certificate(proof,proof['target'])


def test_checker_does_not_import_builder_or_its_arithmetic_helpers():
    tree=ast.parse((ROOT/'a_reference/c1b1_same_input_checker.py').read_text())
    banned=('c1b1_same_input_filter','c1b1_quotient_gap_survey','c1b1_residue_class_survey','c1b1_modular_distance_survey')
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in node.names]+([node.module] if isinstance(node,ast.ImportFrom) else [])
            assert not any(any(b in (name or '') for b in banned) for name in names)


def test_fixture_source_bindings(stored):
    for path,digest in stored['source_sha256'].items():
        assert sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest


def test_prior_hash_fault_is_rejected_after_cache_population(monkeypatch):
    C.foundation_guard()
    original=Path.read_bytes
    monkeypatch.setattr(Path,'read_bytes',lambda p:original(p)+b' ' if p==ROOT/C.PRIOR else original(p))
    with pytest.raises(O.NotCertified,match='prior fixture changed'):
        C.foundation_guard()
