"""Production execution selection. Proof, audit and historical REF stay separate.

Generation 1's guarded Pilot 3 ABCD path is the runtime default. Reference,
Candidate B and Combined remain explicitly callable; there is
no automatic fallback, retry, cap change, or module-global monkey-patching.
"""
from . import c1b1_two_atom as reference, c1b1_fast_impulse as fast

new_run = reference.new_run
DEFAULT_MODE = 'fast_pilot3'


def select(mode=DEFAULT_MODE):
    if mode == 'fast':
        return fast.impulse, fast.step_fast
    if mode == 'reference':
        return reference.impulse, reference.step
    if mode == 'fast_combined':
        from . import c1b1_combined_arithmetic as combined
        return fast.impulse, combined.step
    if mode == 'fast_pilot3':
        from . import c1b1_pilot3_impulse as pilot3
        return pilot3.impulse, pilot3.step
    raise ValueError("runtime mode must be 'fast', 'reference', 'fast_combined' or 'fast_pilot3'")


def impulse(dr, dt_kick, profile, *, mode=DEFAULT_MODE):
    return select(mode)[0](dr, dt_kick, profile)


def step(run, *, mode=DEFAULT_MODE):
    return select(mode)[1](run)


class BoundRuntime:
    """Uniform run-bound entry for preserved reference and Candidate B modes."""
    def __init__(self,run,function):
        self.run=run
        self.function=function

    def step(self):
        return self.function(self.run)


def bind(run, *, mode=DEFAULT_MODE):
    _,function=select(mode)
    if mode == 'fast_combined':
        from .c1b1_combined_arithmetic import CombinedRuntime
        return CombinedRuntime(run)
    if mode == 'fast_pilot3':
        from .c1b1_pilot3_impulse import Runtime
        return Runtime(run,'ABCD')
    return BoundRuntime(run,function)
