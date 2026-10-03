"""Raw-MO Slater--Condon operator from determinant ladder operations.

The vectorized ladder is a batching of the previous independent fermion
definition. No direct-pair builder/action, FCI packing, absorption, or integral
symmetry substitution is used. Both ordered electron contributions survive.
"""
import math
import numpy as np
from electronic_pilot.ci_layer_audit_v0 import fermion


def catalog(n):
    return fermion.state_catalog(n)


def expansions(states):
    occupations = np.empty((len(states), 2, 2), dtype=np.int64)
    coefficients = np.zeros((len(states), 2))
    for i, state in enumerate(states):
        terms, radical = fermion.singlet(state['pair'])
        occupations[i, :, :] = terms[0][0]
        for slot, (det, sign) in enumerate(terms):
            occupations[i, slot] = det
            coefficients[i, slot] = sign / math.sqrt(2)**radical
    return occupations, coefficients


def transition(ket, bra, operations):
    """Batched CAR action, with the same lower-occupied parity rule as fermion.

    Two storage slots hold the occupied set. Slot order has no effect on signs;
    signs count active orbitals below the operated orbital. Operations arrive
    rightmost first. A failed Pauli step keeps valid=False permanently.
    """
    shape = np.broadcast_shapes(ket.shape[:-1], bra.shape[:-1])
    occupied = np.broadcast_to(ket, shape + (2,)).copy()
    active = np.ones_like(occupied, dtype=bool)
    valid = np.ones(shape, dtype=bool)
    sign = np.ones(shape, dtype=np.int8)
    for orbital, create in operations:
        orbital = np.broadcast_to(orbital, shape)
        present = active & (occupied == orbital[..., None])
        exists = present.any(axis=-1)
        sign *= np.where((active & (occupied < orbital[..., None])).sum(axis=-1) % 2, -1, 1).astype(np.int8)
        if create:
            free = ~active
            valid &= ~exists & free.any(axis=-1)
            slot = free.argmax(axis=-1)
            chosen = np.arange(2) == slot[..., None]
            occupied = np.where(chosen, orbital[..., None], occupied)
            active |= chosen
        else:
            valid &= exists
            active &= ~present
    target = np.broadcast_to(bra, shape + (2,))
    valid &= active.all(axis=-1)
    for slot in range(2):
        valid &= ((occupied == target[..., slot, None]) & active).any(axis=-1)
    return sign, valid


def rows(h, g, states, start, stop, decomposition=False):
    """Compute independent matrix rows; no spatial pair formula or transpose fix."""
    occ, coefficients = expansions(states)
    parts = {kind: np.zeros((stop-start, len(states)))
             for kind in ('one_electron', 'Coulomb', 'exchange')}
    for bra_slot in range(2):
        bd = occ[start:stop, bra_slot, None, :]
        for ket_slot in range(2):
            kd = occ[None, :, ket_slot, :]
            norm_sign = coefficients[start:stop, bra_slot, None] * coefficients[None, :, ket_slot]
            for qi in range(2):
                q = kd[..., qi]
                for pi in range(2):
                    p = bd[..., pi]
                    sign, valid = transition(kd, bd, [(q, False), (p, True)])
                    valid &= p % 2 == q % 2
                    parts['one_electron'] += norm_sign * sign * valid * h[p//2, q//2]
                    s, r = kd[..., 1-qi], bd[..., 1-pi]
                    sign, valid = transition(kd, bd, [(q, False), (s, False), (r, True), (p, True)])
                    valid &= (p % 2 == q % 2) & (r % 2 == s % 2)
                    kind = 'Coulomb' if pi == qi else 'exchange'
                    parts[kind] += 0.5 * norm_sign * sign * valid * g[p//2, q//2, r//2, s//2]
    if decomposition:
        return parts
    return sum(parts.values())


def dense(h, g, block=32, progress=None):
    states = catalog(len(h))
    if h.shape != (len(h), len(h)) or g.shape != (len(h),)*4:
        raise ValueError('input dimensions')
    if not np.isfinite(h).all() or not np.isfinite(g).all():
        raise ValueError('nonfinite input')
    matrix = np.empty((len(states), len(states)))
    for start in range(0, len(states), block):
        stop = min(start+block, len(states))
        matrix[start:stop] = rows(h, g, states, start, stop)
        if progress is not None:
            progress(stop, len(states))
    return matrix, states


def residual(matrix, energy, vector, states):
    action = matrix @ vector
    ev = energy * vector
    delta = action-ev
    index = int(np.argmax(np.abs(delta)))
    norm2 = float(vector @ vector)
    return dict(l2=float(np.linalg.norm(delta)), linf=float(np.max(np.abs(delta))),
                maximum_index=index, maximum_state=states[index],
                H_SC_v=float(action[index]), E_v=float(ev[index]), difference=float(delta[index]),
                vector_l2=math.sqrt(norm2), vector_norm_error=abs(norm2-1),
                rayleigh_quotient=float(vector @ action / norm2)), action, delta


def action_pass(diagnostics, asymmetry, guards):
    numbers = [diagnostics['l2'], diagnostics['vector_norm_error'], asymmetry,
               diagnostics['rayleigh_quotient']]
    return bool(np.isfinite(numbers).all() and
                diagnostics['l2'] <= guards['eigen_l2_max'] and
                diagnostics['vector_norm_error'] <= guards['norm_max'] and
                asymmetry <= guards['H_asym_max'])


def eigensolve(matrix):
    """Independent full-spectrum NumPy _syevd; no vector, shift, or target input."""
    return np.linalg.eigh(matrix, UPLO='L')
