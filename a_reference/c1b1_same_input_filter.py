"""Bounded same-j gap trees and a complete survey of the open class inventory.

All exclusions recombine (A-c*h*B)*V+R before ranging a polynomial.
Remaining interval overlap and work limits never imply an actual input.
"""
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
from pathlib import Path
import json

from a_reference import c1b1_quotient_gap_survey as Q
from a_reference import c1b1_residue_class_survey as V
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_same_input_checker as C
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_outer_bootstrap as O

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-same-input-correlation-survey-v1'
POLICY = {'max_depth':4,'max_nodes':31,'max_odd_h_per_leaf':16,
          'refine_all_classes_with_input_count_at_most':16,
          'representatives_per_shell':4,'max_original_classes':9000}


def inventory(p,q,lo,hi,m):
    pp,qq = (V._shift(poly,lo,1) for poly in (p,q))
    degree = max(max(pp,default=0),max(qq,default=0))
    qc = Q.bernstein(qq,hi-lo,degree)
    if min(qc) <= 0:
        return None
    radius = m-1
    lower = Q.ratio_range(Q._add(Q._scale(pp,2),{0:-radius}),qq,hi-lo)
    upper = Q.ratio_range(Q._add(Q._scale(pp,2),{0:radius}),qq,hi-lo)
    first,last = Q._ceil(lower[0]),Q._floor(upper[1])
    first += (1-first)%2
    last -= (last-1)%2
    return [first,last,max(0,(last-first)//2+1)]


def joint_sign(a,b,v,r,c,h,lo,hi,m):
    # The same-j cancellation happens BEFORE taking an enclosure.
    f = Q._add(V._multiply(Q._add(a,Q._scale(b,-c*h)),v),r)
    if max(f,default=0) <= 2:
        # Exact minimum on INTEGER j. A continuous interval may contain a
        # spurious root between lattice inputs; no sample inference is used.
        for side in (1,-1):
            poly = Q._scale(f,side)
            candidates = {lo,hi}
            if poly.get(2,0)>0:
                vertex = F(-poly.get(1,0),2*poly[2])
                candidates.update(max(lo,min(hi,j)) for j in (Q._floor(vertex),Q._ceil(vertex)))
            if min(V._at(poly,j) for j in candidates) >= c*m:
                return [side,'quadratic_integer_min']
    shifted = V._shift(f,lo,1)
    controls = Q.bernstein(shifted,hi-lo,max(shifted,default=0))
    if min(controls) >= c*m:
        return [1,'bernstein_sign']
    if max(controls) <= -c*m:
        return [-1,'bernstein_sign']
    return None


def filter_problem(p,q,v,b,c,a,r,count,m,*,refine=True):
    """Synthetic/public arithmetic core; certificates get real source bindings separately."""
    Q._require(type(count) is int and count>0 and type(m) is int and m>0,'positive class size and threshold required')
    Q.validate_identity(p,q,v,b,c,a,r)
    nodes,leaves,seen_h,why = 0,0,0,Counter()
    actual = None
    root_inventory = None
    def visit(lo,hi,depth):
        nonlocal nodes,leaves,seen_h,actual,root_inventory
        if nodes >= POLICY['max_nodes']:
            why['node_work_budget'] += 1
            return None
        nodes += 1
        candidates = inventory(p,q,lo,hi,m)
        if depth == 0:
            root_inventory = candidates
        if candidates is None:
            why['positive_denominator_unproved'] += 1
            return None
        first,last,total = candidates
        leaf = {'j_domain':[lo,hi],'odd_h_inventory':candidates}
        if total == 0:
            leaves += 1
            return {**leaf,'method':'odd_range_empty'}
        if total <= POLICY['max_odd_h_per_leaf']:
            signs = []
            for h in range(first,last+1,2):
                seen_h += 1
                side = joint_sign(a,b,v,r,c,h,lo,hi,m)
                if side is None:
                    break
                signs.append([h,*side])
            if len(signs) == total:
                leaves += 1
                return {**leaf,'method':'joint_polynomial_sign','h_signs':signs}
        if lo == hi:
            pn,qn = V._at(p,lo),V._at(q,lo)
            Q._require(qn > 0,'positive actual denominator required')
            z = (2*pn % (2*qn))-qn
            if abs(z) < m:
                h = (2*pn-z)//qn
                Q._require(h%2 == 1,'actual odd quotient required')
                actual = {'j':lo,'odd_h':h,'signed_gap':z,
                          'full_impulse_rounding_failure_proved':False,'precision_cap_exceeded_proved':False}
                why['actual_small_gap_input'] += 1
            else:
                why['singleton_bound_unproved'] += 1
            return None
        if not refine:
            why['refinement_not_selected'] += 1
            return None
        if depth >= POLICY['max_depth']:
            why['depth_work_budget'] += 1
            return None
        middle = (lo+hi)//2
        left = visit(lo,middle,depth+1)
        right = visit(middle+1,hi,depth+1)
        if left is None or right is None:
            return None
        return {'method':'split','j_domain':[lo,hi],'mid':middle,'children':[left,right]}
    tree = visit(0,count-1,0)
    return {'resolution':'whole_class_lower_bound_candidate' if tree is not None else
                         'actual_small_gap_input' if actual is not None else 'unresolved',
            'tree':tree,'actual_witness':actual,'root_odd_h_inventory':root_inventory,
            'visited_nodes':nodes,'proved_leaf_count':leaves,'enumerated_h_count':seen_h,
            'unresolved_reason_counts':dict(why),'refinement_attempted':refine,
            'interval_overlap_implies_actual_input':False,'unproved_leaf_promoted':False}


def _load():
    C.foundation_guard()
    prior = json.loads((ROOT/C.PRIOR).read_bytes())
    packed = json.loads((ROOT/C.CLASSES).read_bytes())
    classes = V.unpacked_report(packed)
    rows = {(g['shell_index'],i):row for g in classes['groups'] for i,row in enumerate(g['classes'])}
    obligations = [(g,row) for g in prior['groups'] for row in g['class_rows'] if row[1]=='unresolved']
    Q._require(len(obligations)==8076 and len(obligations)<=POLICY['max_original_classes'], 'original unresolved inventory changed')
    return prior,rows,obligations


def _selected(obligations):
    chosen = { (g['shell_index'],row[0]) for g,row in obligations
               if row[5] <= POLICY['refine_all_classes_with_input_count_at_most'] }
    representatives = {}
    for shell in (18,17,16,15):
        items = [(g,row) for g,row in obligations if g['shell_index']==shell and row[5]>16]
        # Fixed before solving: smallest/largest N, smallest/largest threshold.
        orders = ((lambda x:x[1][5],False),(lambda x:x[1][5],True),
                  (lambda x:x[1][3].bit_length(),False),(lambda x:x[1][3].bit_length(),True))
        picks = [sorted(items,key=lambda x:(key(x),x[1][0]),reverse=reverse)[0][1][0] for key,reverse in orders]
        representatives[shell] = sorted(set(picks))
        chosen.update((shell,index) for index in picks)
    return chosen,representatives


def example_report(raw_path=None,proof_path=None):
    prior,rows,obligations = _load()
    selected,representatives = _selected(obligations)
    p,q,_,d = K.frozen_identity()
    raw = prior['raw_remainder_identity']
    raw = {**raw,'quotient':{int(k):v for k,v in raw['quotient'].items()},
                'remainder':{int(k):v for k,v in raw['remainder'].items()}}
    sink = None if raw_path is None else Path(raw_path).open('x',encoding='utf-8',newline='\n')
    proof_sink = None if proof_path is None else Path(proof_path).open('x',encoding='utf-8',newline='\n')
    summaries,proofs,witnesses,examples = [],[],[],{}
    classifications,failures = Counter(),Counter()
    try:
        for group,old in obligations:
            target = {'shell_index':group['shell_index'],'class_index':old[0]}
            key = target['shell_index'],target['class_index']
            row = rows[key]
            problem = Q.normalized_identity(p,q,d,raw,row)
            pp,qq,v,b,c,a,r,g = problem
            m = (group['required_raw_M']+g-1)//g
            Q._require(m==old[3],'normalized threshold differs from original obligation')
            result = filter_problem(pp,qq,v,b,c,a,r,row['input_count'],m,refine=key in selected)
            hcount = None if result['root_odd_h_inventory'] is None else result['root_odd_h_inventory'][2]
            classification = 'positivity_unproved' if hcount is None else 'bounded_odd_h' if hcount <= C.MAX_ODD_H else 'wide_odd_h_inventory'
            classifications[classification] += 1
            failures.update(result['unresolved_reason_counts'])
            proof = None
            if result['tree'] is not None:
                source = {'prior_fixture_sha256':C.PRIOR_HASH,'class_fixture_sha256':C.CLASS_HASH,
                          'normalized_class_sha256':row['normalized_polynomial_sha256'],
                          'identity_sha256':V._hash_polynomials({0:c},a,r,v,b)}
                claim = {'normalized_gap_lower':m,'required_normalized_gap':m,'input_count':row['input_count'],
                         'raw_required_M':group['required_raw_M'],'common_factor':g}
                proof = {'version':C.VERSION,'status':'candidate','target':target,'source':source,'claim':claim,'tree':result['tree']}
                verified = C.verify_certificate(proof,target)
                result['independent_verification'] = verified
                proofs.append(proof)
                if proof_sink is not None:
                    proof_sink.write(json.dumps(proof,separators=(',',':'))+'\n')
            if result['actual_witness'] is not None:
                witness = {**result['actual_witness'],'target':target,
                           'n':row['first_n']+result['actual_witness']['j']*2**row['v2_n']*5**row['v5_n']*row['unit_modulus']}
                C.verify_witness(witness,target)
                witnesses.append(witness)
            detail = {'target':target,'input_count':row['input_count'],'required_normalized_gap':m,
                      'classification':classification,**result}
            line = json.dumps(T.serial(detail),sort_keys=True,separators=(',',':'))+'\n'
            if sink is not None:
                sink.write(line)
            examples.setdefault((target['shell_index'],result['resolution'],row['input_count']<=16),detail)
            summaries.append((target['shell_index'],target['class_index'],result['resolution'],row['input_count'],m,
                              hcount,result['visited_nodes'],result['proved_leaf_count'],key in selected,
                              sha256(line.encode()).hexdigest()))
    finally:
        if sink is not None: sink.close()
        if proof_sink is not None: proof_sink.close()
    by_shell = []
    for shell in (18,17,16,15):
        subset = [x for x in summaries if x[0]==shell]
        certified = [x for x in subset if x[2]=='whole_class_lower_bound_candidate']
        by_shell.append({'shell_index':shell,'original_unresolved_class_count':len(subset),
                         'independently_verified_new_class_bounds':len(certified),
                         'verified_classes_with_more_than_16_inputs':sum(x[3]>16 for x in certified),
                         'verified_input_count':sum(x[3] for x in certified),
                         'remaining_unresolved_class_count':sum(x[2]=='unresolved' for x in subset),
                         'actual_small_gap_class_count':sum(x[2]=='actual_small_gap_input' for x in subset),
                         'root_odd_h_count_range':(min(x[5] for x in subset if x[5] is not None),
                                                  max(x[5] for x in subset if x[5] is not None))})
    verified_count = len(proofs)
    return {'version':VERSION,'status':'survey_only','global_4_4b':'NotCertified','policy':POLICY,
            'representative_class_indices':representatives,'refinement_selected_class_count':len(selected),
            'classification_counts':dict(classifications),'unresolved_reason_counts':dict(failures),
            'all_original_8076_classes_surveyed':True,'class_row_fields':('shell','class_index','resolution','input_count',
                'required_normalized_gap','root_odd_h_count','visited_nodes','proved_leaves','refinement_selected','detail_sha256'),
            'class_rows':summaries,'groups':by_shell,'proof_objects':proofs,'actual_witnesses':witnesses,
            'diagnostic_examples':list(examples.values()),'independently_verified_new_class_bound_count':verified_count,
            'previous_survey_class_bound_count':6195,'combined_class_bound_count':6195+verified_count,
            'whole_shell_lemma_count':0,'new_certified_regions':0,'coverage_modified':False,
            'prior_coverage':prior['prior_coverage'],'precision_cap':16384,
            'rational_gap_bound_is_full_impulse_certificate':False,
            'interval_overlap_is_actual_input':False,'builder_status_is_certification_authority':False,
            'independent_checker_scope':'class rational gap only; frozen physics/numeric foundation shared',
            'prior_fixture_sha256':{C.PRIOR:C.PRIOR_HASH,C.CLASSES:C.CLASS_HASH},
            'source_sha256':{name:sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in
                             ('a_reference/c1b1_same_input_filter.py','a_reference/c1b1_same_input_checker.py')}}


if __name__ == '__main__':
    import sys
    report = example_report(sys.argv[2] if len(sys.argv)>2 else None,sys.argv[3] if len(sys.argv)>3 else None)
    output = json.dumps(T.serial(report),separators=(',',':'))+'\n'
    if len(sys.argv)>1:
        Path(sys.argv[1]).write_text(output,encoding='utf-8')
    else:
        print(output)
