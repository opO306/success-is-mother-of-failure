"""Only three sealed arbitrary-R calls into the unchanged V5Z numerical path."""
import argparse
import math
import resource
import time
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from electronic_pilot.frontend_reference_v0.audit import read, write, sha
from electronic_pilot.h2_force_v0.interface import BASIS, MODE, GUARDS, refusal
from electronic_pilot.ao_micro_v0.reuse import canonical_ao, transform
from electronic_pilot.numerical_cause.core import coordinates
from .scalar import geometry


def run(label, protocol_path, output):
    from pyscf import gto, lib
    protocol = read(protocol_path)
    if sha(protocol_path) != read(Path(protocol_path).with_name('protocol_seal.json'))['sha256']:
        raise ValueError('protocol changed')
    for path, expected in protocol['implementation_sha256'].items():
        if sha(path) != expected:
            raise ValueError('source/input changed: '+path)
    requested = protocol['initial_state']['requested_geometries'][label]
    g = geometry(requested)
    lib.num_threads(1)
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=False)
    spec = read(protocol['basis_definitions'])['records'][BASIS]
    guard = read('electronic_pilot/ao_micro_v0/protocol.json')['guards']
    if guard != GUARDS:
        raise ValueError('historical guard mismatch')
    start = time.perf_counter()
    row = dict(label=label, requested_R=requested, R_bohr=g['actual_serialized_R'], geometry=g,
        basis=BASIS, mode=MODE, guards=guard, arithmetic='IEEE binary64', driver='evr',
        energy_convention='EBO=Ee+1/R', accepted=False, failure_stage=None, total_energy_hartree=None)
    try:
        mol = gto.M(atom=[('H', xyz) for xyz in g['positions_bohr']], unit='Bohr',
                    basis={'H':spec['raw_PySCF_H_basis']}, spin=0, charge=0,
                    cart=False, symmetry=False, verbose=0)
        row['actual_stored_positions_bohr'] = mol.atom_coords(unit='Bohr').tolist()
        if row['actual_stored_positions_bohr'] != g['positions_bohr']:
            raise ValueError('molecule coordinate serialization changed')
        s, h, g8 = canonical_ao(mol)
        ev = eigh(s, eigvals_only=True)
        np.save(dest/'overlap_spectrum.npy', ev, allow_pickle=False)
        row.update(basis_size=len(s), Smin=float(ev[0]), condition=float(ev[-1]/ev[0]))
        if ev[0] <= guard['Smin_floor']:
            row['failure_stage'] = 'overlap_floor'
        else:
            c = coordinates(s, h, 'cholesky')
            orth = float(np.linalg.norm(c.T@s@c-np.eye(len(s)), ord=2))
            row['orthogonality_l2'] = orth
            if orth > guard['orth_l2_max']:
                row['failure_stage'] = 'orthonormalization'
            else:
                final, c = transform(mol, s, h, g8, MODE, guard, solve=True)
                row.update(final)
                np.savez(dest/'AO_C.npz', s=s, h=h, c=c, positions=mol.atom_coords(unit='Bohr'))
        reason = refusal(row)
        if reason:
            row.update(accepted=False, failure_stage=row['failure_stage'] or reason,
                       total_energy_hartree=None, electronic_energy_hartree=None)
    except Exception as exc:
        row.update(accepted=False, failure_stage='calculator_exception', exception=repr(exc),
                   total_energy_hartree=None, electronic_energy_hartree=None)
    row.update(runtime_seconds=time.perf_counter()-start,
               peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               numerical_guard_status='ACCEPTED' if row['accepted'] else 'REFUSED',
               norm_measure='abs(v.T @ v - 1)', not_certified=True, diagnostic_only=True)
    nonfinite={k:repr(v) for k,v in row.items() if isinstance(v,float) and not math.isfinite(v)}
    for key in nonfinite: row[key]=None
    if nonfinite: row['nonfinite_diagnostics']=nonfinite
    write(dest/'result.json', row)
    print(label, row['numerical_guard_status'], row['total_energy_hartree'], flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--label',choices=('left','center','right'),required=True)
    p.add_argument('--protocol',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    run(a.label,a.protocol,a.output)
