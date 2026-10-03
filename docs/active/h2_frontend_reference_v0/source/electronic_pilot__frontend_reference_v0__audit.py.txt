"""Decimal/reference gate audit. No AO, MO, CI, or eigensolver imports.

Manual primary-page transcription is an input, not a new independent physical
calculation. Missing pointwise uncertainty is preserved, never manufactured.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def verify(bindings, root, main):
    for key, expected in bindings.items():
        kind, relative = key.split(':', 1)
        if kind not in ('worktree', 'main'):
            raise ValueError('unsupported binding ' + key)
        path = Path(root if kind == 'worktree' else main) / relative
        if not path.is_file() or sha(path) != expected:
            raise ValueError('BYTE DRIFT ' + key)
    return len(bindings)


def parenthetical(text):
    match = re.fullmatch(r'(-?\d+\.\d+)\((\d+)\)', text)
    if not match:
        raise ValueError('expected decimal with last-digit uncertainty')
    value = Decimal(match[1])
    uncertainty = Decimal(match[2]) * Decimal(10) ** value.as_tuple().exponent
    return value, uncertainty


def transcription(primary, stored):
    energy, uncertainty = parenthetical(primary['printed_energy'])
    if energy != Decimal(primary['energy_hartree']) or uncertainty != Decimal(primary['uncertainty_hartree']):
        raise ValueError('manual printed and expanded scalar definitions disagree')
    difference = Decimal(stored['total_energy_hartree']) - energy
    uncertainty_difference = Decimal(stored['published_uncertainty_hartree']) - uncertainty
    match = (Decimal(primary['R_bohr']) == Decimal(stored['R_bohr'])
             and difference == 0 and uncertainty_difference == 0)
    return dict(status='REFERENCE_TRANSCRIPTION_MATCH_SUPPORTED' if match else
                'REFERENCE_TRANSCRIPTION_ERROR_CONFIRMED',
                primary_energy=str(energy), primary_uncertainty=str(uncertainty),
                stored_energy=stored['total_energy_hartree'],
                stored_uncertainty=stored['published_uncertainty_hartree'],
                stored_minus_primary=str(difference), uncertainty_difference=str(uncertainty_difference))


CONTRACT_KEYS = ('fixed_nuclei', 'nonrelativistic', 'BO', 'nuclear_repulsion',
                 'quantity', 'energy_zero', 'R_unit', 'energy_unit', 'R_definition',
                 'Z', 'electrons', 'spin_S', 'finite_mass', 'relativistic', 'QED')


def contract(ours, reference):
    # Never substitute an undocumented default for a missing definition.
    missing = [key for key in CONTRACT_KEYS if key not in ours or key not in reference]
    if missing:
        return dict(status='COMPARISON_CONTRACT_UNRESOLVED', missing=missing)
    mismatches = {key: [ours[key], reference[key]] for key in CONTRACT_KEYS
                  if ours[key] != reference[key]}
    return dict(status='COMPARISON_CONTRACT_MISMATCH_CONFIRMED' if mismatches else
                'PHYSICAL_QUANTITY_MATCH_SUPPORTED', differences=mismatches,
                ours_spatial_selection=ours['spatial_selection'],
                reference_spatial_selection=reference['spatial_selection'],
                identical_trial_spaces=False,
                observed_state_spatial_irrep='NOT_INDEPENDENTLY_CHECKED',
                scope='operator and total BO energy convention; not all front-end numerical fidelity')


def crosscheck(first, second):
    if first['calculation_lineage'] == second['calculation_lineage']:
        return dict(status='REFERENCE_SIDE_UNRESOLVED', reason='same calculation lineage')
    quantity = contract(first['contract'], second['contract'])
    if quantity['status'] != 'PHYSICAL_QUANTITY_MATCH_SUPPORTED' or Decimal(first['R_bohr']) != Decimal(second['R_bohr']):
        return dict(status='REFERENCE_SIDE_UNRESOLVED', reason='reference definition mismatch', contract=quantity)
    difference = Decimal(second['energy_hartree']) - Decimal(first['energy_hartree'])
    uncertainties = [first.get('uncertainty_hartree'), second.get('uncertainty_hartree')]
    available = all(source.get('reported_pointwise_uncertainty') is True
                    and source.get('uncertainty_R_bohr') is not None
                    and Decimal(source['uncertainty_R_bohr']) == Decimal(source['R_bohr'])
                    and value is not None
                    for source, value in zip((first,second), uncertainties))
    band = sum((Decimal(value) for value in uncertainties), Decimal(0)) if available else None
    if available and any(not Decimal(value).is_finite() or Decimal(value)<0 for value in uncertainties):
        raise ValueError('invalid reported uncertainty')
    within = abs(difference) <= band if available else None
    return dict(status='REFERENCE_CROSSCHECK_SUPPORTED' if within is True else 'REFERENCE_SIDE_UNRESOLVED',
                second_minus_first_hartree=str(difference),
                reported_pointwise_uncertainties=uncertainties,
                combined_reported_uncertainty_hartree=str(band) if band is not None else None,
                within_reported_uncertainty=within,
                reason='within both reported pointwise uncertainties' if within is True else
                ('outside combined reported uncertainty' if available else 'second source has no investigated/reported R=0.4 uncertainty'),
                meaningful_reference_disagreement=within is False,
                unknown_uncertainty_is_not_evidence_of_reference_error=not available)


def downstream(a, b, c):
    closed = (a['status'] == 'REFERENCE_TRANSCRIPTION_MATCH_SUPPORTED'
              and b['status'] == 'PHYSICAL_QUANTITY_MATCH_SUPPORTED'
              and c['status'] == 'REFERENCE_CROSSCHECK_SUPPORTED')
    return {name: dict(status='ELIGIBLE_NOT_EXECUTED' if closed and name == 'D' else 'NOT_EXECUTED',
                      reason='earlier stages required; no automatic launch' if closed else 'reference-side prerequisite not closed')
            for name in ('D', 'E', 'F', 'G')}


def git(*args):
    return subprocess.check_output(['git', *args], encoding='utf-8').strip()


def seal(root, main, acquisition, output):
    root, main, acquisition, output = (Path(path).resolve() for path in (root, main, acquisition, output))
    spec = read(root/'electronic_pilot/frontend_reference_v0/protocol.json')
    state = dict(branch=git('branch', '--show-current'), HEAD=git('rev-parse', 'HEAD'),
                 origin_master=git('rev-parse', 'origin/master'),
                 origin_branch=git('rev-parse', 'origin/'+spec['branch']),
                 ahead_behind=git('rev-list', '--left-right', '--count', 'HEAD...origin/'+spec['branch']),
                 dirty_tracked=git('diff', '--name-only'), untracked=git('ls-files', '--others', '--exclude-standard'))
    if (state['branch'] != spec['branch'] or state['HEAD'] != spec['base_commit'] or
        state['origin_master'] != spec['origin_master'] or state['origin_branch'] != spec['base_commit'] or state['dirty_tracked']):
        raise ValueError('Git precondition mismatch ' + repr(state))
    inherited = read(root/'docs/active/h2_ground_state_audit_v0/evidence/execution_seal.json')['bound_sha256']
    count = verify(inherited, root, main)
    bindings = dict(inherited)
    protected = git('ls-files', 'electronic_pilot', 'tests/*h2*', 'tests/h2_ground_state_audit_v0',
                    'docs/active/H2*', 'docs/active/h2*').splitlines()
    for path in protected:
        bindings['worktree:'+path] = sha(root/path)
    for folder in ('runs/h2_ground_state_audit_v0/validation_v0', 'runs/h2_ci_layer_audit_v0/audit_v0',
                   'electronic_pilot/frontend_reference_v0', 'tests/h2_frontend_reference_v0'):
        for path in sorted((root/folder).iterdir()):
            if path.is_file():
                bindings['worktree:'+path.relative_to(root).as_posix()] = sha(path)
    for path in sorted(acquisition.iterdir()):
        if path.is_file():
            bindings['worktree:'+path.relative_to(root).as_posix()] = sha(path)
    manual = root/'electronic_pilot/frontend_reference_v0/primary_transcriptions.json'
    output.mkdir(parents=True, exist_ok=False)
    write(output/'execution_seal.json', dict(spec=spec, Git=state, bound_sha256=bindings,
          inherited_bindings_checked=count, raw_acquisition=acquisition.as_posix(),
          manual_transcription_sha256=sha(manual), source_review_before_seal=True,
          AO_calls=0, MO_transform_calls=0, CI_calls=0))
    print('SEALED',len(bindings),'bindings; inherited',count,flush=True)


def run(root, main, acquisition, output):
    root, acquisition, output = map(Path, (root, acquisition, output))
    bound = read(output/'execution_seal.json')
    verify(bound['bound_sha256'], root, main)
    manual = read(root/'electronic_pilot/frontend_reference_v0/primary_transcriptions.json')
    first, second = manual['Pachucki'], manual['Sims_Hagstrom']
    # Original-page input is sealed before opening the historic CSV.
    with (root/'electronic_pilot/reference_pachucki_v2.csv').open(encoding='utf-8', newline='') as stream:
        matches = [row for row in csv.DictReader(stream) if Decimal(row['R_bohr']) == Decimal('0.4')]
    if len(matches) != 1:
        raise ValueError('stored R04 is not a singleton')
    a = transcription(first, matches[0]); write(output/'stage_A.json',a)
    if a['status'] != 'REFERENCE_TRANSCRIPTION_MATCH_SUPPORTED':
        write(output/'STOP.json',dict(reason=a['status'])); return
    # Static anchors ensure the source being manually reviewed is the bound source.
    for relative, needles in manual['local_code_anchors'].items():
        source = (root/relative).read_text(encoding='utf-8')
        if not all(needle in source for needle in needles):
            raise ValueError('physical definition source anchor drift '+relative)
    b = contract(manual['ours_contract'], first['contract']); write(output/'stage_B.json',b)
    if b['status'] != 'PHYSICAL_QUANTITY_MATCH_SUPPORTED':
        write(output/'STOP.json',dict(reason=b['status'])); return
    c = crosscheck(first,second); write(output/'stage_C.json',c)
    physical = read(root/'docs/active/h2_ground_state_audit_v0/evidence/physical_comparison.json')
    limit = Decimal(str(read(root/'electronic_pilot/protocol_v2.json')['criteria']['P3_curve_max_abs_error_hartree']))
    energy = Decimal(first['energy_hartree'])
    diff = Decimal(str(physical['direct_BO']))-energy
    cross_diff = Decimal(str(physical['direct_BO']))-Decimal(second['energy_hartree'])
    prior = dict(physical, fresh_energy_run=False, source='preceding sealed ground-state audit',
                 primary_retranscription_direct_signed_difference=str(diff),
                 second_source_direct_signed_difference=str(cross_diff),
                 original_criterion=str(limit), within_original_criterion=abs(diff)<=limit)
    write(output/'prior_energy_comparison.json',prior)
    write(output/'downstream.json',downstream(a,b,c))
    classifications = dict(REFERENCE_TRANSCRIPTION_ERROR_CONFIRMED='NOT_OBSERVED',
        COMPARISON_CONTRACT_MISMATCH_CONFIRMED='NOT_OBSERVED_FOR_OPERATOR_AND_QUANTITY; spatial selection explicitly differs',
        REFERENCE_SIDE_UNRESOLVED=c['status']=='REFERENCE_SIDE_UNRESOLVED',
        BASIS_DEFINITION_MISMATCH_CONFIRMED='NOT_TESTED', AO_INTEGRAL_MISMATCH_CONFIRMED='NOT_TESTED',
        AO_TO_MO_TRANSFORM_MISMATCH_CONFIRMED='NOT_TESTED',
        MO_REPRESENTATION_NUMERICAL_ERROR_SUPPORTED='ENERGY_CAUSATION_NOT_ESTABLISHED; inherited pair residual UNRESOLVED',
        FINITE_BASIS_LIMIT_SUPPORTED=False, UNRESOLVED=True)
    count = verify(bound['bound_sha256'], root, main)
    write(output/'preservation.json',dict(status='UNCHANGED',protected_bindings_checked=count,
                                         inherited_bindings_checked=bound['inherited_bindings_checked']))
    write(output/'summary.json',dict(classifications=classifications, AO_calls=0, MO_transform_calls=0,
          CI_calls=0, new_energy_calculations=0, prior_QZ44='NUMERICAL FAIL unchanged', not_certified=True,
          controlling_unresolved='No pointwise reported uncertainty for independent R04 reference; observed state spatial irrep also not independently checked',
          decision='DESIGNER DECISION REQUIRED', no_reference_error_confirmed=True,
          numerical_closeness_is_not_a_reported_uncertainty_gate=True))
    print(a['status'],b['status'],c['status'],'preserved',count,flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['seal','run'])
    parser.add_argument('--main',required=True);parser.add_argument('--acquisition',required=True)
    parser.add_argument('--output',required=True);args=parser.parse_args()
    (seal if args.mode=='seal' else run)(Path.cwd(),args.main,args.acquisition,args.output)
