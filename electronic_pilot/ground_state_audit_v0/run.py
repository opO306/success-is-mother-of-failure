"""Stage A then conditional Stage B; no physical reference data read here."""
import argparse
import hashlib
import time
import traceback
from pathlib import Path
import numpy as np
from . import operator
from .io import read, write, npy, array_meta, sha, verify, runtime, binding_path


def mapping(vector, order, states):
    identities = [tuple(map(int, row)) for row in order]
    wanted = [tuple(state['pair']) for state in states]
    if len(vector) != len(wanted) or len(set(identities)) != len(wanted) or set(identities) != set(wanted):
        raise ValueError('state coverage mismatch')
    lookup = {identity: index for index, identity in enumerate(identities)}
    permutation = [lookup[state] for state in wanted]
    result = vector[permutation].copy()
    rows = [dict(canonical_index=k, direct_index=permutation[k], **state) for k, state in enumerate(states)]
    return result, dict(status='MATCH', dimensions=len(states), duplicate_missing_extra=0,
                        identity_permutation=permutation == list(range(len(states))), rows=rows)


def validate(matrix, states, energy, vector, guards, band, solver=operator.eigensolve):
    asymmetry = float(np.max(np.abs(matrix-matrix.T)))
    a, action, delta = operator.residual(matrix, energy, vector, states)
    a.update(hamiltonian_asymmetry=asymmetry, guards=guards)
    a['classification'] = ('GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED'
                           if operator.action_pass(a, asymmetry, guards) else 'GROUND_STATE_ACTION_MISMATCH')
    if a['classification'] != 'GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED':
        return a, None, action, delta, None
    started = time.perf_counter()
    energies, vectors = solver(matrix)  # no original E or v passed
    seconds = time.perf_counter()-started
    independent_energy, independent_vector = float(energies[0]), vectors[:, 0]
    b, independent_action, independent_delta = operator.residual(matrix, independent_energy, independent_vector, states)
    gap = float(energies[1]-energies[0])
    dot = float(abs(vector @ independent_vector))
    normalized_overlap = dot / (float(np.linalg.norm(vector))*float(np.linalg.norm(independent_vector)))
    dimension = int(np.count_nonzero(abs(energies-independent_energy) <= band))
    subspace_overlap = float(np.linalg.norm(vectors[:, :dimension].T @ vector)/np.linalg.norm(vector))
    difference = float(abs(independent_energy-energy))
    passed = operator.action_pass(b, asymmetry, guards) and difference <= band
    b.update(E_direct=energy, E_independent=independent_energy, absolute_difference=difference,
             energy_agreement_max=band, direct_independent_action_residual_l2=a['l2'],
             next_singlet_gap=gap, lowest_cluster_dimension_at_existing_band=dimension,
             overlap_absolute=dot, normalized_overlap=normalized_overlap,
             subspace_overlap=subspace_overlap, eigensolve_seconds=seconds,
             eigenvalues_returned=len(energies), driver='numpy.linalg.eigh UPLO=L, full spectrum _syevd',
             hint_vector_used=False, shift_or_energy_target_used=False,
             classification='INDEPENDENT_GROUND_STATE_ENERGY_SUPPORTED' if passed else 'INDEPENDENT_EIGENSOLVE_MISMATCH')
    return a, b, action, delta, (energies, independent_vector, independent_action, independent_delta)


def failure_trace(h, g, matrix, states, vector, stage_a):
    from electronic_pilot.ci_layer_audit_v0 import fermion
    index = stage_a['maximum_index']
    contributions = matrix[index]*vector
    order = np.argsort(-abs(contributions), kind='stable')
    terms = [dict(input_index=int(j), state=states[j], vector_value=float(vector[j]),
                  matrix_value=float(matrix[index, j]), contribution=float(contributions[j])) for j in range(len(states))]
    biggest = [dict(**terms[j], independent_fermion_terms=fermion.breakdown(h, g, states[index]['pair'], states[j]['pair']))
               for j in order[:12]]
    return dict(output_state=states[index], output_index=index, stage_a=stage_a,
                all_input_contributions=terms, largest_absolute_contributions=biggest,
                no_stage_b=True, no_repair=True)


def execute(directory, main):
    import resource
    from .replay import extract  # baseline adapter only; independent operator has no import of it
    root = Path.cwd()
    directory = Path(directory)
    seal = read(directory/'execution_seal.json')
    spec, guards = seal['spec'], seal['guards']
    started, cpu = time.perf_counter(), time.process_time()
    critical = {k: v for k, v in seal['bound_sha256'].items()
                if '/ground_state_audit_v0/' in k or k.endswith(('solver.py', 'fermion.py', '/h.npy', '/g.npy', '/R_0.4.json'))}
    verify(critical, root, main)
    write(directory/'runtime.json', runtime())
    h_path = root/'runs/h2_ci_layer_audit_v0/audit_v0/h.npy'
    g_path = root/'runs/h2_ci_layer_audit_v0/audit_v0/g.npy'
    write(directory/'MO_input.json', dict(h=array_meta(h_path), g=array_meta(g_path), source='unchanged preceding audit saved MO'))
    h, g = np.load(h_path, allow_pickle=False), np.load(g_path, allow_pickle=False)
    replay = extract(h, g, seal['archived_direct'], guards, directory)
    if replay is None:
        write(directory/'stage_B.json', dict(status='NOT_EXECUTED', reason='replay input failed'))
        write(directory/'summary.json', dict(classification='UNRESOLVED', failure_stage='replay input', designer_decision_required=True, not_certified=True))
        return
    energy, vector, order = replay
    states = operator.catalog(len(h))
    canonical, basis = mapping(vector, order, states)
    write(directory/'basis_mapping.json', basis)
    npy(directory/'v_direct_canonical.npy', canonical)
    sealed_vector = array_meta(directory/'v_direct_canonical.npy')
    write(directory/'canonical_vector_seal.json', dict(vector=sealed_vector, basis_mapping_sha256=sha(directory/'basis_mapping.json'),
          input_seal_sha256=sha(directory/'vector_input_seal.json'), no_vector_adjustment=True))
    print('REPLAY INPUT ACCEPTED; energy bitwise equality; vector sealed', flush=True)
    assembly = time.perf_counter()
    last_update = assembly
    def progress(done, total):
        nonlocal last_update
        now = time.perf_counter()
        if now-last_update >= 15 or done == total:
            print('independent SC rows', done, '/', total, flush=True)
            last_update = now
    matrix, independently_enumerated_states = operator.dense(h, g, progress=progress)
    assembly_seconds = time.perf_counter()-assembly
    if independently_enumerated_states != states:
        raise ValueError('catalog drift')
    npy(directory/'H_SC.npy', matrix)
    # A is persisted before the first permitted independent eigen call.
    asymmetry = float(np.max(np.abs(matrix-matrix.T)))
    a, action, delta = operator.residual(matrix, energy, canonical, states)
    a.update(hamiltonian_asymmetry=asymmetry, guards=guards, assembly_seconds=assembly_seconds,
             matrix_array_sha256=hashlib.sha256(matrix.tobytes()).hexdigest(),
             canonical_vector=sealed_vector)
    a['classification'] = ('GROUND_STATE_ACTION_EQUIVALENCE_SUPPORTED'
                           if operator.action_pass(a, asymmetry, guards) else 'GROUND_STATE_ACTION_MISMATCH')
    npy(directory/'H_SC_v_direct.npy', action)
    npy(directory/'stage_A_residual.npy', delta)
    write(directory/'stage_A.json', a)
    print('STAGE A', a['classification'], 'L2', a['l2'], flush=True)
    if a['classification'] == 'GROUND_STATE_ACTION_MISMATCH':
        write(directory/'counterexample_ground_state.json', failure_trace(h, g, matrix, states, canonical, a))
        write(directory/'stage_B.json', dict(status='NOT_EXECUTED', reason='Stage A mismatch; mandatory STOP'))
        classification = a['classification']
    else:
        # No eigen hint enters validate/its solver call; all original-input use is comparison only.
        checked_a, b, _, _, independent = validate(matrix, states, energy, canonical, guards, seal['energy_agreement'])
        if checked_a['classification'] != a['classification']:
            raise ValueError('A gate drift')
        b['status'] = 'EXECUTED'
        b['matrix_sha256'] = sha(directory/'H_SC.npy')
        b['canonical_input_unchanged_after_solve'] = array_meta(directory/'v_direct_canonical.npy') == sealed_vector
        energies, independent_vector, independent_action, independent_delta = independent
        npy(directory/'E_independent_all.npy', energies)
        npy(directory/'v_independent.npy', independent_vector)
        npy(directory/'stage_B_residual.npy', independent_delta)
        b['independent_vector'] = array_meta(directory/'v_independent.npy')
        b['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        write(directory/'stage_B.json', b)
        classification = b['classification']
        print('STAGE B', classification, 'E', b['E_independent'], 'difference', b['absolute_difference'], flush=True)
    verify(critical, root, main)
    write(directory/'summary.json', dict(classification=classification, R_bohr=spec['R_bohr'],
          stage_A=a['classification'], wall_seconds=time.perf_counter()-started,
          cpu_seconds=time.process_time()-cpu, peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
          scope='replay export plus independent full CI action/conditional eigensolve; same saved MO; 1 valid approach',
          critical_bindings_checked=len(critical), not_certified=True, designer_decision_required=True,
          unresolved=['AO precision', 'AO-to-MO transformation', 'MO accuracy including pair interchange', 'finite-basis physical accuracy'],
          QZ44_gate='NUMERICAL FAIL unchanged', stop=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--main', required=True)
    args = parser.parse_args()
    try:
        execute(args.directory, args.main)
    except Exception as exc:
        write(Path(args.directory)/'execution_error.json', dict(status='IMPLEMENTATION_ERROR_PRESERVED',
              error=repr(exc), traceback=traceback.format_exc(), no_automatic_retry=True))
        raise
