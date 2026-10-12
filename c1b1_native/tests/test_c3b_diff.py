"""C3b-1 differential tests (plan docs/active/C1B1_C3B_NATIVE_KERNEL_SPEED_PLAN_V0.md section 4): the refactored
track.cpp must answer every command exactly as the sealed C3a source does, including refusals, errors and the limb
boundaries where C3a fails. A -DCHECK_INVARIANTS build of the new source must give the same answers too (it would
print 'err invariant' on a negative zero or an untrimmed value). Kept outside tests/ (designer decision (c)).

Run on Linux with g++:  python -m pytest c1b1_native/tests -q     (needs C1B1_LANG_PES; never skips).
Set C3B1_STATS=path to write the largest limb counts seen by the check build.
"""
import json
import os
import random
import subprocess
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mm
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def exes():
    from c1b1_native.build import SEALED_C3A, build
    return dict(old=build('-O2', src=SEALED_C3A), new=build('-O2'), chk=build('-O2', check=True))


def run(exe, lines):
    """Answers, one per command line; the CPU field of state answers (11 tokens) is masked."""
    out = subprocess.run([str(exe)], input='\n'.join(lines) + '\nquit\n', capture_output=True, text=True,
                         timeout=1800).stdout.splitlines()
    return [' '.join(l.split()[:-1] + ['CPU']) if l.startswith('ok ') and len(l.split()) == 11 else l for l in out]


def same_everywhere(exes, lines):
    old, new, chk = (run(exes[k], lines) for k in ('old', 'new', 'chk'))
    assert len(old) >= len(lines)
    for i, (a, b, c) in enumerate(zip(old, new, chk)):
        assert a == b == c, (i, lines[i] if i < len(lines) else None, a, b, c)
    assert len(old) == len(new) == len(chk)
    return old


def h(x):
    return format(int(x), 'x') if x >= 0 else '-' + format(-int(x), 'x')


# ----------------------------------------------------------------- sealed copy
def test_sealed_copy_is_the_c3a_source():
    from c1b1_native.build import SEALED_C3A, SEALED_C3A_SHA256, lf_sha256
    assert lf_sha256(SEALED_C3A)[:16] == SEALED_C3A_SHA256
    src = SEALED_C3A.read_text(encoding='utf-8')
    for word in ('double', 'float', '<cmath>', '<math.h>', 'long double'):
        assert word not in src, word


# ----------------------------------------------------------------- arithmetic, refusals, limb boundaries
def calc_lines(seed=20261012, n=2000):
    rnd = random.Random(seed)

    def num(bits, sign=None):
        x = (rnd.getrandbits(bits) | (1 << (bits - 1))) if bits > 0 else 0
        neg = rnd.random() < 0.5 if sign is None else sign
        return -x if neg else x

    def limbs(k):                                          # exactly k limbs (top bit of the top limb set)
        return num(64 * k) if k else 0
    L = []
    special = [0, 1, -1, 2, -2, 3, 2 ** 63, 2 ** 64 - 1, 2 ** 64, -(2 ** 64), 2 ** 128 - 1, -(2 ** 127)]
    for _ in range(n):
        a, b = num(rnd.randint(0, 1700)), num(rnd.randint(0, 1700))
        if rnd.random() < 0.15:
            a, b = rnd.choice(special), rnd.choice(special)
        L += [f'calc add {h(a)} {h(b)}', f'calc sub {h(a)} {h(b)}', f'calc sub {h(a)} {h(a)}']
        ka = rnd.randint(1, 27)
        kb = rnd.choice([27 - ka, 28 - ka, 29 - ka, rnd.randint(0, 28 - ka)])     # sums 27, 28, 29 (C3a: >28 fails)
        L.append(f'calc mul {h(limbs(ka) * rnd.choice([1, -1]))} {h(limbs(max(kb, 0)))}')
        L.append(f'calc mul {h(a)} {h(rnd.choice(special))}')
        A = num(rnd.randint(1, 1790))
        for B in (num(rnd.randint(1, 64)), num(rnd.randint(65, 1700)), rnd.choice([1, -1, 3, -3, 2 ** 64 - 1]),
                  0, A, -A, A + 1):
            L.append(f'calc divmod {h(A)} {h(B)}')
        L.append(f'calc divmod {h(num(rnd.randint(0, 600)))} {h(rnd.randint(1, 400))}')   # exp-series divisions
        s = rnd.choice([0, 1, 63, 64, 65, rnd.randint(0, 600), 64 * rnd.randint(1, 3) + rnd.randint(-2, 2)])
        L += [f'calc shl {h(a)} {s}', f'calc shr {h(A)} {s}', f'calc shr {h(-abs(A) or -1)} {bitlen(A) + rnd.randint(0, 5)}']
        L.append(f'calc shl {h(limbs(rnd.randint(25, 28)))} {rnd.randint(0, 260)}')        # near the 28-limb limit
        L.append(f'calc isqrt {h(A)}')
        den = num(rnd.randint(1, 200))
        L += [f'calc halfeven {h(num(rnd.randint(0, 400)))} {h(den)}',
              f'calc halfeven {h(rnd.randint(-50, 50) * abs(den) + abs(den) // 2)} {h(den)}']
        p = rnd.choice([60, 200, 300, 365, 400])
        X = rnd.choice([0, 1, -5, num(rnd.randint(1, p + 10), False), -num(rnd.randint(1, p), False)])
        L.append(f'calc expneg {h(X)} {p} {h(num(p + 64, False))}')
        q = [num(rnd.randint(60, 120)) for _ in range(2)]
        pp = [num(rnd.randint(60, 120)) for _ in range(2)]
        L.append(f'calc exitcheck {h(q[0])} {h(q[1])} {h(pp[0])} {h(pp[1])} {rnd.choice([0, 32, 64, 100])}')
        L.append(f'calc roundguard {h(num(rnd.randint(0, 300)))} {rnd.choice([0, 1, 2, 64, 200])}')
    # review m3: the Knuth branch where the partial remainder's top limb equals the divisor's top limb (the divq path
    # is not taken there), and one-limb division of an all-ones dividend by 2^64 - 1
    for k in range(40):
        v = (1 << 127) + (1 << 64) - 1 - rnd.randint(0, 1000)          # top limb 0x8000..., normalised (shift 0)
        r = (1 << 127) + rnd.randint(0, 2 ** 63)                        # r < v, top limb equal to v's
        assert r < v and r >> 64 == v >> 64
        u = ((v * rnd.getrandbits(64 * (k % 5 + 1)) + r) << 64) | rnd.getrandbits(64)
        L += [f'calc divmod {h(u)} {h(v)}', f'calc divmod {h(-u)} {h(v)}', f'calc divmod {h(u)} {h(-v)}']
    for k in (1, 2, 13, 27):
        L += [f'calc divmod {h(2 ** (64 * k) - 1)} {h(2 ** 64 - 1)}', f'calc divmod {h(2 ** (64 * k) - 1)} 1']
    L += ['calc divmod 5 0', 'calc isqrt -4', 'calc shl 1 -1', 'calc shr 1 -1', 'calc nosuchop',
          f'calc add {"f" * (16 * 28 + 1)} 1', f'calc add {"f" * (16 * 28)} 1', f'calc mul {"f" * (16 * 14)} {"f" * (16 * 14)}',
          f'calc mul {"f" * (16 * 14)} {"f" * (16 * 15)}', 'calc add 1g 1', 'calc add - 1', 'to 5', 'jet 5']
    return L


def bitlen(x):
    return abs(int(x)).bit_length()


def test_calc_identical(exes):
    same_everywhere(exes, calc_lines())


# ----------------------------------------------------------------- jet, kick values and tracks (dev-panel starts)
def _starts():
    from c1b1_t7.lang import reference_potential
    from c1b1_t7.state import canonical_raw
    V = reference_potential()
    fx = json.loads((ROOT / 'a_reference/fixtures/c1b1_orbit_boundary_v3.json').read_bytes())
    b_orb = {Q(r['e']): Q(r['b_orb']) for r in fx['energies']}
    b2 = b_orb[Q('1/5')] * (1 + Q('-1e-7'))
    b6 = b_orb[Q('7/10')] * (1 + Q('-1e-9'))
    return {'G1': canonical_raw('1/5', Q(4) ** 2, V), 'B2': canonical_raw('1/5', b2 * b2, V),
            'B6': canonical_raw('7/10', b6 * b6, V)}


_S = {}


def init(name, j, method='chin', W=None, extra=0):
    """The init line NativeTrack would send for this dev-panel start (Python-side start rounding)."""
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import grid
    from c1b1_native.reference import PyOneTrack
    from c1b1_native.track import init_line
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative
    if not _S:
        _S.update(_starts())
    fp, fm = grid(j)
    with mm.workdps(DPS):
        q0, p0 = relative(_S[name])
        mu = mm.mpf(MU.numerator) / MU.denominator
        t = PyOneTrack(LangForceFX2(), q0, p0, j, method, fp + extra, fm + extra, mu, 40, MU)
        return init_line(t.pot, t.fp, t.fm, j, method, 40, t.qr, t.pr_, t.mu_x, t.mu, W=W)


def test_jet_identical(exes):
    from c1b1_t7.lang_fx2 import EXTRA_BITS
    lines = []
    for dps in (60, 68, 77, 80):
        with mm.workdps(dps):
            W = mm.mp.prec
        lines.append(init('G1', 0, W=W))
        for k in range(61):
            r = mm.mpf(2) * mm.mpf(20) ** (mm.mpf(k) / 60)
            with mm.workprec(W + EXTRA_BITS + 64):
                lines.append(f'jet {h(int(mm.floor(r * mm.mpf(2) ** (W + EXTRA_BITS))))}')
    lines += ['jet 0', 'jet -5', 'jet 1']
    same_everywhere(exes, lines)


def test_kickval_identical(exes):
    lines = []
    for name in ('G1', 'B2', 'B6'):
        for j in (0, 4):
            lines.append(init(name, j))
            hd = 2 ** j
            for cn, cd, g in ((40, 6 * hd, 0), (80, 3 * hd, 1), (40, 2 * hd, 0), (80, 3 * hd, 0)):
                lines.append(f'kickval {cn} {cd} {g}')
    same_everywhere(exes, lines)


@pytest.mark.parametrize('method', ['chin', 'kdk'])
def test_interleaved_track_sessions_identical(exes, method):
    lines = []
    for name in ('G1', 'B6'):
        for j in (0, 2, 4):
            lines += [init(name, j, method), 'to 100', 'kickval 40 6 0', 'jet 1000000000000000000000000000000',
                      'to 200', init(name, j, method), 'to 300', 'to_exit 3', 'to 310', 'kickval 80 3 1', 'to 320']
    same_everywhere(exes, lines)


def test_full_exit_with_turns_identical(exes):
    lines = []
    for name in ('G1', 'B2'):
        for method in ('chin', 'kdk'):
            lines += [init(name, 0, method), 'to_exit 300000', 'to_exit 300000', 'to 5']
    out = same_everywhere(exes, lines)
    turns = [int(l.split()[4]) for l in out if l.startswith('ok ') and len(l.split()) == 11]
    assert max(turns) >= 1, 'the B2 track must exercise the turn count'


def test_check_build_stats(exes):
    lines = [init('B6', 4, extra=16), 'to 200', init('G1', 0), 'to_exit 300000', 'stats']
    out = run(exes['chk'], lines)
    assert all(not l.startswith('err') for l in out), out
    maxn, maxsum = map(int, out[-1].split()[1:])
    assert maxsum <= 28
    if os.environ.get('C3B1_STATS'):
        Path(os.environ['C3B1_STATS']).write_text(json.dumps(dict(max_limbs=maxn, max_mul_limb_sum=maxsum)))
