"""C1-B1 runtime local witness PROTOTYPE (survey_only): stop -> record -> re-decide one impulse -> verify -> resume.

What this prototype tests: whether the structure "the executor refuses a step it cannot decide, the refused impulse
alone is re-decided and checked, and the same step is re-run with that checked value" gives, step by step, exactly
the raw states of the plain executor. The refusal is FORCED by lowering the executor's precision cap to 128 bits for
the stepping attempt; the re-decision uses the full contract schedule (128 ... 16384). Nothing raises the cap above
16384: a decision the full schedule cannot close stays refused (NotWitnessed).

What it is not:
  * not a solution for a real 16384-bit failure (that would need a different proof, e.g. exact rational tie
    exclusion; out of scope by designer decision 2026-09-29);
  * not an independent physics check: the witness and its checker both use the executor's own evaluator
    (C._model). A witness is an "executor rounding-decision re-verification witness" -- it shows the rounding of
    the executor's enclosure is closed, given that the evaluator's enclosures are valid;
  * not a certification: witnesses live in runs/ only, never in fixtures, and change no coverage/D_valid/④ status.

The executor (c1b1_two_atom) is unchanged. As in the stress survey, its module functions are wrapped only inside a
context and always restored: C.impulse is wrapped to see the refused input and, when resuming, to hand back a
VERIFIED witness value for exactly that input (the executor computes the input itself; the witness is keyed by it).
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from fractions import Fraction as Q
from pathlib import Path

import a_reference.ar2_lang2024 as L
import a_reference.c1b1_two_atom as C
from a_numeric.profiles import VMHalt

VERSION = 'c1b1-runtime-local-witness-v0'
KIND = 'executor_rounding_decision_witness'
ROOT = Path(__file__).resolve().parents[1]
FULL_START, FULL_CAP = C.START_PRECISION_BITS, C.MAX_PRECISION_BITS      # the contract schedule, fixed at import
SOURCES = ('a_reference/c1b1_two_atom.py', 'a_reference/ar2_lang2024.py')


class NotWitnessed(Exception):
    """The full schedule did not close the decision, or a witness failed verification. The step stays refused."""


def schedule(start=FULL_START, cap=FULL_CAP):
    out, M = [], start
    while M <= cap:
        out.append(M)
        M *= 2
    return out


def _lf_sha256(rel):
    return hashlib.sha256((ROOT / rel).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def _profile_id(p):
    return {'name': p.name, 'width': p.width, 'frac_bits': p.frac_bits}


def binding(run) -> dict:
    """Everything a witness depends on. A witness whose binding differs from the current one is stale."""
    return {'model_fingerprint': L.parameter_fingerprint(), 'frozen_c1a_fingerprint': C.FROZEN_C1A_FINGERPRINT,
            'sources_lf_sha256': {s: _lf_sha256(s) for s in SOURCES},
            'position_profile': _profile_id(run.pos), 'momentum_profile': _profile_id(run.mom),
            'dt': str(run.dt), 'dt_kick': str(run.dt / 2), 'drift': run.drift,
            'retardation': L.WORLD_RETARDATION, 'rounding': 'half_even',
            'precision_schedule': schedule()}


@contextmanager
def precision_cap(bits):
    old = C.MAX_PRECISION_BITS
    C.MAX_PRECISION_BITS = bits
    try:
        yield
    finally:
        C.MAX_PRECISION_BITS = old


# ---------------------------------------------------------------------------------------------------------------------
# builder: re-decide one impulse on the executor's own path at the full schedule, recording its enclosures
# ---------------------------------------------------------------------------------------------------------------------

def build_witness(dr, run, cap=FULL_CAP) -> dict:
    """Re-run the executor's impulse for input dr with the precision cap at `cap` (never above FULL_CAP) and record,
    per nonzero component, the enclosure at the precision where its two ends rounded alike."""
    if cap > FULL_CAP:
        raise NotWitnessed(f'cap {cap} above the contract cap {FULL_CAP}')
    dr = tuple(Q(x) for x in dr)
    comps, current = [], []
    orig = C._decide

    def decide(profile, value_at):
        seen = []

        def at(M):
            r = value_at(M)
            seen.append((M, r[0], r[1]))
            return r
        raw = orig(profile, at)
        current.append((seen[-1], raw))
        return raw
    C._decide = decide
    try:
        with precision_cap(cap):
            J = C.impulse(dr, run.dt / 2, run.mom)
    except (C.ReferenceUndecided, VMHalt) as exc:
        raise NotWitnessed(f'{type(exc).__name__}: {exc}') from exc
    finally:
        C._decide = orig
    it = iter(current)
    for k, x in enumerate(dr):
        if x == 0:
            comps.append({'axis': k, 'zero_input': True, 'raw': 0})
            continue
        (M, lo, hi), raw = next(it)
        comps.append({'axis': k, 'bits': M, 'lo': str(lo), 'hi': str(hi), 'raw': raw})
    return {'version': VERSION, 'kind': KIND, 'binding': binding(run), 'input': {'dr': [str(x) for x in dr]},
            'components': comps, 'impulse_raw': list(J)}


# ---------------------------------------------------------------------------------------------------------------------
# checker: a separate code path from the builder (it never calls C.impulse or C._decide)
# ---------------------------------------------------------------------------------------------------------------------

def _enclosure(dr, dt_kick, k, M):
    R2 = sum((x * x for x in dr), Q(0))
    _, dV, inv1 = C._model(R2, M, L.WORLD_RETARDATION)
    lo, hi = C._mul(C._neg(dV), inv1, M)
    c = dr[k] * dt_kick
    a, b = Q(lo, 1 << M) * c, Q(hi, 1 << M) * c
    return min(a, b), max(a, b)


def verify_witness(w: dict, run) -> tuple:
    """Return the witnessed impulse (raw tuple) or raise NotWitnessed. Trusts nothing in `w` but the input it binds."""
    if w.get('version') != VERSION or w.get('kind') != KIND:
        raise NotWitnessed('unknown witness version or kind')
    if w.get('binding') != binding(run):
        raise NotWitnessed('stale binding (model, sources, profiles, dt, retardation, drift or schedule differ)')
    dr = tuple(Q(x) for x in w['input']['dr'])
    if len(dr) != 3 or sum((x * x for x in dr), Q(0)) < C.R_MIN2:
        raise NotWitnessed('input outside the executor domain')
    if [c['axis'] for c in w['components']] != [0, 1, 2]:
        raise NotWitnessed('components must be axes 0, 1, 2 in order')
    dt_kick, sched = run.dt / 2, schedule()
    out = []
    for c in w['components']:
        k = c['axis']
        if dr[k] == 0:
            if not c.get('zero_input') or c['raw'] != 0:
                raise NotWitnessed(f'axis {k}: zero input must give raw 0')
            out.append(0)
            continue
        if c.get('zero_input'):
            raise NotWitnessed(f'axis {k}: input is not zero')
        M = c['bits']
        if M not in sched:
            raise NotWitnessed(f'axis {k}: precision {M} not in the contract schedule')
        lo, hi = _enclosure(dr, dt_kick, k, M)
        if (str(lo), str(hi)) != (c['lo'], c['hi']):
            raise NotWitnessed(f'axis {k}: enclosure does not recompute')
        try:
            a, b = run.mom.from_exact(lo), run.mom.from_exact(hi)
        except VMHalt as exc:
            raise NotWitnessed(f'axis {k}: endpoint outside the momentum range') from exc
        if not (a == b == c['raw']):
            raise NotWitnessed(f'axis {k}: enclosure ends do not both round to the claimed raw')
        out.append(a)
    if out != list(w['impulse_raw']):
        raise NotWitnessed('impulse_raw differs from the component decisions')
    return tuple(out)


# ---------------------------------------------------------------------------------------------------------------------
# runner: step at a low cap; on a refusal re-decide that impulse, verify, and re-run the same step
# ---------------------------------------------------------------------------------------------------------------------

def _key(dr, dt_kick, mom):
    return (tuple(Q(x) for x in dr), Q(dt_kick), mom.name)


@contextmanager
def _executor_hooks(verified: dict, seen: list):
    """Wrap C.impulse: remember every input it is asked for; hand back a VERIFIED witness value for exactly that
    input (else compute as usual). Restored on every exit path."""
    orig = C.impulse

    def impulse(dr, dt_kick, profile):
        seen.append((tuple(dr), dt_kick, profile))
        hit = verified.get(_key(dr, dt_kick, profile))
        if hit is not None:
            return hit
        return orig(dr, dt_kick, profile)
    C.impulse = impulse
    try:
        yield
    finally:
        C.impulse = orig


def _raw(run):
    i, j = run.atoms
    return [list(i.r), list(i.p), list(j.r), list(j.p)]


def run_with_local_witnesses(run, n_steps, exec_cap=128, use_witnesses=True):
    """Step `run` n_steps times with the executor capped at exec_cap. Returns (per-step raw states, witnesses,
    refusal log). use_witnesses=False is the DEFECT switch for the tests (resume without a witness)."""
    states, witnesses, refusals, verified = [_raw(run)], [], [], {}
    while run.t_steps < n_steps:
        before, seen = dict(vars(run)), []
        try:
            with precision_cap(exec_cap), _executor_hooks(verified if use_witnesses else {}, seen):
                C.step(run)
            states.append(_raw(run))
            continue
        except C.ReferenceUndecided:
            pass
        if dict(vars(run)) != before:
            raise AssertionError('fail-closed violated: a refused step changed the run')
        dr, dt_kick, mom = seen[-1]                       # the impulse call that raised
        key = _key(dr, dt_kick, mom)
        if key in verified:
            raise AssertionError('refused again on an input that already has a verified witness')
        w = build_witness(dr, run)
        verified[key] = verify_witness(json.loads(json.dumps(w)), run)   # verify the stored form, not the object
        witnesses.append(w)
        refusals.append({'step_index': run.t_steps, 'input': w['input']['dr'],
                         'axes_above_exec_cap': [c['axis'] for c in w['components']
                                                 if not c.get('zero_input') and c['bits'] > exec_cap]})
    return states, witnesses, refusals


CASES = ((Q(9), Q(1, 2), 1640), (Q(1, 2), Q(1, 2), 5775), (Q(1, 10), Q(2), 21056))   # whole trajectories


def main(out_dir):
    """Demo for runs/: whole trajectories (to their return to R = 20), every step compared with the plain run."""
    import time
    from a_reference import c1b1_stress_survey as X
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    reports = []
    for e, bf, n in CASES:
        st = X.canonical(e, bf * X.RE)
        mk = lambda: C.new_run(X.POS, X.DT, st['r_i'], st['p_i'], st['r_j'], st['p_j'], momentum_profile=X.MOM)
        t0 = time.perf_counter()
        ref, tel = mk(), X.Telemetry()
        ref_states = [_raw(ref)]
        with X.instrumented(tel):
            for _ in range(n):
                C.step(ref)
                ref_states.append(_raw(ref))
        t_ref = time.perf_counter() - t0
        t0 = time.perf_counter()
        states, witnesses, refusals = run_with_local_witnesses(mk(), n)
        t_wit = time.perf_counter() - t0
        tag = f'e={e}_b={bf}Re'.replace('/', '_')
        rep = {'version': VERSION, 'state': f'e={e} De b={bf} Re', 'steps': n, 'exec_cap': 128,
               'plain_decisions': {str(k): v for k, v in sorted(tel.decisions.items())},
               'refusals': len(refusals), 'witnesses': len(witnesses),
               'components_above_exec_cap': sum(len(r['axes_above_exec_cap']) for r in refusals),
               'every_step_raw_equal': states == ref_states,
               'wall_seconds': {'plain': t_ref, 'witness_run': t_wit}}
        (out / f'witnesses_{tag}.json').write_text(json.dumps(witnesses, indent=1) + '\n', encoding='utf-8')
        (out / f'refusals_{tag}.json').write_text(json.dumps(refusals, indent=1) + '\n', encoding='utf-8')
        reports.append(rep)
        print(json.dumps(rep), flush=True)
    (out / 'report.json').write_text(json.dumps(reports, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    import sys
    main(sys.argv[1])
