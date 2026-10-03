"""Baseline input-export adapter ONLY; never imported by independent operator."""
import time
import numpy as np
from scipy.linalg import eigh
from electronic_pilot.solver import singlet_matrix
from .io import write, npy, array_meta, sha


def extract(h, g, archived, guards, directory):
    started = time.perf_counter()
    matrix, i, j, norms = singlet_matrix(h, g)  # unchanged baseline function
    asym = float(np.max(np.abs(matrix-matrix.T)))
    if asym > guards['H_asym_max']:
        write(directory/'replay.json', dict(status='STOP', reason='baseline Hermiticity guard', asymmetry=asym))
        return None
    energies, vectors = eigh(matrix, subset_by_index=(0, 1), driver='evr')  # unchanged QZ44 call
    energy = float(energies[0])
    vector = vectors[:, 0].copy()  # no sign change, adjustment or renormalization
    residual = float(np.linalg.norm(matrix @ vector-energy*vector))
    norm_error = float(abs(vector @ vector-1))
    record = dict(provenance='REPRODUCED_FROM_SEALED_REPLAY; original QZ44 vector was not archived',
                  driver='scipy.linalg.eigh subset_by_index=(0,1), driver=evr',
                  E_direct=archived['electronic_energy_hartree'], E_replayed=energy,
                  archived_energy_hex=float(archived['electronic_energy_hartree']).hex(),
                  replayed_energy_hex=energy.hex(), energy_bitwise_equal=energy.hex() == float(archived['electronic_energy_hartree']).hex(),
                  matrix_array_sha256=__import__('hashlib').sha256(matrix.tobytes()).hexdigest(),
                  matrix_asymmetry=asym, residual_l2=residual, vector_norm_error=norm_error,
                  next_singlet_gap=float(energies[1]-energies[0]),
                  archived_next_singlet_gap=archived.get('next_singlet_gap'),
                  gap_comparison='UNAVAILABLE: QZ44 path did not record its second eigenvalue or gap',
                  seconds=time.perf_counter()-started)
    okay = bool(record['energy_bitwise_equal'] and residual <= guards['eigen_l2_max'] and
                norm_error <= guards['norm_max'] and np.isfinite(energy))
    record['status'] = 'REPLAY_INPUT_ACCEPTED' if okay else 'STOP_REPLAY_INPUT_MISMATCH'
    if okay:
        npy(directory/'v_direct_reproduced.npy', vector)
        pairs = np.column_stack((i, j))
        npy(directory/'direct_state_order.npy', pairs)
        record['vector'] = array_meta(directory/'v_direct_reproduced.npy')
        record['ordering'] = array_meta(directory/'direct_state_order.npy')
        write(directory/'vector_input_seal.json', dict(energy=energy, vector=record['vector'],
              ordering=record['ordering'], source='sealed replay; accepted before independent Hamiltonian construction'))
    write(directory/'replay.json', record)
    del matrix
    if not okay:
        return None
    loaded = np.load(directory/'v_direct_reproduced.npy', allow_pickle=False)
    if not np.array_equal(loaded.view(np.uint64), vector.view(np.uint64)):
        raise ValueError('vector save/load bit drift')
    return energy, loaded, pairs
