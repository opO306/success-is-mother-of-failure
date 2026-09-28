"""C1-B1 runtime stress / failure-driven validation survey (survey_only).

Question (designer, the only verdict question of this stage): do the rounding decisions of real, valid trajectories
almost all end at 128-256 bits? The answer is a DISTRIBUTION (128 / 256 / 512 / 1024+) and where 512+ concentrates,
not just "ReferenceUndecided = 0".

Nothing here changes the executor (a_reference/c1b1_two_atom.py), any certificate, fixture or coverage, and nothing
here is a certification. The per-shell exhaustive hard-case search stopped at shell 15.

Instrumentation (designer conditions 1, 3, 8):
  * The ORIGINAL C._decide still makes every 128 -> 256 -> ... -> 16384 decision. A wrapper, installed only inside the
    process that runs trajectories and always restored (try/finally), hands C._decide a value_at(M) that records M and
    delegates the computation to the original value_at(M) unchanged. The largest M requested is the decision precision.
  * check_integrator_domain (admission E_rel <= 10 De) escalates on its own, without _decide. Its precision is observed
    the same way through C.relative_energy_enclosure and kept in a SEPARATE counter, never merged with the impulse
    rounding decisions.
  * Counters live in memory; state dumps are written only for failure candidates.
  * telemetry=False runs the plain executor (for the overhead measurement and the on/off equality check).

Statistics kept apart (designer condition 5): trajectory_precision_distribution vs
targeted_hard_case_precision_distribution (the 61,936 shell 15-18 candidates are evaluated one impulse at a time and
never enter the trajectory histogram).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from fractions import Fraction as Q
from math import isqrt
from pathlib import Path

import a_reference.c1b1_canonical_state as G
import a_reference.c1b1_dt_study as S
import a_reference.c1b1_inner_validation as I
import a_reference.c1b1_two_atom as C
from a_numeric.profiles import VMHalt

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'c1b1-stress-survey-v0'
DT = Q(40)
POS, MOM = I.POS, I.MOM                       # FX(96,48) positions, FX(96,80) momenta (the C1-B1 candidate)
RE = S.RE_GRID
HARD_CASE_FIXTURES = {
    15: 'a_reference/fixtures/c1b1_hard_case_survey_shell15_v1.json',
    16: 'a_reference/fixtures/c1b1_hard_case_survey_shell16_v1.json',
    17: 'a_reference/fixtures/c1b1_hard_case_survey_shell17_v1.json',
    18: 'a_reference/fixtures/c1b1_hard_case_survey_v1.json',
}


# ---------------------------------------------------------------------------------------------------------------------
# instrumentation
# ---------------------------------------------------------------------------------------------------------------------

class Telemetry:
    """In-memory counters. decisions: final precision M of each impulse rounding (or 'undecided' / 'halt@M');
    admission: precision at which each check_integrator_domain call settled."""

    HOT_BITS = 512                       # decisions at or above this precision are located, not only counted
    HOT_KEEP = 200                       # at most this many located records per trajectory (the count stays exact)

    def __init__(self):
        self.decisions = Counter()
        self.decide_calls = 0
        self.admission_M = []            # every M requested by relative_energy_enclosure during one admission check
        self.step = None                 # run.t_steps before the step being computed (None during admission)
        self.run = None                  # the run being stepped, read only to locate hot decisions
        self.hot = []                    # [{'M', 'step', 'raw'}] for decisions >= HOT_BITS or that failed
        self.bins = Counter()            # profile only
        self.wfinal = Counter()          # profile only: (final M, log2 of the final enclosure width in ulps)
        self.hardest = None              # profile only: the decision whose final midpoint was nearest a boundary
        self.cur_R2 = None               # profile only: R^2 of the impulse being decided
        self.comp = 0                    # profile only: decision index inside the current impulse
        self.axes = []                   # profile only: axis index of each nonzero component of the current impulse

    # --- optional per-decision profile (read-only): why does a decision need 256 bits? -------------------------
    profile = False                      # set True on an instance to fill `bins` and `hardest`
    R_BIN = Q(1, 2)                      # bohr

    def profile_decision(self, fx, comp, evals, M_final):
        """evals = [(M, lo, hi)] in the order _decide asked for them. Records, per decision: final M, component,
        separation bin, log2 of the 128-bit enclosure width in output ulps, and log2 of the distance of the final
        enclosure midpoint from the nearest rounding boundary (half-integer ulp), also in ulps."""
        scale = 1 << fx.frac_bits
        _, lo0, hi0 = evals[0]
        w0 = _flog2((hi0 - lo0) * scale)
        M, lo, hi = evals[-1]
        v = (lo + hi) / 2 * scale
        t = v - (v.numerator // v.denominator)
        d = abs(t - Q(1, 2))
        dl = _flog2(d)
        rb = None if self.cur_R2 is None else int(_sqrt_floor(self.cur_R2 / (self.R_BIN * self.R_BIN)))
        self.bins[(M_final, comp, rb, w0, max(dl, -64) if dl is not None else 'tie')] += 1
        wf = (hi - lo) * scale
        self.wfinal[(M_final, _flog2(wf))] += 1
        if self.hardest is None or d < self.hardest['d']:
            self.hardest = {'d': d, 'M_final': M_final, 'comp': comp, 'R2': self.cur_R2, 'width_final_ulps': wf,
                            'width_128_log2': w0, 'step': self.step}

    def locate(self, M):
        if len(self.hot) < self.HOT_KEEP:
            raw = None if self.run is None else [[str(x) for x in v] for v in _raw(self.run)]
            self.hot.append({'M': M, 'step': self.step, 'raw_before_step': raw})

    def admission_decided_at(self):
        return max(self.admission_M) if self.admission_M else None


@contextmanager
def instrumented(tel: Telemetry):
    """Observe the original executor; never replace its logic. Restored on every exit path."""
    orig_decide, orig_enclosure = C._decide, C.relative_energy_enclosure

    orig_impulse = C.impulse

    def decide(profile, value_at):
        top = [0]
        evals = []

        def at(M):
            top[0] = M
            r = value_at(M)               # the computation itself is the original one
            if tel.profile:
                evals.append((M, r[0], r[1]))
            return r
        tel.decide_calls += 1
        comp = tel.axes[tel.comp] if tel.profile and tel.comp < len(tel.axes) else tel.comp
        tel.comp += 1
        try:
            out = orig_decide(profile, at)
            if tel.profile:
                tel.profile_decision(profile, comp, evals, top[0])
        except C.ReferenceUndecided:
            tel.decisions['undecided'] += 1
            tel.locate('undecided')
            raise
        except VMHalt:
            tel.decisions[f'halt@{top[0]}'] += 1
            tel.locate(f'halt@{top[0]}')
            raise
        tel.decisions[top[0]] += 1
        if top[0] >= tel.HOT_BITS:
            tel.locate(top[0])
        return out

    def enclosure(run, M):
        tel.admission_M.append(M)
        return orig_enclosure(run, M)

    def impulse(dr, dt_kick, profile):
        tel.cur_R2, tel.comp = sum((x * x for x in dr), Q(0)), 0
        tel.axes = [k for k, x in enumerate(dr) if x != 0]      # the executor decides only nonzero components
        return orig_impulse(dr, dt_kick, profile)

    C._decide, C.relative_energy_enclosure = decide, enclosure
    if tel.profile:
        C.impulse = impulse
    try:
        yield tel
    finally:
        C._decide, C.relative_energy_enclosure, C.impulse = orig_decide, orig_enclosure, orig_impulse


def _flog2(x: Q):
    """floor(log2 x) for a rational x > 0, exactly; None for 0."""
    if x == 0:
        return None
    n, d = x.numerator, x.denominator
    k = n.bit_length() - d.bit_length()
    if (n << max(0, -k)) < (d << max(0, k)):
        k -= 1
    return k


def _sqrt_floor(x: Q) -> int:
    return isqrt(x.numerator // x.denominator)


# ---------------------------------------------------------------------------------------------------------------------
# failure classification (designer condition 9: ReferenceUndecided BEFORE its base class ExecutorLimitExceeded;
# an unexpected Python exception is only a bug CANDIDATE)
# ---------------------------------------------------------------------------------------------------------------------

def classify(exc: BaseException) -> str:
    if isinstance(exc, C.ReferenceUndecided):
        return 'reference_undecided'
    if isinstance(exc, C.ExecutorLimitExceeded):
        return 'executor_limit_exceeded'
    if isinstance(exc, C.IntegratorDomainExceeded):
        return 'integrator_domain_exceeded'
    if isinstance(exc, C.PhysicsDomainExceeded):
        return 'physics_domain_exceeded'
    return 'unexpected_exception'


# ---------------------------------------------------------------------------------------------------------------------
# initial states
# ---------------------------------------------------------------------------------------------------------------------

def _q(x) -> str:
    return str(Q(x))


def state_key(st: dict) -> str:
    """Hash of the STORED state (raw lattice values), used for deduplication (designer condition 7)."""
    raw = [[str(POS.from_exact(Q(x))) for x in st['r_i']], [str(MOM.from_exact(Q(x))) for x in st['p_i']],
           [str(POS.from_exact(Q(x))) for x in st['r_j']], [str(MOM.from_exact(Q(x))) for x in st['p_j']]]
    return hashlib.sha256(json.dumps(raw).encode()).hexdigest()


def spec(kind: str, label: str, st: dict, max_steps: int, transform: str | None = None) -> dict:
    return {'kind': kind, 'label': label, 'transform': transform, 'max_steps': max_steps,
            'state': {k: [_q(x) for x in st[k]] for k in ('r_i', 'p_i', 'r_j', 'p_j')}}


def _state(sp: dict) -> dict:
    return {k: tuple(Q(x) for x in v) for k, v in sp['state'].items()}


def canonical(e, b) -> dict:
    return G.canonical_initial_state(str(Q(e)), Q(b))


def grid_specs(energies, b_fracs, max_steps):
    out = []
    for e in energies:
        for f in b_fracs:
            out.append(spec('grid', f'e={e} b={f}Re', canonical(e, f * RE), max_steps))
    return out


def headon_specs(energies, max_steps):
    return [spec('headon', f'e={e} b=0', canonical(e, 0), max_steps) for e in energies]


def orbit_specs(e_fracs, rhos, max_steps):
    """b = b_orb (1 + rho) on BOTH sides of the orbiting boundary (designer condition 7)."""
    out = []
    for e in e_fracs:
        bo = I.orbiting(Q(e))[0]
        for r in rhos:
            for sign in (-1, 1):
                out.append(spec('orbit', f'e={e} rho={sign}*{r}', canonical(e, bo * (1 + sign * Q(r))), max_steps))
    return out


def dedupe(specs):
    """Keep the first spec of each STORED initial state (transforms are distinct runs and are kept)."""
    seen, out, dropped = set(), [], []
    for sp in specs:
        key = (state_key(_state(sp)), sp['transform'])
        if key in seen:
            dropped.append(sp['label'])
            continue
        seen.add(key)
        out.append(sp)
    return out, dropped


def admission_bracket(b_frac, lo=Q(999, 100), hi=Q(1001, 100), iterations=160):
    """Nearest STORED canonical states on both sides of the integrator contract E_rel <= 10 De (designer condition 6):
    bisect the nominal e, but judge each side by the real check_integrator_domain on the stored state."""
    def accepted(e):
        st = canonical(e, b_frac * RE)
        try:
            C.new_run(POS, DT, st['r_i'], st['p_i'], st['r_j'], st['p_j'], momentum_profile=MOM)
            return True, st
        except C.IntegratorDomainExceeded:
            return False, st
    ok_lo, st_lo = accepted(lo)
    ok_hi, st_hi = accepted(hi)
    if not ok_lo or ok_hi:
        raise ValueError(f'bracket does not straddle 10 De at b={b_frac}Re')
    for _ in range(iterations):
        if state_key(st_lo) != state_key(st_hi) and st_lo['p_j'] != st_hi['p_j'] and hi - lo < Q(1, 10 ** 30):
            break
        mid = (lo + hi) / 2
        ok, st = accepted(mid)
        if ok:
            lo, st_lo = mid, st
        else:
            hi, st_hi = mid, st

    def energy(st):
        run = C.new_run(POS, DT, st['r_i'], st['p_i'], st['r_j'], st['p_j'], momentum_profile=MOM,
                        validated_only=False)
        a, z = C.relative_energy_enclosure(run, 512)
        return [_q(a / C.DE_CONTRACT), _q(z / C.DE_CONTRACT)]
    return {'b_frac': _q(b_frac), 'inside': st_lo, 'outside': st_hi,
            'inside_E_over_De': energy(st_lo), 'outside_E_over_De': energy(st_hi),
            'nominal_e_gap': _q(hi - lo)}


# ---------------------------------------------------------------------------------------------------------------------
# symmetry transforms (applied to the exact initial state; the same map must carry the final raw state)
# ---------------------------------------------------------------------------------------------------------------------

def _swap_xy(v):
    return (v[1], v[0], v[2])


def _mirror_x(v):
    return (-v[0], v[1], v[2])


def transform_state(st: dict, t: str | None) -> dict:
    if t is None:
        return st
    if t == 'swap_atoms':
        return {'r_i': st['r_j'], 'p_i': st['p_j'], 'r_j': st['r_i'], 'p_j': st['p_i']}
    f = {'swap_xy': _swap_xy, 'mirror_x': _mirror_x}[t]
    return {k: f(v) for k, v in st.items()}


def transform_raw(atoms: list, t: str | None) -> list:
    """atoms = [[r_i raw], [p_i raw], [r_j raw], [p_j raw]] (raw integers on FX profiles, exact negation)."""
    if t is None:
        return atoms
    if t == 'swap_atoms':
        return [atoms[2], atoms[3], atoms[0], atoms[1]]
    f = {'swap_xy': _swap_xy, 'mirror_x': _mirror_x}[t]
    return [list(f(tuple(v))) for v in atoms]


# ---------------------------------------------------------------------------------------------------------------------
# one trajectory
# ---------------------------------------------------------------------------------------------------------------------

def _raw(run) -> list:
    i, j = run.atoms
    return [list(i.r), list(i.p), list(j.r), list(j.p)]


def _rel2(run) -> Q:
    return sum((x * x for x in C.relative(run.pos, *run.atoms)), Q(0))


def run_trajectory(sp: dict, telemetry: bool = True, trace: bool = False, profile: bool = False) -> dict:
    """Run one canonical state with the unchanged executor until it returns to its starting separation after the
    closest approach, a refusal, or max_steps. Returns counters (and the full raw-state trace if trace=True)."""
    st = transform_state(_state(sp), sp['transform'])
    tel = Telemetry()
    tel.profile = profile
    out = {'kind': sp['kind'], 'label': sp['label'], 'transform': sp['transform']}
    trace_rows = [] if trace else None
    t0 = time.perf_counter()

    def body():
        tel.admission_M.clear()
        run = C.new_run(POS, DT, st['r_i'], st['p_i'], st['r_j'], st['p_j'], momentum_profile=MOM)
        out['admission_M'] = tel.admission_decided_at() if telemetry else None
        holder[0] = run
        p0 = C.total_momentum(run)
        R2_start = prev = _rel2(run)
        stop_R = sp.get('stop_R')            # outgoing flight: run on past the start separation up to stop_R bohr
        R2_stop = R2_start if stop_R is None else Q(stop_R) ** 2
        passed_min = False
        if trace:
            trace_rows.append(_raw(run))
        out['end'] = 'step_cap'
        tel.run = run
        while run.t_steps < sp['max_steps']:
            tel.step = run.t_steps
            C.step(run)
            if trace:
                trace_rows.append(_raw(run))
            R2 = _rel2(run)
            if R2 > prev:
                passed_min = True
            prev = R2
            if passed_min and R2 >= R2_stop:
                out['end'] = 'returned_to_start' if stop_R is None else 'reached_stop_R'
                break
        out['steps'] = run.t_steps
        out['final_raw'] = [[str(x) for x in v] for v in _raw(run)]
        if C.total_momentum(run) != p0:
            out['end'] = 'invariant_violation'
            out['invariant'] = 'total momentum not exactly conserved'
        return run

    holder = [None]
    try:
        if telemetry:
            with instrumented(tel):
                body()
        else:
            body()
    except Exception as exc:          # noqa: BLE001 -- every refusal and every unexpected exception is recorded
        run = holder[0]
        out['end'] = classify(exc)
        out['exception'] = f'{type(exc).__name__}: {exc}'
        out['repro'] = {'initial_state': sp['state'], 'transform': sp['transform'],
                        'failed_after_steps': None if run is None else run.t_steps,
                        'state_at_failure': None if run is None else [[str(x) for x in v] for v in _raw(run)]}
    out['wall_seconds'] = time.perf_counter() - t0
    # D_valid of the initial state, evaluated OUTSIDE the instrumentation: it calls relative_energy_enclosure itself
    # and must not leak into the admission or decision counters.
    out['d_valid'] = None if holder[0] is None else holder[0].validation.get('validation_status')
    out['decide_calls'] = tel.decide_calls
    out['decisions'] = {str(k): v for k, v in sorted(tel.decisions.items(), key=lambda kv: str(kv[0]))}
    out['hot'] = tel.hot
    if profile:
        out['profile'] = profile_dump(tel)
    if trace:
        out['trace'] = [[[str(x) for x in v] for v in row] for row in trace_rows]
    return out


def profile_dump(tel: Telemetry) -> dict:
    h = tel.hardest
    return {'bins': [[list(k), v] for k, v in sorted(tel.bins.items(), key=str)],
            'wfinal': [[list(k), v] for k, v in sorted(tel.wfinal.items(), key=str)],
            'hardest': None if h is None else {**h, 'd': str(h['d']), 'd_log2': _flog2(h['d']),
                                               'R2': None if h['R2'] is None else str(h['R2']),
                                               'width_final_ulps': str(h['width_final_ulps']),
                                               'width_final_log2': _flog2(h['width_final_ulps'])}}


def _job(args):
    sp, telemetry = args
    return run_trajectory(sp, telemetry=telemetry)


# ---------------------------------------------------------------------------------------------------------------------
# targeted hard-case points (kept apart from trajectories)
# ---------------------------------------------------------------------------------------------------------------------

def hard_case_points(shells=(15, 16, 17, 18)):
    """(shell, n) for every candidate lattice point of the shell surveys (relative position n / 2^48 bohr on +x)."""
    out = []
    for s in shells:
        run = json.loads((ROOT/HARD_CASE_FIXTURES[s]).read_text(encoding='utf-8'))['full_run']
        for a, b in run['candidate_intervals']:
            out.extend((s, n) for n in range(int(a), int(b) + 1))
    return out


def _point_job(args):
    shell, n = args
    tel = Telemetry()
    rec = {'shell': shell, 'n': str(n)}
    try:
        with instrumented(tel):
            C.impulse((Q(n, 1 << 48), Q(0), Q(0)), DT / 2, MOM)
        rec['end'] = 'decided'
    except Exception as exc:          # noqa: BLE001
        rec['end'] = classify(exc)
        rec['exception'] = f'{type(exc).__name__}: {exc}'
    rec['decisions'] = {str(k): v for k, v in tel.decisions.items()}
    return rec


# ---------------------------------------------------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------------------------------------------------

def precision_distribution(records):
    total = Counter()
    by_kind = {}
    for r in records:
        for k, v in r.get('decisions', {}).items():
            total[k] += v
            by_kind.setdefault(r.get('kind', r.get('shell')), Counter())[k] += v
    n = sum(total.values())
    return {'decisions': n, 'by_precision': dict(sorted(total.items(), key=lambda kv: kv[0])),
            'fraction': {k: v / n for k, v in total.items()} if n else {},
            'by_kind': {str(k): dict(v) for k, v in by_kind.items()}}


def run_batch(specs, workers: int, telemetry: bool = True):
    t0 = time.perf_counter()
    if workers <= 1:
        out = [run_trajectory(sp, telemetry=telemetry) for sp in specs]
    else:
        with ProcessPoolExecutor(workers) as pool:
            out = list(pool.map(_job, [(sp, telemetry) for sp in specs], chunksize=1))
    return out, time.perf_counter() - t0


def summarize(records):
    ends = Counter(r['end'] for r in records)
    failures = [r for r in records if r['end'] not in ('returned_to_start', 'step_cap')]
    return {'trajectories': len(records), 'steps': sum(r.get('steps', 0) for r in records),
            'decide_calls': sum(r['decide_calls'] for r in records), 'ends': dict(ends),
            'admission_precision': dict(Counter(str(r.get('admission_M')) for r in records)),
            'failure_candidates': failures,
            'steps_distribution': sorted(r.get('steps', 0) for r in records),
            'wall_seconds_distribution': sorted(r['wall_seconds'] for r in records)}
