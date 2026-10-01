"""Exact audit transport, normal-input equivalence, and fail-closed mutations."""
import ast
import importlib.util
import json
import sys
from fractions import Fraction as Q
from pathlib import Path

import pytest
from a_numeric import FixedPoint
from a_numeric.profiles import VMHalt
from a_reference import c1b1_two_atom as C
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_source_binding as S


@pytest.fixture(scope='module')
def old():
    name = '_c1b1_pre_classification_test_only'
    spec = importlib.util.spec_from_file_location(name, S.HISTORY/'a_reference/c1b1_two_atom.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(name, None)


def outcome(call):
    try:
        return ('return', call())
    except Exception as e:
        return ('raise', type(e).__name__, str(e), getattr(e, 'reason', None))


@pytest.mark.parametrize('case', ['finite', 'tie', 'refine', 'positive_overflow', 'negative_overflow', 'opposite_overflow', 'precision'])
def test_decide_normal_contract_has_identical_result_and_schedule(old, monkeypatch, case):
    monkeypatch.setattr(C, 'MAX_PRECISION_BITS', 256)
    monkeypatch.setattr(old, 'MAX_PRECISION_BITS', 256)
    p = FixedPoint(8, 4)
    def interval(m):
        return {
            'finite': (Q(1, 16), Q(1, 16)), 'tie': (Q(1, 32), Q(1, 32)),
            'refine': (Q(1, 32)-Q(1, m), Q(1, 32)+Q(1, m)) if m == 128 else (Q(1, 16), Q(1, 16)),
            'positive_overflow': (Q(9), Q(10)), 'negative_overflow': (Q(-10), Q(-9)),
            'opposite_overflow': (Q(-10), Q(10)) if m == 128 else (Q(0), Q(0)),
            'precision': (Q(0), Q(1)),
        }[case]
    def run(module):
        schedule = []
        def at(m):
            schedule.append(m)
            return interval(m)
        return outcome(lambda: module._decide(p, at)), schedule
    assert run(C) == run(old)


def test_all_tiny_profile_rounding_cells_and_ties_match(old):
    p = FixedPoint(8, 4)
    for numerator in range(-258, 257):
        x = Q(numerator, 32)
        assert outcome(lambda: C._decide(p, lambda m: (x, x))) == outcome(lambda: old._decide(p, lambda m: (x, x)))


def test_limit_normal_and_overflow_are_identical(old):
    p = FixedPoint(8, 4)
    for x in (Q(0), Q(1, 32), Q(-8), Q(8)):
        assert outcome(lambda: C._limit(p.from_exact, x)) == outcome(lambda: old._limit(p.from_exact, x))


def test_legal_stored_state_transition_and_guard_are_identical(old):
    def snapshot(run):
        return tuple((a.species, a.r, a.p) for a in run.atoms), run.J_cache, run.t_steps
    for radius, momentum in ((20, 1), (20, -1), (20, 0)):
        radius = Q(radius)
        runs = [m.new_run(FixedPoint(96,48), 40, (-radius/2,0,0), (-momentum,0,0),
                (radius/2,0,0), (momentum,0,0), momentum_profile=FixedPoint(96,80), validated_only=False)
                for m in (C, old)]
        # radius/2 above remains exact for Fraction inputs.
        for _ in range(3):
            result = [outcome(lambda m=m, r=r: m.step(r)) for m,r in zip((C,old), runs)]
            assert result[0] == result[1] and snapshot(runs[0]) == snapshot(runs[1])
            if result[0][0] == 'raise': break


def test_entire_audited_source_transports_and_original_hashes_remain():
    for name, expected in S.BASELINES.items():
        assert S.source_matches(S.ROOT/name, expected)
    assert A._SOURCE_HASHES[C] == S.BASELINES['a_reference/c1b1_two_atom.py']
    assert K.FOUNDATION_HASHES['a_reference/c1b1_two_atom.py'] == A._SOURCE_HASHES[C]
    A.proof_guard(); K.foundation_guard()


@pytest.mark.parametrize('fault', ['mul', 'rounding', 'cap', 'kick', 'drift', 'guard', 'raw_check'])
def test_unaudited_source_mutations_are_rejected_even_with_replaced_new_hash(monkeypatch, fault):
    name = 'a_reference/c1b1_two_atom.py'
    data = (S.ROOT/name).read_text(encoding='utf-8')
    replacements = {
        'mul': ('return min(p) >> M', 'return (min(p) + 1) >> M'),
        'rounding': ('return a\n        M *= 2', 'return a + 1\n        M *= 2'),
        'cap': ('MAX_PRECISION_BITS = 1 << 14', 'MAX_PRECISION_BITS = 1 << 15'),
        'kick': ('p - q', 'p + q'),
        'drift': ('p * dt / m', 'p * dt * m'),
        'guard': ('if lo > hi:', 'if lo >= hi:'),
        'raw_check': ('not all(valid(v) for v in raws)', 'not any(valid(v) for v in raws)'),
    }
    before, after = replacements[fault]
    assert before in data
    mutated = data.replace(before, after, 1).encode()
    monkeypatch.setattr(S, 'EXECUTOR_HASH', S.digest(mutated))
    monkeypatch.setitem(S.CURRENT_VARIANTS, name, S.variant_hash(name, mutated))
    assert not S.equivalent_source(name, (S.HISTORY/name).read_bytes(), mutated, S.digest(Path(S.__file__).read_bytes()))


def test_historical_source_tamper_and_unrecognized_path_are_rejected():
    name = 'a_reference/c1b1_two_atom.py'
    assert not S.equivalent_source(name, (S.HISTORY/name).read_bytes()+b'\n# tamper\n',
                                 (S.ROOT/name).read_bytes(), S.digest(Path(S.__file__).read_bytes()))
    assert not S.source_matches(S.ROOT/name, '0'*64)


def test_redacted_guard_literal_still_requires_the_exact_auditor_hash():
    name = 'a_reference/c1b1_axis_decision_bounds.py'
    current = (S.ROOT/name).read_bytes()
    actual = S.digest(Path(S.__file__).read_bytes())
    mutant = current.replace(actual.encode(), b'0'*64, 1)
    assert S.variant_hash(name, current) == S.variant_hash(name, mutant)
    assert not S.equivalent_source(name, (S.HISTORY/name).read_bytes(), mutant, actual)


def test_live_auditor_replacement_is_refused(monkeypatch):
    monkeypatch.setattr(S, 'equivalent_source', lambda *args: True)
    with pytest.raises(Exception, match='source-binding auditor changed'):
        A.proof_guard()


def test_live_auditor_constant_mutation_is_refused(monkeypatch):
    monkeypatch.setattr(S, 'EXECUTOR_HASH', '0'*64)
    with pytest.raises(Exception, match='source-binding auditor changed'):
        K.foundation_guard()


@pytest.mark.parametrize('name', tuple(S.METADATA_EDITS))
def test_provenance_transport_cannot_admit_a_numerical_body_edit(name, monkeypatch):
    tree = ast.parse((S.ROOT/name).read_bytes())
    operation = next(n for n in ast.walk(tree) if isinstance(n, ast.BinOp))
    operation.op = ast.Sub() if not isinstance(operation.op, ast.Sub) else ast.Add()
    mutant = ast.unparse(tree).encode()
    monkeypatch.setitem(S.CURRENT_VARIANTS, name, S.variant_hash(name, mutant))
    assert not S.equivalent_source(name, (S.HISTORY/name).read_bytes(), mutant,
                                   S.digest(Path(S.__file__).read_bytes()))


def test_recombined_receipt_binds_fresh_artifacts_and_exact_payloads():
    from tools.c1b1_source_binding_reaudit import mathematical_payload, payload_hash
    receipt = json.loads((S.ROOT/'a_reference/fixtures/c1b1_source_binding_reaudit_v1.json').read_bytes())
    assert len(receipt['regenerated']) == 11
    assert receipt['new_normal_input_premises'] == []
    assert receipt['new_certified_region_count'] == 0 and not receipt['A_EV_closed']
    for path, h in receipt['source_sha256'].items():
        assert S.digest((S.ROOT/path).read_bytes()) == h
    for row in receipt['regenerated']:
        old = json.loads((S.HISTORY/row['historical_path']).read_bytes())
        path = S.ROOT/row['current_path']
        fresh = json.loads(path.read_bytes())
        assert S.digest(path.read_bytes()) == row['new_artifact_sha256']
        assert mathematical_payload(old, row['kind']) == mathematical_payload(fresh, row['kind'])
        assert payload_hash(mathematical_payload(fresh, row['kind'])) == row['mathematical_payload_sha256']
    original = 'a_reference/fixtures/c1b1_half_ulp_boundaries_v1.json'
    assert S.digest((S.ROOT/original).read_bytes()) == S.digest((S.HISTORY/original).read_bytes())
