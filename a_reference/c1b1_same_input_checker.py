"""Recheck same-input gap trees without importing their builder or survey.

The frozen component identity and its existing foundation guard are shared
trust anchors. Class partition arithmetic and Bernstein checks are rebuilt.
This checks a class rational-gap claim, never a whole impulse/region claim.
"""
from fractions import Fraction as F
from functools import lru_cache
from hashlib import sha256
from math import comb, factorial, gcd
from pathlib import Path
import json

from a_reference import c1b1_family_checker as K
from a_reference import c1b1_outer_bootstrap as O
from a_reference import c1b1_source_binding as SA

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-same-input-gap-proof-v1'
PRIOR = 'a_reference/fixtures/c1b1_quotient_gap_survey_v1.json'
PRIOR_HASH = '33492859bb776a72aa47df768451417595dd8f8773c89f87e2e36819a5c32594'
CLASSES = 'a_reference/fixtures/c1b1_residue_class_survey_v1.json'
CLASS_HASH = 'f209b3d32fffb2e2807f22b7099fbfcf55cc2499836437328e6b35c855368c3d'
MAX_NODES = 31
MAX_DEPTH = 4
MAX_ODD_H = 16


def require(condition, reason):
    if not condition:
        raise O.NotCertified(reason)


def integer(x):
    require(type(x) is int, 'exact integer required')
    return x


def _hash(path):
    return sha256((ROOT/path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


@lru_cache(maxsize=1)
def _inputs():
    require(_hash(PRIOR) == PRIOR_HASH and _hash(CLASSES) == CLASS_HASH, 'same-input prior fixture changed')
    prior = json.loads((ROOT/PRIOR).read_bytes())
    classes = json.loads((ROOT/CLASSES).read_bytes())
    for obj in (prior, classes):
        for path, digest in obj['source_sha256'].items():
            require(SA.source_matches(ROOT/path, digest), 'same-input prior source changed')
    table = {(g['shell_index'], i): dict(zip(classes['class_row_fields'], row))
             for g in classes['groups'] for i, row in enumerate(g['class_rows'])}
    obligations = {(g['shell_index'], row[0]): (row, g['required_raw_M'])
                   for g in prior['groups'] for row in g['class_rows'] if row[1] == 'unresolved'}
    return prior, table, obligations


def foundation_guard():
    K.foundation_guard()
    # Cache parsed data only; recheck the file bindings at every public entry.
    prior, _, _ = _inputs()
    require(_hash(PRIOR) == PRIOR_HASH and _hash(CLASSES) == CLASS_HASH, 'same-input prior fixture changed')
    for path, digest in prior['source_sha256'].items():
        require(SA.source_matches(ROOT/path, digest), 'same-input prior source changed')


def _add(*polys):
    result = {}
    for p in polys:
        for k,c in p.items():
            result[k] = result.get(k,0)+c
    return {k:c for k,c in result.items() if c}


def _scale(p, s):
    return {k:s*c for k,c in p.items() if s*c}


def _multiply(a,b):
    result = {}
    for i,x in a.items():
        for j,y in b.items():
            result[i+j] = result.get(i+j,0)+x*y
    return {k:c for k,c in result.items() if c}


def _compose(p, start, step):
    """Compose by repeated multiplication, independently of builder shifts."""
    result = {}
    for power in range(max(p,default=0),-1,-1):
        result = _multiply(result,{0:start,1:step})
        result = _add(result,{0:p.get(power,0)})
    return result


def _divide(p, divisor):
    require(divisor > 0 and all(c%divisor == 0 for c in p.values()), 'class common factor not proved')
    return {k:c//divisor for k,c in p.items()}


def _poly_hash(*polys):
    rows = tuple(tuple(sorted(p.items())) for p in polys)
    return sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()


@lru_cache(maxsize=1)
def _frozen():
    return K.frozen_identity()


@lru_cache(maxsize=512)
def _rebuild(shell,index):
    prior, table, obligations = _inputs()
    require((shell,index) in obligations, 'target is not an original unresolved class')
    row = table[shell,index]
    old, required = obligations[shell,index]
    p,q,_,d = _frozen()
    count,start = row['input_count'],row['first_n']
    step = 2**row['v2_n']*5**row['v5_n']*row['unit_modulus']
    g = 2**row['common_25_orders_lower'][0]*5**row['common_25_orders_lower'][1]
    dh = 2**row['valuations_P2_P5_D2_D5'][2][0]*5**row['valuations_P2_P5_D2_D5'][3][0]
    pp,qq = (_divide(_compose(poly,start,step),g) for poly in (p,q))
    dd = _divide(_compose(d,start,step),dh)
    require(_poly_hash(pp,qq,dd) == row['normalized_polynomial_sha256'], 'rebuilt class polynomial mismatch')
    require(row['last_n'] == start+(count-1)*step and count == old[5], 'original class endpoint mismatch')
    divisor = _multiply(dd,dd)
    unit = {0:start//(2**row['v2_n']*5**row['v5_n']),1:row['unit_modulus']}
    b = {0:1}
    for _ in range(17):
        b = _multiply(b,unit)
    x2,x5 = row['normalized_Q_scalar_orders']
    b = _scale(b,2**x2*5**x5)
    require(_multiply(b,divisor) == qq, 'rebuilt variable factor identity mismatch')
    raw = prior['raw_remainder_identity']
    a0,r0 = ({int(k):v for k,v in raw[name].items()} for name in ('quotient','remainder'))
    c = raw['multiplier']*g
    a = _scale(_compose(a0,start,step),dh*dh)
    r = _compose(r0,start,step)
    common = c
    for value in (*a.values(),*r.values()):
        common = gcd(common,abs(value))
    c,a,r = c//common,_divide(a,common),_divide(r,common)
    require(_add(_multiply(a,divisor),r) == _scale(pp,2*c), 'rebuilt cleared identity mismatch')
    return {'p':pp,'q':qq,'v':divisor,'b':b,'c':c,'a':a,'r':r,'count':count,
            'g':g,'m':(required+g-1)//g,'raw_M':required,'start':start,'step':step,
            'class_hash':row['normalized_polynomial_sha256'],
            'identity_hash':_poly_hash({0:c},a,r,divisor,b)}


def scaled_controls(p, lo, hi, degree):
    """Integer controls multiplied by degree!, on [lo,hi].

    This checker uses integer factorial scaling, not builder Fraction controls.
    """
    require(0 <= lo <= hi and max(p,default=0) <= degree, 'invalid proof interval')
    shifted = _compose(p,lo,hi-lo)
    return tuple(sum(shifted.get(k,0)*comb(i,k)*factorial(k)*factorial(degree-k)
                     for k in range(i+1)) for i in range(degree+1))


def odd_inventory(problem,lo,hi):
    degree = max(max(problem['p'],default=0),max(problem['q'],default=0))
    pc = scaled_controls(problem['p'],lo,hi,degree)
    qc = scaled_controls(problem['q'],lo,hi,degree)
    require(min(qc)>0,'positive denominator not proved')
    radius = (problem['m']-1)*factorial(degree)
    lower = min(F(2*x-radius,y) for x,y in zip(pc,qc))
    upper = max(F(2*x+radius,y) for x,y in zip(pc,qc))
    first = -((-lower.numerator)//lower.denominator)
    last = upper.numerator//upper.denominator
    first += (1-first)%2
    last -= (last-1)%2
    return first,last,max(0,(last-first)//2+1)


def _verify_tree(problem, tree):
    nodes = 0
    def visit(node,lo,hi,depth):
        nonlocal nodes
        nodes += 1
        require(nodes <= MAX_NODES and depth <= MAX_DEPTH,'proof tree work budget exceeded')
        require(type(node) is dict and node.get('j_domain') == [lo,hi], 'proof partition missing or mismatched')
        kind = node.get('method')
        if kind == 'split':
            require(lo < hi, 'singleton cannot be split')
            mid = integer(node.get('mid'))
            require(lo <= mid < hi and type(node.get('children')) is list and len(node['children']) == 2,
                    'incomplete split cover')
            visit(node['children'][0],lo,mid,depth+1)
            visit(node['children'][1],mid+1,hi,depth+1)
            return
        first,last,count = odd_inventory(problem,lo,hi)
        require(node.get('odd_h_inventory') == [first,last,count], 'odd h inventory altered or incomplete')
        if kind == 'odd_range_empty':
            require(count == 0, 'odd quotient range is not empty')
            return
        require(kind == 'joint_polynomial_sign' and 0 < count <= MAX_ODD_H,'unknown or unbounded leaf lemma')
        signs = node.get('h_signs')
        require(type(signs) is list and len(signs) == count,'odd h exclusion missing')
        for h,claim in zip(range(first,last+1,2),signs):
            require(type(claim) is list and len(claim) == 3 and integer(claim[0]) == h,'odd h changed')
            side = integer(claim[1])
            require(side in (-1,1),'invalid sign direction')
            # Recombine quotient, variable factors, and R at the SAME j.
            f = _add(_multiply(_add(problem['a'],_scale(problem['b'],-problem['c']*h)),problem['v']),problem['r'])
            require(f == _scale(_add(_scale(problem['p'],2),_scale(problem['q'],-h)),problem['c']),
                    'same-input polynomial identity failed')
            degree = max(f,default=0)
            signed = _scale(f,side)
            if claim[2] == 'quadratic_integer_min':
                require(degree <= 2,'quadratic lemma applied to a higher degree')
                points = {lo,hi}
                if signed.get(2,0)>0:
                    # Independent integer vertex calculation, no builder helper.
                    floor_vertex = (-signed.get(1,0))//(2*signed[2])
                    points.update(max(lo,min(hi,j)) for j in (floor_vertex-1,floor_vertex,floor_vertex+1))
                lower = min(sum(coef*j**k for k,coef in signed.items()) for j in points)
                require(lower >= problem['c']*problem['m'],'claimed gap sign bound not proved')
            else:
                require(claim[2] == 'bernstein_sign','unknown same-input sign lemma')
                controls = scaled_controls(signed,lo,hi,degree)
                require(min(controls) >= problem['c']*problem['m']*factorial(degree), 'claimed gap sign bound not proved')
    visit(tree,0,problem['count']-1,0)
    return nodes


def verify_certificate(proof, expected_target):
    """The caller supplies the expected target; proof status grants no authority."""
    foundation_guard()
    try:
        require(type(proof) is dict and proof.get('version') == VERSION,'wrong same-input proof version')
        require(proof.get('target') == expected_target,'proof target substitution')
        shell,index = integer(expected_target['shell_index']),integer(expected_target['class_index'])
        problem = _rebuild(shell,index)
        source = proof['source']
        require(source == {'prior_fixture_sha256':PRIOR_HASH,'class_fixture_sha256':CLASS_HASH,
                           'normalized_class_sha256':problem['class_hash'],'identity_sha256':problem['identity_hash']},
                'proof source binding mismatch')
        require(type(proof['claim']) is dict and all(type(value) is int for value in proof['claim'].values()),
                'exact integer proof claims required')
        require(proof['claim'] == {'normalized_gap_lower':problem['m'],'required_normalized_gap':problem['m'],
                                  'input_count':problem['count'],'raw_required_M':problem['raw_M'],
                                  'common_factor':problem['g']},'proof threshold or input claim mismatch')
        nodes = _verify_tree(problem,proof['tree'])
        return {'scope':'original_class_rational_gap_only','target':expected_target,
                'normalized_gap_lower':problem['m'],'input_count':problem['count'],'verified_nodes':nodes,
                'region_certified':False,'full_impulse_rounding_certified':False}
    except (KeyError,TypeError,ValueError,IndexError) as error:
        raise O.NotCertified(f'invalid same-input proof: {error}') from error


def verify_witness(witness, expected_target):
    foundation_guard()
    try:
        require(witness['target'] == expected_target,'witness target substitution')
        p = _rebuild(integer(expected_target['shell_index']),integer(expected_target['class_index']))
        j,h = integer(witness['j']),integer(witness['odd_h'])
        require(0 <= j < p['count'] and h%2 == 1,'invalid actual witness input or parity')
        at = lambda poly:sum(c*j**k for k,c in poly.items())
        z = 2*at(p['p'])-h*at(p['q'])
        require(at(p['q'])>0 and abs(z)<p['m'],'witness is not a small normalized gap')
        require(witness['n'] == p['start']+p['step']*j and witness['signed_gap'] == z,'witness value mismatch')
        require(witness['full_impulse_rounding_failure_proved'] is False and witness['precision_cap_exceeded_proved'] is False,
                'rational witness was promoted beyond its scope')
        return {'scope':'rational_sufficient_condition_counterexample','signed_gap':z,'raw_gap':p['g']*abs(z)}
    except (KeyError,TypeError,ValueError,IndexError) as error:
        raise O.NotCertified(f'invalid same-input witness: {error}') from error
