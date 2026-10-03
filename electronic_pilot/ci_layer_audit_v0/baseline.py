"""Reference/export adapter only; deliberately outside independent evaluator.

Calls the unchanged original and prior direct-pair builders on a small union
of orbital labels solely to extract entries. This is not a reduced CI solve.
The original formulas have no sums over unused orbitals, so each extracted
entry uses identical input values and arithmetic as the full builder.
"""
import numpy as np


def catalog(n, lower=False):
    rows, cols = np.tril_indices(n) if lower else np.triu_indices(n)
    return [dict(index=k, pair=sorted((int(i), int(j))),
                 occupation=[[p, (int(i), int(j)).count(p)] for p in sorted(set((int(i), int(j))))],
                 S=0, Ms=0, normalization='closed_unit' if i == j else 'open_1_over_sqrt2')
            for k, (i, j) in enumerate(zip(rows, cols))]


def entries(h, g, requested, prior=False):
    if prior:
        from electronic_pilot.failure_cause_v0.same_basis import direct_pair_matrix
    else:
        from electronic_pilot.solver import singlet_matrix
    orbitals = sorted({x for bra, ket in requested for x in (*bra, *ket)})
    hs = h[np.ix_(orbitals, orbitals)]
    gs = g[np.ix_(orbitals, orbitals, orbitals, orbitals)]
    if prior:
        matrix = direct_pair_matrix(hs, gs)
        metadata = catalog(len(orbitals), lower=True)
    else:
        matrix = singlet_matrix(hs, gs)[0]
        metadata = catalog(len(orbitals))
    positions = {tuple(orbitals[x] for x in row['pair']): row['index'] for row in metadata}
    return [float(matrix[positions[tuple(bra)], positions[tuple(ket)]]) for bra, ket in requested]


def column(h, g, ket, states):
    # Each union has at most four orbitals; never builds the full matrix.
    return np.array([entries(h, g, [(bra, ket)])[0] for bra in states])


class PriorAction:
    def __init__(self, h, g):
        from pyscf import ao2mo, fci, lib
        from .fermion import alpha_beta_terms
        lib.num_threads(1)
        self.n = len(h)
        self.fci = fci
        self.mapping = alpha_beta_terms
        self.k4 = fci.direct_spin1.absorb_h1e(h, g, self.n, (1, 1), fac=.5)
        self.k = ao2mo.restore(1, self.k4, self.n)
        self.link = fci.cistring.gen_linkstr_index_trilidx(range(self.n), 1)

    def __call__(self, entries, states):
        ci = np.zeros((self.n, self.n))
        for pair, weight in entries:
            for a, b, coefficient in self.mapping(pair):
                ci[a, b] += weight*coefficient
        out = self.fci.direct_spin1.contract_2e(self.k4, ci, self.n, (1, 1),
                                               link_index=(self.link, self.link))
        return np.array([sum(coefficient*float(out[a,b]) for a,b,coefficient in self.mapping(pair)) for pair in states])


def uncompressed_absorption(h, g):
    """Diagnostic intermediate immediately before installed absorb_h1e packing."""
    trace = np.einsum('jiik->jk', g)
    f = (h - .5*trace)/2
    k = g.copy()
    for p in range(len(h)):
        k[p,p,:,:] += f
        k[:,:,p,p] += f
    k *= .5
    return k, trace, f
