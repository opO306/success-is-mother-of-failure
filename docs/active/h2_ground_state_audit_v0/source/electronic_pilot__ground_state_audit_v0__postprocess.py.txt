"""Separate AFTER-A/B comparison and byte preservation; no CI evaluator."""
import argparse
import csv
from decimal import Decimal
from pathlib import Path
import numpy as np
from .io import sha, read, write, verify


def package(directory, main, destination):
    root, directory, destination = Path.cwd(), Path(directory), Path(destination)
    seal = read(directory/'execution_seal.json')
    count = verify(seal['bound_sha256'], root, main)
    a, b = read(directory/'stage_A.json'), read(directory/'stage_B.json')
    if a['classification'] != 'GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED' or b.get('status') != 'EXECUTED':
        raise ValueError('A/B not ended; no reference read')
    reference = root/'electronic_pilot/reference_pachucki_v2.csv'
    protocol = root/'electronic_pilot/protocol_v2.json'
    write(directory/'postcomparison_seal.json', dict(input_sha256={
        'Stage_A': sha(directory/'stage_A.json'), 'Stage_B': sha(directory/'stage_B.json'),
        'reference': sha(reference), 'protocol': sha(protocol), 'postprocess': sha(__file__)},
        after_stage_A_and_B=True, reference_not_used_in_CI=True))
    criteria = read(protocol)['criteria']
    limit = Decimal(str(criteria['P3_curve_max_abs_error_hartree']))
    with reference.open(encoding='utf-8', newline='') as stream:
        matches = [x for x in csv.DictReader(stream) if Decimal(x['R_bohr']) == Decimal('0.4')]
    if len(matches) != 1:
        raise ValueError('reference singleton coverage')
    ref = matches[0]
    ref_bo = Decimal(ref['total_energy_hartree'])
    nn = seal['archived_direct']['nuclear_repulsion_hartree']
    direct_bo = seal['archived_direct']['total_energy_hartree']
    independent_bo = float(b['E_independent']+nn)
    direct_error = Decimal(str(direct_bo))-ref_bo
    independent_error = Decimal(str(independent_bo))-ref_bo
    write(directory/'physical_comparison.json', dict(R_bohr=0.4, nuclear_repulsion_hartree=nn,
        direct_BO=direct_bo, independent_BO=independent_bo, Pachucki_BO=str(ref_bo),
        published_uncertainty_hartree=ref['published_uncertainty_hartree'],
        direct_signed_difference=str(direct_error), independent_signed_difference=str(independent_error),
        original_criterion=str(limit), direct_within_criterion=abs(direct_error)<=limit,
        independent_within_criterion=abs(independent_error)<=limit,
        classification='PHYSICAL_COMPARISON_FAIL_AT_R04; cause UNRESOLVED; prior QZ44 NUMERICAL FAIL unchanged',
        no_basis_cause_inference=True, performed_only_after_AB=True))
    prior_path=root/'docs/active/h2_ci_layer_audit_v0/evidence/counterexample.json'
    prior=read(prior_path)
    matrix=np.load(directory/'H_SC.npy',mmap_mode='r',allow_pickle=False)
    basis=read(directory/'basis_mapping.json')['rows']
    lookup={tuple(x['pair']):x['canonical_index'] for x in basis}
    fresh=float(matrix[lookup[tuple(prior['bra'])],lookup[tuple(prior['ket'])]])
    write(directory/'regression_preservation.json',dict(source=str(prior_path.relative_to(root)),
        source_sha256=sha(prior_path), immutable_prior_values={k:prior[k] for k in ['bra','ket','existing_direct_pair','independent_SC','prior_action','absolute_difference']},
        new_batch_SC_value=fresh, new_minus_frozen_SC=fresh-prior['independent_SC'],
        prior_counterexample_not_overwritten=True, old_invalid_action_not_repaired=True))
    write(directory/'preservation.json',dict(status='UNCHANGED', protected_bindings_checked=count,
        preceding_inherited_bindings=seal['inherited_bindings_checked'], original_source_and_raw_evidence_unchanged=True))
    destination.mkdir(parents=True,exist_ok=False)
    evidence=destination/'evidence';evidence.mkdir()
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name!='H_SC.npy':
            (evidence/path.name).write_bytes(path.read_bytes())
    manifest={p.name:dict(sha256=sha(p),bytes=p.stat().st_size,
              committed_as_compact_evidence=p.name!='H_SC.npy') for p in sorted(directory.iterdir()) if p.is_file()}
    write(evidence/'raw_manifest.json',dict(source=str(directory), files=manifest,
        raw_matrix_retained_outside_git=True, saved_MO_inputs_retained_in_preceding_raw_audit=True))
    source=destination/'source';source.mkdir()
    source_paths=sorted((root/'electronic_pilot/ground_state_audit_v0').glob('*.py'))
    source_paths+=sorted((root/'electronic_pilot/ground_state_audit_v0').glob('*.json'))
    source_paths+=[root/'electronic_pilot/ground_state_audit_v0/DERIVATION.md']
    source_paths+=sorted((root/'tests/h2_ground_state_audit_v0').glob('*.py'))
    for path in source_paths:
        name=path.relative_to(root).as_posix().replace('/','__')+'.txt'
        (source/name).write_bytes(path.read_bytes())
    print('POSTCOMPARISON after A/B; preserved',count,'bindings; compact evidence packaged',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',required=True)
    parser.add_argument('--main',required=True)
    parser.add_argument('--destination',required=True)
    args=parser.parse_args()
    package(args.directory,args.main,args.destination)
