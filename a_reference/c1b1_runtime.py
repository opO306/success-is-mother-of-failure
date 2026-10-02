"""Production execution selection. Proof, audit and historical REF stay separate.

FAST is the runtime default. Explicit reference mode remains callable; there is
no automatic fallback, retry, cap change, or module-global monkey-patching.
"""
from . import c1b1_two_atom as reference, c1b1_fast_impulse as fast

new_run = reference.new_run


def select(mode='fast'):
    if mode == 'fast':
        return fast.impulse, fast.step_fast
    if mode == 'reference':
        return reference.impulse, reference.step
    raise ValueError("runtime mode must be 'fast' or 'reference'")


def impulse(dr, dt_kick, profile, *, mode='fast'):
    return select(mode)[0](dr, dt_kick, profile)


def step(run, *, mode='fast'):
    return select(mode)[1](run)
