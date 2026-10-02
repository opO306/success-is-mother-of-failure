"""Pilot 1: deterministic verification of endpoints and J raw, no trajectories."""
from __future__ import annotations
import ast, copy, hashlib, itertools, json, math, random, types
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path
from time import perf_counter
import a_reference.c1b1_two_atom as REF
import a_numeric.exp as EXP
from a_numeric.profiles import FixedPoint, Binary64Finite, VMHalt
from . import candidate_a as A
from . import candidate_b as B
from . import fast_primitives as FP
from . import checker as CK

HERE=Path(__file__).resolve().parent
OUT=HERE/'results'
PROFILES=[{'kind':'FX','width':64,'frac':48}, {'kind':'FX','width':128,'frac':111},
          {'kind':'B64'}, {'kind':'CARRY','width':64,'fine':111}]

def profile(spec):
    if spec['kind']=='FX': return FixedPoint(spec['width'],spec['frac'])
    if spec['kind']=='B64': return Binary64Finite()
    return REF.CarryMomentum(spec['fine'],spec['width'])

def normalize(v):
    if isinstance(v,Q): return str(v)
    if isinstance(v,(tuple,list)): return [normalize(x) for x in v]
    if isinstance(v,dict): return {k:normalize(x) for k,x in v.items()}
    return v

def write(name,value):
    OUT.mkdir(exist_ok=True)
    (OUT/name).write_text(json.dumps(normalize(value),indent=2,sort_keys=True)+'\n')

def trace(module,dr,dt,spec):
    """Observe actual impulse/decision code, using copied globals, no module patch."""
    model_bits,decisions=[],[]
    namespace=dict(module.impulse.__globals__)
    real_model,real_decide=namespace['_model'],namespace['_decide']
    def observed_model(r2,M,ret):
        model_bits.append(M)
        return real_model(r2,M,ret)
    def observed_decide(p,at):
        steps=[]; decisions.append(steps)
        def observed(M):
            a,b=at(M); steps.append({'M':M,'lo':str(a),'hi':str(b)}); return a,b
        return real_decide(p,observed)
    namespace.update(_model=observed_model,_decide=observed_decide)
    fn=types.FunctionType(module.impulse.__code__,namespace,module.impulse.__name__)
    try: outcome=('value',fn(dr,dt,profile(spec)))
    except VMHalt as exc: outcome=('halt',exc.reason)
    except (REF.PhysicsDomainExceeded,REF.ReferenceUndecided,REF.ContractViolation) as exc:
        outcome=('error',exc.reason)
    return {'outcome':outcome,'model_bits':model_bits,'decisions':decisions}

def raw_radius(value,M,width=0):
    scaled=value*(1<<M)
    return math.floor(scaled),math.ceil(scaled)+width

def primitive_checks():
    counts=Counter()
    intervals=[(a,b) for a in range(-5,6) for b in range(a,6)]
    for M in (0,3,128):
        for a,b in itertools.product(intervals,repeat=2):
            assert FP._mul(a,b,M)==REF._mul(a,b,M),(M,a,b)
            counts['mul_signed_grid']+=1
        for a in intervals:
            for b in [(c,d) for c in range(1,6) for d in range(c,6)]:
                assert FP._div_pos(a,b,M)==REF._div_pos(a,b,M)
                counts['positive_division']+=1
            for c in map(Q,['-3/7','0','1','7/3']):
                assert FP._scale(a,c)==REF._scale(a,c)
                counts['scale']+=1
    rng=random.Random(2026100201)
    for M in (128,256,512,1024):
        threshold=math.ceil(Q(M*(1<<M))*FP.LN2_UPPER)
        ends=[0,1,1<<M,threshold-1,threshold,threshold+1]
        ends += [rng.randrange(0,200*(1<<M)) for _ in range(24)]
        ends += [(1<<(M+j))+delta for j in range(8) for delta in (-1,0,1)]
        for end in ends:
            for width in (0,1,17):
                x=(end,end+width); expected=REF._exp_neg(x,M)
                assert FP._exp_neg(x,M)==expected,(M,x)
                assert CK.exponential(CK.Cell.from_raw(x,M)).raw()==expected
                counts['exp_with_independent_checker']+=1
        for _ in range(40):
            lo=rng.randrange(1,40*(1<<M));hi=lo+rng.randrange(0,10*(1<<M))
            expected={n:((1<<(M*(n+1)))//hi**n,-((-(1<<(M*(n+1))))//lo**n))
                      for n in (1,2,*range(4,18))}
            assert FP._inverse_table(lo,hi,M)==expected
            counts['inverse_table']+=1
            r2=Q(rng.randrange(1,10**12),rng.randrange(1,10**5))
            assert FP._radius(r2,M)==CK.radius_raw(r2,M)
            counts['radius']+=1
    fractions=[Q(0),Q(1),Q(-1)]
    for e in (-1200,-1075,-1074,-1022,-113,-112,-111,-49,-48,0,51,52,1023,1024):
        for m in (Q(1),Q(3,2),Q(1,2),Q(1)-Q(1,2**53)):
            fractions += [s*m*Q(2)**e for s in (-1,1)]
    for spec in PROFILES+[{'kind':'FX','width':8,'frac':7}]:
        p=profile(spec)
        for v in fractions:
            try: actual=('value',p.from_exact(v))
            except VMHalt as exc: actual=('halt',exc.reason)
            assert CK.round_raw(v,spec)==actual,(spec,v)
            counts['independent_rounding']+=1
    return dict(counts)

def structural_checks():
    """Independent AST acceptance check, distinct from numerical tests."""
    def funcs(path):
        return {f.name:f for f in ast.parse(path.read_bytes()).body if isinstance(f,ast.FunctionDef)}
    def dump(f):
        f=copy.deepcopy(f)
        if isinstance(f.body[0],ast.Expr) and isinstance(f.body[0].value,ast.Constant) and isinstance(f.body[0].value.value,str):
            f.body=f.body[1:]
        return ast.dump(f,include_attributes=False)
    refs=funcs(Path(REF.__file__));aa=funcs(Path(A.__file__));bb=funcs(Path(B.__file__))
    r=copy.deepcopy(refs['_model_R'])
    v_uses=[n for n in ast.walk(r) if isinstance(n,ast.Name) and n.id=='V']
    assert len(v_uses)==6,len(v_uses)
    removed=[]
    def prune(stmts):
        out=[]
        for s in stmts:
            if isinstance(s,ast.Assign):
                ids=[ast.unparse(x) for x in s.targets]
                if ids==['V','dV']: s.targets=s.targets[1:]
                elif ids==['V']:
                    assert isinstance(s.value,ast.Call) and ast.unparse(s.value.func)=='_add'
                    calls={ast.unparse(x.func) for x in ast.walk(s.value) if isinstance(x,ast.Call)}
                    assert calls<={'_add','_neg','_scale','_mul','power'},calls
                    removed.append(ast.unparse(s));continue
            if isinstance(s,ast.For): s.body=prune(s.body)
            if isinstance(s,ast.Return):
                assert ast.unparse(s.value)=='(V, dV, inv[1])'
                s.value.elts=s.value.elts[1:]
            out.append(s)
        return out
    r.body=prune(r.body)
    assert len(removed)==2
    assert dump(r)==dump(aa['_model_R'])
    assert dump(refs['_model'])==dump(aa['_model'])
    impulse=copy.deepcopy(refs['impulse'])
    for n in ast.walk(impulse):
        if isinstance(n,ast.Assign) and ast.unparse(n.targets[0])=='(_, dV, inv1)':n.targets[0].elts=n.targets[0].elts[1:]
    assert dump(impulse)==dump(aa['impulse'])==dump(bb['impulse'])
    for s in r.body:
        if isinstance(s,ast.Assign) and ast.unparse(s.targets[0])=='inv':
            s.value=ast.parse('_inverse_table(lo, hi, M)',mode='eval').body
    assert dump(r)==dump(bb['_model_R'])
    used={1}
    for short,(_,C,_) in REF.L.COMPONENTS.values():
        for _,coefs in short.values():
            for i,c in coefs.items():
                if c:
                    if i<0:used.add(-i)
                    if i and i-1<0:used.add(1-i)
        for k in C:used.update((2*k,2*k+1))
    assert used=={1,2,*range(4,18)}
    import sympy as sp
    x=sp.Symbol('x',integer=True);powers=FP._raw_powers(x)
    for n in used:assert sp.expand(powers[n]-x**n)==0
    imports=[]
    for n in ast.walk(ast.parse(Path(CK.__file__).read_text())):
        if isinstance(n,ast.Import):imports += [a.name for a in n.names]
        if isinstance(n,ast.ImportFrom):imports.append(n.module or '')
    assert not any(s.startswith(('a_reference','a_numeric','candidate','fast_primitives')) for s in imports)
    return {'a_live_ast_equal':True,'b_live_ast_equal_modulo_certified_inverse_table':True,
            'impulse_ast_equal_modulo_pair_unpack':True,'deleted_assignments':removed,
            'inverse_exponents_proved_symbolically':sorted(used),'checker_imports':imports,
            'proof_type':'AST certificate plus exact primitive lemmas; not a Lean/Coq proof'}


# Fresh execution is exclusively run_pilot.py; no legacy summary or search entry point.
