"""C3a component tests (plan section 6, tests 1-12). Kept outside tests/ (designer decision (c): not part of LOCAL FULL).

Run on Linux with g++:  python -m pytest c1b1_native/tests -q     (needs C1B1_LANG_PES; never skips).
Starts are dot-plan dev-panel inputs (G1, B2), not T7 inputs.
"""
import ast
import json
import random
import subprocess
import time
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mm
import pytest

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'c1b1_native'


# ----------------------------------------------------------------- helpers
def _pes():
    from c1b1_t7.lang import pes_path
    if not pes_path().exists():
        pytest.fail(f'Lang PES file not found at {pes_path()}; this test must not be skipped')


@pytest.fixture(scope='module')
def exe():
    from c1b1_native.build import build
    return build('-O2')


class Proc:
    def __init__(self, path):
        self.p = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

    def __call__(self, line):
        self.p.stdin.write(line + '\n')
        self.p.stdin.flush()
        return self.p.stdout.readline().split()

    def close(self):
        self.p.stdin.write('quit\n')
        self.p.stdin.flush()
        self.p.wait(timeout=10)


def h(x):
    return format(int(x), 'x')


def starts():
    from c1b1_t7.lang import reference_potential
    from c1b1_t7.state import canonical_raw
    V = reference_potential()
    fx = json.loads((ROOT / 'a_reference/fixtures/c1b1_orbit_boundary_v3.json').read_bytes())
    b_orb = {Q(r['e']): Q(r['b_orb']) for r in fx['energies']}[Q('1/5')]
    b2 = b_orb * (1 + Q('-1e-7'))
    return {'G1': canonical_raw('1/5', Q(4) ** 2, V), 'B2': canonical_raw('1/5', b2 * b2, V)}


_STARTS = {}


def start(name):
    if not _STARTS:
        _STARTS.update(starts())
    return _STARTS[name]


def make(cls, name, j, method='chin', extra=0, fpfm=None):
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import grid
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative
    fp, fm = fpfm or grid(j)
    with mm.workdps(DPS):
        q0, p0 = relative(start(name))
        mu = mm.mpf(MU.numerator) / MU.denominator
        return cls(LangForceFX2(), q0, p0, j, method, fp + extra, fm + extra, mu, 40, MU)


def snap(t):
    from c1b1_method_bench.ladder2 import DPS
    with mm.workdps(DPS):
        return dict(qr=list(t.qr), pr=list(t.pr_), tick=t.tick, exit_tick=t.exit_tick, substeps=t.substeps,
                    turns=t.turns, state=t.state())


@pytest.fixture(scope='module')
def native(exe):
    from c1b1_native import track
    track.configure(exe)
    yield track
    track.close_all()


# ----------------------------------------------------------------- 1. arithmetic against Python integers
def test_arithmetic_matches_python(exe):
    rnd = random.Random(20261012)
    P = Proc(exe)

    def num(bits):
        x = rnd.getrandbits(bits) | (1 << (bits - 1)) if bits else 0
        return -x if rnd.random() < 0.5 else x
    special = [0, 1, -1, 2 ** 64 - 1, 2 ** 64, -(2 ** 64), 2 ** 128 - 1, 2 ** 127, -(2 ** 191 + 5)]
    cases = 0
    try:
        for _ in range(1500):
            a, b = num(rnd.randint(0, 850)), num(rnd.randint(0, 850))
            if rnd.random() < 0.1:
                a, b = rnd.choice(special), rnd.choice(special)
            assert int(P(f'calc add {h(a)} {h(b)}')[1], 16) == a + b
            assert int(P(f'calc sub {h(a)} {h(b)}')[1], 16) == a - b
            assert int(P(f'calc mul {h(a)} {h(b)}')[1], 16) == a * b
            A, B = num(rnd.randint(1, 1700)), num(rnd.randint(1, 1700))
            if rnd.random() < 0.3:
                B = num(rnd.randint(1, 70))
            if B:
                r = P(f'calc divmod {h(A)} {h(B)}')
                assert (int(r[1], 16), int(r[2], 16)) == divmod(A, B), (A, B)
            s = rnd.randint(0, 600)
            assert int(P(f'calc shl {h(a)} {s}')[1], 16) == a << s
            assert int(P(f'calc shr {h(A)} {s}')[1], 16) == A >> s
            n = abs(A)
            from math import isqrt
            assert int(P(f'calc isqrt {h(n)}')[1], 16) == isqrt(n)
            den = abs(num(rnd.randint(1, 200))) or 1
            qq = num(rnd.randint(0, 300))
            for nm in (qq * den + den // 2, qq * den + (den + 1) // 2, A):   # exact halves when den is even
                from c1b1_method_bench.fixedpoint import _half_even
                assert int(P(f'calc halfeven {h(nm)} {h(den)}')[1], 16) == _half_even(nm, den), (nm, den)
            cases += 1
    finally:
        P.close()
    assert cases == 1500


# ----------------------------------------------------------------- 2. exp against mpmath
def exp_cases(exe, inject_path=None):
    rnd = random.Random(7)
    P = Proc(inject_path or exe)
    worst = 0
    try:
        for p in (300, 365):
            with mm.workprec(p + 192):
                ln2q = int(mm.floor(mm.ln2 * mm.mpf(2) ** (p + 64)))
            xs = [0, 1, 2 ** p, 3 * 2 ** (p - 1)] + [rnd.randint(0, 160 * 2 ** p) for _ in range(150)] + \
                 [rnd.randint(0, 2 ** (p - 20)) for _ in range(30)]
            for X in xs:
                got = int(P(f'calc expneg {h(X)} {p} {h(ln2q)}')[1], 16)
                with mm.workprec(p + 256):
                    want = int(mm.floor(mm.exp(-mm.mpf(X) / mm.mpf(2) ** p) * mm.mpf(2) ** p))
                worst = max(worst, abs(got - want))
    finally:
        P.close()
    return worst


def test_exp_within_two_units(exe):
    assert exp_cases(exe) <= 2


# ----------------------------------------------------------------- 3. jet values against the mpmath jet
@pytest.mark.parametrize('dps', [60, 68, 77, 80])
def test_jet_matches_mpmath(native, dps):
    _pes()
    from c1b1_t7.lang import LangForce
    from c1b1_native.track import init_line
    from c1b1_t7.lang_fx2 import EXTRA_BITS
    t = make(native.NativeTrack, 'G1', 0)
    ref = LangForce()
    try:
        with mm.workdps(dps):
            W = mm.mp.prec
        t._apply(t._cmd(init_line(t.pot, t.fp, t.fm, t.j, 'chin', 40, t.qr, t.pr_, t.mu_x, t.mu, W=W)))
        Pbits = W + EXTRA_BITS
        for k in range(41):
            r = mm.mpf(3) * (mm.mpf(10) ** (mm.mpf(k) / 40))
            with mm.workdps(dps + 80):
                R = int(mm.floor(r * mm.mpf(2) ** Pbits))
                rr = mm.mpf(R) / mm.mpf(2) ** Pbits
            got = t.jet_raw(R)
            with mm.workdps(dps + 60):
                want = ref.jet(rr)
                for g, w in zip(got, want):
                    assert abs(mm.mpf(g) / mm.mpf(2) ** Pbits - w) <= mm.ldexp(max(1, abs(w)), -(W - 5)), (k, dps)
    finally:
        t.close()


# ----------------------------------------------------------------- 4. track bit identity with the Python one-shot track
@pytest.mark.parametrize('j', [0, 1])
def test_track_200_ticks_identical(native, j):
    _pes()
    from c1b1_native.reference import PyOneTrack
    a, b = make(PyOneTrack, 'G1', j), make(native.NativeTrack, 'G1', j)
    try:
        a.run_to(200)
        b.run_to(200)
        assert snap(a) == snap(b)
    finally:
        b.close()


@pytest.fixture(scope='module')
def b2_python():
    _pes()
    from c1b1_native.reference import PyOneTrack
    a = make(PyOneTrack, 'B2', 0)
    a.run_to_exit(300_000)
    return snap(a)


def test_track_full_exit_with_turns_identical(native, b2_python):
    b = make(native.NativeTrack, 'B2', 0)
    try:
        b.run_to_exit(300_000)
        got = snap(b)
    finally:
        b.close()
    assert b2_python['turns'] >= 1, 'this input must exercise the turn count'
    assert got == b2_python


# ----------------------------------------------------------------- 5. exit test and its refusal band
def test_exit_check(exe):
    P = Proc(exe)
    try:
        fp = 104
        T = 20 << fp
        assert P(f'calc exitcheck {h(T)} 0 1 0 {fp}')[0] == 'err'             # r exactly 20: refuse
        assert P(f'calc exitcheck {h(T)} {h(1000)} 1 0 {fp}')[0] == 'err'     # inside the 2^-190 band
        assert P(f'calc exitcheck {h(T)} {h(2 ** 20)} 1 0 {fp}') == ['ok', '1']
        assert P(f'calc exitcheck {h(T)} {h(2 ** 20)} -1 0 {fp}') == ['ok', '0']
        assert P(f'calc exitcheck {h(T - 2 ** 60)} 0 1 0 {fp}') == ['ok', '0']
        a, b = T + 2 ** 70, 3 * 2 ** 100                                      # momentum perpendicular: refuse
        assert P(f'calc exitcheck {h(a)} {h(b)} {h(-b)} {h(a)} {fp}')[0] == 'err'
        rnd = random.Random(3)
        for _ in range(300):                                                   # agrees with the 60-digit mpf test
            q = [rnd.randint(-(25 << 64), 25 << 64), rnd.randint(-(25 << 64), 25 << 64)]
            p = [rnd.randint(-2 ** 90, 2 ** 90), rnd.randint(-2 ** 90, 2 ** 90)]
            with mm.workdps(60):
                qm = [mm.ldexp(x, -64) for x in q]
                pm = [mm.ldexp(x, -96) for x in p]
                r = mm.sqrt(qm[0] ** 2 + qm[1] ** 2)
                want = int(r >= 20 and (qm[0] * pm[0] + qm[1] * pm[1]) / r > 0)
            assert P(f'calc exitcheck {h(q[0])} {h(q[1])} {h(p[0])} {h(p[1])} 64') == ['ok', str(want)]
    finally:
        P.close()


# ----------------------------------------------------------------- 6. kick tie guard
def test_round_guard(exe):
    P = Proc(exe)
    try:
        s = 200
        for q in (12345, -777):
            base = q * 2 ** s + 2 ** (s - 1)
            assert P(f'calc roundguard {h(base)} {s}')[0] == 'err'
            assert P(f'calc roundguard {h(base + 2 ** s // 10 ** 31)} {s}')[0] == 'err'
            assert P(f'calc roundguard {h(base + 2 ** s // 10 ** 29)} {s}') == ['ok', h(q + 1)]
            assert P(f'calc roundguard {h(base - 2 ** s // 10 ** 29)} {s}') == ['ok', h(q)]
    finally:
        P.close()


# ----------------------------------------------------------------- 7. fault injection (each fault must change a result)
@pytest.mark.parametrize('inject', [1, 2, 4])
def test_injected_track_faults_detected(native, inject):
    from c1b1_native.build import build
    from c1b1_native.reference import PyOneTrack
    a = make(PyOneTrack, 'G1', 0)
    a.run_to(200)
    good = native.BINARY['path']
    native.configure(build('-O2', inject))
    try:
        b = make(native.NativeTrack, 'G1', 0)
        try:
            b.run_to(200)
            assert snap(a) != snap(b)
        finally:
            b.close()
    finally:
        native.configure(good)


def test_injected_turn_fault_detected(native, b2_python):
    from c1b1_native.build import build
    good = native.BINARY['path']
    native.configure(build('-O2', 5))
    try:
        b = make(native.NativeTrack, 'B2', 0)
        try:
            b.run_to_exit(300_000)
            assert snap(b)['turns'] != b2_python['turns']
        finally:
            b.close()
    finally:
        native.configure(good)


@pytest.mark.parametrize('inject', [3, 6])
def test_injected_exp_faults_detected(exe, inject):
    from c1b1_native.build import build
    assert exp_cases(exe, build('-O2', inject)) > 2


# ----------------------------------------------------------------- 8. impulse value end to end
@pytest.mark.parametrize('j,extra', [(0, 0), (0, 16), (6, 16)])
def test_impulse_value_end_to_end(native, j, extra):
    _pes()
    from c1b1_t7.lang import LangForce
    t = make(native.NativeTrack, 'G1', j, extra=extra)
    try:
        for coef, grad in ((Q(40, 6 * 2 ** j), False), (Q(80, 3 * 2 ** j), True)):
            got = t.kick_value(coef.numerator, coef.denominator, grad)
            k = max(60, int(t.fm * 0.30103) + 40)
            vals = {}
            for label, pot, dps in (('py', t.pot, k), ('ref', LangForce(), k + 60)):
                with mm.workdps(dps):
                    qm = t.q_mpf()
                    r = mm.sqrt(qm[0] ** 2 + qm[1] ** 2)
                    d1 = pot.dV(r)
                    c = -d1 / r
                    if grad:
                        hh = mm.mpf(40) / 2 ** j
                        mu = t.mu if label == 'py' else mm.mpf(t.mu)
                        c += hh ** 2 * d1 * pot.d2V(r) / (24 * mu * r)
                    c *= mm.mpf(coef.numerator) / coef.denominator
                    vals[label] = [mm.ldexp(c * x, t.fm) for x in qm]
            with mm.workdps(k + 80):
                for i in range(2):
                    cpp = mm.mpf(got[i]) / mm.mpf(2) ** 128
                    assert abs(cpp - vals['py'][i]) <= mm.ldexp(1, -110), (j, extra, grad, i)
                    assert abs(cpp - vals['ref'][i]) <= mm.ldexp(1, -110), (j, extra, grad, i)
    finally:
        t.close()


# ----------------------------------------------------------------- 9. static checks
def test_no_floating_point_and_no_forbidden_flags():
    from c1b1_native.build import FLAGS, FORBIDDEN
    src = (NATIVE / 'track.cpp').read_text(encoding='utf-8')
    for word in ('double', 'float', '<cmath>', '<math.h>', 'long double'):
        assert word not in src, word
    assert not set(FLAGS) & set(FORBIDDEN)


def test_no_forbidden_imports():
    for f in NATIVE.rglob('*.py'):
        tree = ast.parse(f.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ''] if isinstance(node, ast.ImportFrom) else []
            for n in names:
                assert n.split('.')[0] not in ('a_reference', 'a_numeric', 'engine', 'audit'), (f, n)


# ----------------------------------------------------------------- 10. -O0 and -O2 builds agree
def test_O0_equals_O2(native):
    from c1b1_native.build import build
    good = native.BINARY['path']
    out = []
    try:
        for opt in ('-O0', '-O2'):
            native.configure(build(opt))
            b = make(native.NativeTrack, 'G1', 0)
            try:
                b.run_to(60)
                out.append(snap(b))
            finally:
                b.close()
    finally:
        native.configure(good)
    assert out[0] == out[1]


# ----------------------------------------------------------------- 11. track lifecycle
def test_lifecycle(native):
    a, b = make(native.NativeTrack, 'G1', 0), make(native.NativeTrack, 'G1', 0)
    try:
        a.run_to(100)
        a.run_to(200)
        b.run_to(200)
        assert snap(a) == snap(b)                      # the cached kick survives between commands
        a.run_to_exit(300_000)
        ex = a.exit_tick
        a.run_to(ex + 5)
        assert a.exit_tick == ex and a.tick == ex + 5
        with pytest.raises(RuntimeError, match='no exit within 3 ticks'):
            c = make(native.NativeTrack, 'G1', 0)
            try:
                c.run_to_exit(3)
            finally:
                c.close()
    finally:
        procs = [a.proc, b.proc]
        native.close_all()
    assert all(p.poll() is not None for p in procs)


# ----------------------------------------------------------------- 12. the swap-in harness itself
def test_swapped_track_class_leaves_pen_state_unchanged():
    _pes()
    import c1b1_t7.ladder as L
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative

    def run():
        with mm.workdps(DPS):
            q0, p0 = relative(start('G1'))
            mu = mm.mpf(MU.numerator) / MU.denominator
        r = L.pen_state(LangForceFX2(), q0, p0, '1e-6', j_max=2, mu=mu, mu_exact=MU)
        for t in r.get('track_cost', []):
            t.pop('cpu_s')
        return r
    plain = run()

    class Same(L.FxTrackX):
        pass
    orig = L.FxTrackX
    L.FxTrackX = Same
    try:
        swapped = run()
    finally:
        L.FxTrackX = orig
    assert plain == swapped and plain['status'] == 'accepted'
