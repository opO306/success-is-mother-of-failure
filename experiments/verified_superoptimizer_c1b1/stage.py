"""Fresh stage worker, with endpoints retained independently for all implementations."""
from __future__ import annotations
import argparse
import ast
import copy
import json
import sys
import types
from collections import Counter
from fractions import Fraction as Q
from pathlib import Path
from . import evidence as E, verify as V, checker as CK, fast_primitives as FP


def normalized(value):
    return V.normalize(value)


def trace(module, dr, dt, spec):
    """Clone globals for observation; never monkeypatch the live reference module."""
    namespace = dict(module.impulse.__globals__)
    actual_model, actual_decide = namespace['_model'], namespace['_decide']
    models, decisions = [], []
    def model(r2, M, ret):
        ans = actual_model(r2, M, ret)
        dv, inv = ans[1:] if module is V.REF else ans
        actual_g = namespace['_mul'](namespace['_neg'](dv),inv,M)
        models.append(dict(M=M, dV=dv, inv1=inv, F_over_R=actual_g))
        return ans
    def decide(p, at):
        attempts = []
        decisions.append(attempts)
        def observed(M):
            lo, hi = at(M)
            attempts.append(dict(M=M, lo=str(lo), hi=str(hi)))
            return lo, hi
        return actual_decide(p, observed)
    namespace.update(_model=model, _decide=decide)
    fn = types.FunctionType(module.impulse.__code__, namespace)
    try:
        outcome = ('value', fn(dr, dt, V.profile(spec)))
    except V.VMHalt as exc:
        outcome = ('halt', exc.reason)
    except (V.REF.PhysicsDomainExceeded, V.REF.ReferenceUndecided, V.REF.ContractViolation) as exc:
        outcome = ('error', exc.reason)
    return normalized(dict(outcome=outcome, models=models, decisions=decisions))


def independent_trace(dr, dt, spec):
    models = []
    def model(r2, M, ret):
        dv, inv = CK.model(r2, M, ret)
        models.append(dict(M=M, dV=dv, inv1=inv, F_over_R=CK.g_and_j(dv, inv, M, Q(1))[0]))
        return dv, inv
    result = CK.impulse(dr, dt, spec, model_function=model)
    return normalized(dict(outcome=result['outcome'], models=models, decisions=result['decisions']))


def endpoint_row(r2, M, ret, *, checker=True, radius=None):
    from a_reference import c1b1_fast_impulse as FAST
    values, g_values = {}, {}
    for name, mod in (('REF', V.REF), ('A', V.A), ('B', V.B), ('FAST',FAST)):
        model_r = mod._impulse_model_R_fast if name == 'FAST' else mod._model_R
        ans = mod._model(r2, M, ret) if radius is None else model_r(radius, M, ret)
        values[name] = ans[1:] if name == 'REF' else ans
        g_values[name] = mod._mul(mod._neg(values[name][0]), values[name][1], M)
    if checker:
        values['checker'] = CK.model(r2, M, ret) if radius is None else CK.model_r(radius, M, ret)
        g_values['checker'] = CK.g_and_j(*values['checker'], M, Q(1))[0]
    equal = all(v == values['REF'] for v in values.values()) and all(v == g_values['REF'] for v in g_values.values())
    # High-M integer decimal strings are large; keep digest per complete endpoint tuple.
    payload = {name: dict(endpoint_sha256=E.digest(normalized(v)),F_over_R_sha256=E.digest(g_values[name])) for name, v in values.items()}
    if M <= 1024:
        payload = {name: dict(dV=v[0], inv1=v[1], F_over_R=g_values[name],
                              endpoint_sha256=E.digest(normalized(v))) for name, v in values.items()}
    return normalized(dict(R2=str(r2), radius_raw=radius, M=M, ret=ret, values=payload, equivalent=equal))


def fixed(high=False):
    rows = []
    for M in ((2048, 4096, 8192, 16384) if high else (128, 256, 512, 1024)):
        radii = [Q(701, 7)] if high else [V.REF.R_MIN2, Q(50), Q(701, 7), Q(400), Q(10**10)]
        for r2 in radii:
            for ret in ((True,) if high else (False, True)):
                rows.append(endpoint_row(r2, M, ret, checker=not high))
                if not high:
                    lo, hi = FP._radius(r2, M)
                    rows.append(endpoint_row(r2, M, ret, radius=(lo, hi + (1 << M))))
        print('completed M', M, flush=True)
    return rows


def dataset(inputs, out):
    from a_reference import c1b1_fast_impulse as FAST
    hist, outcomes = Counter(), Counter()
    count = 0
    with out.open('wb') as f:
        for record in inputs:
            dr, dt = tuple(map(Q, record['dr'])), Q(record['dt'])
            specs = record.get('profiles', V.PROFILES + [dict(kind='FX', width=96, frac=80)])
            for spec in specs:
                values = {name: trace(mod, dr, dt, spec) for name, mod in (('REF', V.REF), ('A', V.A), ('B', V.B), ('FAST',FAST))}
                values['checker'] = independent_trace(dr, dt, spec)
                same = all(v == values['REF'] for v in values.values())
                row = dict(id=record['id'], dr=record['dr'], R2=str(sum(x*x for x in dr)),
                           dt_kick=str(dt), profile=spec, tags=record['tags'], values=values, equivalent=same)
                f.write(E.canonical(row) + b'\n')
                if not same:
                    raise AssertionError(f'differential mismatch {record["id"]} {spec}')
                hist[','.join(str(r['M']) for r in values['REF']['models']) or 'none'] += 1
                outcomes[str(values['REF']['outcome'][0:2] if values['REF']['outcome'][0] != 'value' else ['value'])] += 1
                count += 1
    return dict(cases=count, precision_histogram=dict(hist), outcomes=dict(outcomes))


def mutants():
    """Inject each requested fault into the implementation it actually changes."""
    rows = []
    M = 128
    x = (1 << M, (1 << M) + 17)
    expected = CK.exponential(CK.Cell.from_raw(x, M)).raw()
    def transformed(fn, transform, globals_update=None):
        import inspect
        tree = ast.parse(inspect.getsource(fn))
        transform(tree)
        ns = dict(fn.__globals__)
        ns.update(globals_update or {})
        code = ast.unparse(ast.fix_missing_locations(tree))
        exec(compile(code, '<injected_primitive>', 'exec'), ns)
        return ns[fn.__name__], E.digest(code)
    for delta in (-1, 1):
        def inject_exp(tree):
            tree.body[0].body[-1] = ast.parse(f'return value + ({delta} if not upper else 0)').body[0]
        side, source_hash = transformed(FP._exp_side, inject_exp)
        ns = dict(FP._exp_neg.__globals__, _exp_side=side)
        mutated_exp = types.FunctionType(FP._exp_neg.__code__, ns)
        mutant = mutated_exp(x, M)
        rows.append(dict(name=f'exp_lower_{delta:+d}', expected=expected, mutant=mutant,
                         mutant_source_hash=source_hash, detected=mutant != expected))
    r2 = Q(701, 7)
    root = FP._radius(r2, M)
    want = CK.radius_raw(r2, M)
    def inject_sqrt(tree):
        tree.body[0].body[-1] = ast.parse('return low, high - 1').body[0]
    bad_radius, source_hash = transformed(FP._radius, inject_sqrt)
    mutant = bad_radius(r2, M)
    rows.append(dict(name='sqrt_upper_minus_one', expected=want, mutant=mutant,
                     mutant_source_hash=source_hash, detected=mutant != want))
    lo, hi = root
    table = FP._inverse_table(lo, hi, M)
    def inject_power(tree):
        # +1 may be masked by division. An erroneous recurrence uses x twice at n=6.
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                node.body.append(ast.parse('if n == 6: p[n] *= x').body[0])
    bad_powers, source_hash = transformed(FP._raw_powers, inject_power)
    ns = dict(FP._inverse_table.__globals__, _raw_powers=bad_powers)
    bad_inverse = types.FunctionType(FP._inverse_table.__code__, ns)
    mutant = bad_inverse(lo,hi,M)[6]
    expected = CK.Cell.cover(1/Q(hi, 1 << M)**6, 1/Q(lo, 1 << M)**6, M).raw()
    rows.append(dict(name='inverse_power_contaminated', expected=expected, mutant=mutant,
                     mutant_source_hash=source_hash, detected=mutant != expected))
    a, b = (-5, -2), (2, 7)
    expected = CK.Cell.from_raw(a, 3).multiply(CK.Cell.from_raw(b, 3)).raw()
    def inject_mul(tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and ast.unparse(node) == 'low, high = (al * bh, ah * bl)':
                node.value = ast.parse('(ah * bl, al * bh)',mode='eval').body
    bad_mul, source_hash = transformed(FP._mul, inject_mul)
    mutant = bad_mul(a,b,3)
    rows.append(dict(name='multiplication_sign_branch_flipped', expected=expected, mutant=mutant,
                     mutant_source_hash=source_hash, detected=mutant != expected))
    a, b = (2, 5), (2, 7)
    expected = CK.Cell.from_raw(a, 3).divide(CK.Cell.from_raw(b, 3)).raw()
    def inject_div(tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and ast.unparse(node) == 'dl, dh = (b[1], b[0])':
                node.value = ast.parse('(b[0],b[1])',mode='eval').body
    bad_div, source_hash = transformed(FP._div_pos, inject_div)
    mutant = bad_div(a,b,3)
    rows.append(dict(name='division_endpoint_direction_swapped', expected=expected, mutant=mutant,
                     mutant_source_hash=source_hash, detected=mutant != expected))
    # Actual AST removal of a force accumulation in B, not a fabricated final result.
    tree = ast.parse(Path(V.B.__file__).read_text())
    removed = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            body = []
            for s in node.body:
                if isinstance(s, ast.Assign) and ast.unparse(s).startswith('dV = _add(dV, _scale(_mul(D, power('):
                    removed += 1
                else:
                    body.append(s)
            node.body = body
    assert removed == 1
    ns = dict(V.B.__dict__)
    exec(compile(ast.fix_missing_locations(tree), '<deleted_force_term>', 'exec'), ns)
    expected, mutant = CK.model(r2, M), ns['_model'](r2, M, True)
    rows.append(dict(name='dV_term_deleted', expected=expected, mutant=mutant, detected=mutant != expected))
    # Preserve the real rejected rounded-reciprocal candidate's first counterexample.
    dr = (V.REF.L.R_MIN_BOHR, Q(0), Q(0))
    one = 1 << M
    rlo, rhi = FP._radius(sum(x*x for x in dr), M)
    inv1 = ((one << M)//rhi, -((-(one << M))//rlo))
    inv = {1: inv1}
    for n in range(2,18):
        inv[n] = FP._mul(inv[n-1], inv1, M)
    ns = dict(V.B._model_R.__globals__)
    ns['_inverse_table'] = lambda lo, hi, bits: inv
    fn = types.FunctionType(V.B._model_R.__code__, ns, argdefs=V.B._model_R.__defaults__)
    fn.__kwdefaults__ = V.B._model_R.__kwdefaults__
    expected, mutant = CK.model(sum(x*x for x in dr), M), fn((rlo,rhi), M, True)
    historical = json.loads((E.HERE / 'pilot_counterexamples.json').read_bytes())[0]
    assert normalized(expected) == historical['expected'] and normalized(mutant) == historical['observed']
    rows.append(dict(name='REJECTED_rounded_reciprocal_recurrence', dr=list(map(str,dr)), expected=expected,
                     mutant=mutant, detected=mutant != expected, historical_reproduced=True))
    return normalized(rows)


def main():
    sys.set_int_max_str_digits(0)
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--stage', required=True)
    args = p.parse_args()
    out, name = args.run, args.stage
    m = json.loads((out / 'manifest.json').read_bytes())
    assert E.inventory() == m['source'] and E.sha(out / 'inputs.json') == m['input_hash']
    V.OUT = out
    checks = {}
    if name == 'primitives':
        payload = V.primitive_checks()
        checks['primitive_comparisons'] = all(v > 0 for v in payload.values())
    elif name == 'structure':
        payload = V.structural_checks()
        checks = {k: payload[k] for k in ('a_live_ast_equal', 'b_live_ast_equal_modulo_certified_inverse_table', 'impulse_ast_equal_modulo_pair_unpack')}
    elif name in ('fixed', 'high'):
        payload = fixed(name == 'high')
        E.write(out / f'{name}.endpoints.json', payload)
        checks['endpoints_equal'] = bool(payload) and all(r['equivalent'] for r in payload)
    elif name == 'dataset':
        inputs = json.loads((out / 'inputs.json').read_bytes())
        payload = dataset(inputs['impulses'] if isinstance(inputs,dict) else inputs, out / 'dataset.endpoints.jsonl')
        checks['all_input_profile_endpoint_and_raw_equal'] = payload['cases'] > 0
    elif name == 'mutations':
        payload = mutants()
        E.write(out / 'mutations.witnesses.json', payload)
        checks['every_fault_detected'] = bool(payload) and all(r['detected'] for r in payload)
    else:
        from . import integration_stages
        payload, checks = integration_stages.execute(name, out)
    E.write(out / f'{name}.json', dict(**E.binding(m), stage=name, checks=checks, payload=payload))
    assert E.inventory() == m['source']
    if not checks or any(v is not True for v in checks.values()):
        raise SystemExit(1)
    print(name, 'completed', flush=True)


if __name__ == '__main__':
    main()
