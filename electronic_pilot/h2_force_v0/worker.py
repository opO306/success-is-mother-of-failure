"""Fresh point using the unchanged V5Z cardinal calculator and guards."""
import argparse
import math
import resource
import time
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from electronic_pilot.frontend_reference_v0.audit import read, write, sha
from electronic_pilot.ao_micro_v0.reuse import canonical_ao, transform
from electronic_pilot.numerical_cause.core import coordinates
from .interface import GRID, BASIS, MODE, GUARDS, refusal


def run(r_decimal, output, definitions):
    from pyscf import gto, lib
    if r_decimal not in GRID:
        raise ValueError('unsealed geometry')
    lib.num_threads(1)
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=False)
    spec = read(definitions)['records'][BASIS]
    guard = read('electronic_pilot/ao_micro_v0/protocol.json')['guards']
    if guard != GUARDS:
        raise ValueError('historical guard mismatch')
    start = time.perf_counter()
    r = float(r_decimal)
    row = dict(R_decimal=r_decimal, R_bohr=r, basis=BASIS, mode=MODE, guards=guard,
               arithmetic='IEEE binary64', driver='evr', energy_convention='EBO=Ee+1/R',
               accepted=False, failure_stage=None, total_energy_hartree=None)
    try:
        mol = gto.M(atom=[('H', (0, 0, -r/2)), ('H', (0, 0, r/2))], unit='Bohr',
                    basis={'H': spec['raw_PySCF_H_basis']}, spin=0, charge=0,
                    cart=False, symmetry=False, verbose=0)
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
                np.savez(dest/'AO_C.npz', s=s, h=h, c=c)
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
    # Preserve nonfinite diagnostics explicitly while keeping JSON standard.
    nonfinite = {k: repr(v) for k, v in row.items() if isinstance(v, float) and not math.isfinite(v)}
    for key in nonfinite:
        row[key] = None
    if nonfinite:
        row['nonfinite_diagnostics'] = nonfinite
    write(dest/'result.json', row)
    print(r_decimal, row['numerical_guard_status'], row['total_energy_hartree'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--R', required=True, choices=GRID)
    parser.add_argument('--output', required=True)
    parser.add_argument('--definitions', required=True)
    args = parser.parse_args()
    run(args.R, args.output, args.definitions)
