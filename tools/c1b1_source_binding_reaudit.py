"""Regenerate only the exception-classification source-binding dependencies.

Run: python -m tools.c1b1_source_binding_reaudit
No historical proof is edited. A differing mathematical payload is a STOP.
"""
import json
from pathlib import Path
from a_reference import c1b1_source_binding as S
from a_reference import c1b1_outer_chain as O
from a_reference import c1b1_rounding_completeness as D
from a_reference import c1b1_rounding_diagnosis as T
from a_reference import c1b1_rounding_regions as R
from a_reference import c1b1_half_ulp_boundaries as H
from a_reference import c1b1_family_certificates as F
from a_reference import c1b1_axis_decision_bounds as A
from a_reference import c1b1_family_checker as K
from a_reference import c1b1_fractional_phase_survey as P
from a_reference import c1b1_modular_distance_survey as M
from a_reference import c1b1_residue_class_survey as V
from a_reference import c1b1_quotient_gap_survey as Q
from a_reference import c1b1_same_input_filter as I

PROVENANCE = {
    'outer_bootstrap_example': ('source_sha256',),
    'rounding_decision_examples': ('source_sha256',),
    'rounding_diagnosis': ('source_sha256',),
    'rounding_regions': ('source_sha256', 'diagnosis_sha256'),
    'half_ulp_boundaries': ('source_sha256', 'prior_fixture_sha256'),
    'family_certificates': ('source_sha256',),
    'fractional_phase_survey': ('source_sha256',),
    'modular_distance_survey': ('source_sha256',),
    'residue_class_survey': ('source_sha256',),
    'quotient_gap_survey': ('source_sha256',),
    'same_input_survey': ('source_sha256',),
}
REBOUND = ('rounding_regions', 'half_ulp_boundaries', 'family_certificates',
           'fractional_phase_survey', 'modular_distance_survey', 'residue_class_survey',
           'quotient_gap_survey', 'same_input_survey')


def mathematical_payload(report, kind):
    """Ignore only named top-level provenance, never bounds/certificates/results."""
    return {k: v for k, v in report.items() if k not in PROVENANCE[kind]}


def payload_hash(value):
    return S.digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def regenerate():
    A.proof_guard(); K.foundation_guard()
    history_manifest = json.loads((S.HISTORY/'manifest.json').read_bytes())
    for name, info in history_manifest['files'].items():
        if S.digest((S.HISTORY/name).read_bytes()) != info['sha256']:
            raise RuntimeError('STOP: historical original altered: '+name)
    plan = (
        ('outer_bootstrap_example', O.example_report),
        ('rounding_decision_examples', D.example_report),
        ('rounding_diagnosis', T.example_report),
        ('rounding_regions', R.example_report),
        ('half_ulp_boundaries', H.example_report),
        ('fractional_phase_survey', P.example_report),
        ('family_certificates', F.example_report),
        ('modular_distance_survey', M.example_report),
        ('residue_class_survey', V.example_report),
        ('quotient_gap_survey', Q.example_report),
        ('same_input_survey', I.example_report),
    )
    rows = []
    for kind, generator in plan:
        name = f'a_reference/fixtures/c1b1_{kind}_v1.json'
        original = json.loads((S.HISTORY/name).read_bytes())
        generated = generator()
        # Preserve the existing lossless wire schema of the class inventory.
        wire = V.packed_report(generated) if kind == 'residue_class_survey' else T.serial(generated)
        fresh = json.loads(json.dumps(wire))
        before, after = mathematical_payload(original, kind), mathematical_payload(fresh, kind)
        if before != after:
            raise RuntimeError('STOP: mathematical payload changed: '+name)
        # Replay the actual checkers, beyond equality of serialized payloads.
        if kind == 'rounding_regions':
            for c in (generated['finite_acceptance'], *generated['analytic_and_singleton_certificates']):
                R.verify_region(c)
        if kind == 'half_ulp_boundaries':
            for group in generated['groups']:
                c = group['certificate']
                if c['status'] == 'certified': H.verify_certificate(c, c['domain'])
        if kind == 'family_certificates':
            for group in generated['groups']: K.verify_certificate(group['certificate'], group['expected_domain'])
        destination = name if kind not in REBOUND else f'a_reference/fixtures/c1b1_{kind}_rebound_v1.json'
        data = (json.dumps(fresh, indent=2)+'\n').encode()
        (S.ROOT/destination).write_bytes(data)
        rows.append({'kind': kind, 'historical_path': name, 'current_path': destination,
                     'old_artifact_sha256': history_manifest['files'][name]['sha256'],
                     'new_artifact_sha256': S.digest(data),
                     'mathematical_payload_sha256': payload_hash(after),
                     'mathematical_payload_identical': True,
                     'provenance': {k: fresh[k] for k in PROVENANCE[kind]},
                     'generator': generator.__module__+'.'+generator.__name__})
        print(kind+': regenerated, mathematical payload identical, checkers accepted', flush=True)
    # Preserve all hash-pinned parent inventories. Rebound records do not become
    # new parent domains and do not trigger propagation to new proofs/surveys.
    for kind in REBOUND:
        original = f'a_reference/fixtures/c1b1_{kind}_v1.json'
        if S.digest((S.ROOT/original).read_bytes()) != history_manifest['files'][original]['sha256']:
            raise RuntimeError('STOP: original obligation inventory changed: '+original)
    sources = (*S.BASELINES, 'a_reference/c1b1_source_binding.py',
               'a_numeric/profiles.py', 'a_numeric/exp.py', 'a_reference/ar2_lang2024.py',
               'tools/c1b1_source_binding_reaudit.py')
    receipt = {'version': 'c1b1-source-binding-reaudit-v1',
               'scope': 'exception classification only; no new mathematical bounds or coverage',
               'old_origin_commit': history_manifest['origin_commit'],
               'classification_commit': 'bdc9bfe7c5c763c2900121e4d8f2bcdcf56782e8',
               'source_sha256': {name: S.digest((S.ROOT/name).read_bytes()) for name in sources},
               'source_ast_transport': {name: S.source_matches(S.ROOT/name, expected) for name, expected in S.BASELINES.items()},
               'original_foundation_sha256': K.FOUNDATION_HASHES,
               'endpoint_math_bodies_unchanged': True,
               'premises': ['ordered finite Fraction enclosure', 'canonical FixedPoint profile',
                            'legal stored raw state and legal cached impulse',
                            'existing domain/overflow/precision schedule unchanged'],
               'new_normal_input_premises': [],
               'regenerated': rows, 'original_half_ulp_inventory_unchanged': True,
               'all_original_parent_inventories_unchanged': True,
               'new_certified_region_count': 0, 'A_EV_closed': False,
               'LOCAL_FULL': 'separate test evidence required; not inferred by this receipt'}
    if not all(receipt['source_ast_transport'].values()):
        raise RuntimeError('STOP: source transport failed')
    output = S.ROOT/'a_reference/fixtures/c1b1_source_binding_reaudit_v1.json'
    output.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    regenerate()
