"""NativeTrack: FxTrackX whose arithmetic runs in the C3a C++ executable (c1b1_native/track.cpp), one process per track.

Python keeps: the start-state rounding (FxTrack.__init__), q_mpf / r / pr / state, and the one-shot sweep
(c1b1_native.reference). C++ does: the Lang jet, kicks (1e-30 tie guard), drifts, ticks, exit test, turn count.
Text protocol, integers in hex. Any C++ refusal raises NativeRefused (never a guessed value).
"""
import subprocess

import mpmath as mm

from c1b1_t7.lang import TERMS
from c1b1_t7.lang_fx2 import EXTRA_BITS, LangForceFX2

from .reference import OneShotSweep
from c1b1_t7.ladder import FxTrackX


class NativeRefused(Exception):
    pass


class NativeError(RuntimeError):
    pass


BINARY = {'path': None}
_LIVE, _CLOSED_CPU_NS = [], [0]


def configure(path):
    BINARY['path'] = str(path)


def child_cpu_s():
    return (_CLOSED_CPU_NS[0] + sum(t.cpu_ns for t in _LIVE)) / 1e9


def close_all():
    for t in list(_LIVE):
        t.close()


def _h(x):
    return format(int(x), 'x')


def kick_precision_bits(fm):
    with mm.workdps(max(60, int(fm * 0.30103) + 40)):         # FxTrackP._kick_raw
        return mm.mp.prec


def init_line(pot, fp, fm, j, method, h0, qr, pr, mu_exact, mu_kick, W=None):
    """W: kick working precision in bits (default: the FxTrackP rule for fm; tests may override)."""
    W = kick_precision_bits(fm) if W is None else W
    P = W + EXTRA_BITS
    prm = pot._params(P)
    with mm.workprec(P + 192):
        ln2q = int(mm.floor(mm.ln2 * mm.mpf(2) ** (P + 64)))
    man, ex = mu_kick.man_exp
    parts = ['init', fp, fm, j, method, h0, W, *map(_h, qr), *map(_h, pr), _h(mu_exact.numerator),
             _h(mu_exact.denominator), _h(man), ex, _h(ln2q), len(TERMS)]
    for name, imin, kmin, kadd in TERMS:
        a, al, eta, cs = prm['a_' + name], prm['alpha_' + name], prm['eta_' + name], prm['C_' + name]
        if len(eta) != 1:
            raise ValueError('eta')
        parts += [name, imin, kmin, kadd, len(a), *map(_h, a), len(al), *map(_h, al), _h(eta[0]), len(cs),
                  *map(_h, cs)]
    parts += [len(prm['A']), *map(_h, prm['A']), len(prm['B']), *map(_h, prm['B']), 'end']
    return ' '.join(str(x) for x in parts)


class NativeTrack(OneShotSweep, FxTrackX):
    def __init__(self, pot, q, p, j, method, fp, fm, mu, h0, mu_exact):
        super().__init__(pot, q, p, j, method, fp, fm, mu, h0, mu_exact)
        if not isinstance(pot, LangForceFX2):
            raise TypeError('NativeTrack reproduces LangForceFX2 only')
        if self.h0.denominator != 1 or method not in ('chin', 'kdk'):
            raise ValueError('h0 must be an integer; method chin or kdk')
        self.turns, self.q_start, self.kicks, self.cpu_ns = 0, list(self.qr), 0, 0
        if BINARY['path'] is None:
            raise NativeError('c1b1_native.track.configure(binary) not called')
        self.proc = subprocess.Popen([BINARY['path']], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                     bufsize=1)
        _LIVE.append(self)
        self._apply(self._cmd(init_line(pot, fp, fm, j, method, int(self.h0), self.qr, self.pr_, self.mu_x,
                                        self.mu)))

    def _cmd(self, line):
        if self.proc is None:
            raise NativeError('track closed')
        self.proc.stdin.write(line + '\n')
        self.proc.stdin.flush()
        out = self.proc.stdout.readline()
        if not out:
            raise NativeError(f'native track gave no answer (exit {self.proc.poll()})')
        f = out.split()
        if f[0] == 'err':
            msg = out[4:].strip()
            if msg.startswith('refuse'):
                raise NativeRefused(msg)
            raise NativeError(msg)
        if f[0] != 'ok':
            raise NativeError('malformed answer: ' + out[:200])
        return f[1:]

    def _apply(self, f):
        if len(f) != 10:
            raise NativeError(f'state answer has {len(f)} fields, expected 10')
        self.tick, ex, self.substeps, self.turns = int(f[0]), int(f[1]), int(f[2]), int(f[3])
        self.exit_tick = None if ex < 0 else ex
        self.qr = [int(f[4], 16), int(f[5], 16)]
        self.pr_ = [int(f[6], 16), int(f[7], 16)]
        self.kicks, self.cpu_ns = int(f[8]), int(f[9])

    def run_to_exit(self, max_ticks):
        try:
            self._apply(self._cmd(f'to_exit {int(max_ticks)}'))
        except NativeError as exc:
            if str(exc) == 'no exit':
                raise RuntimeError(f'level {self.j}: no exit within {max_ticks} ticks') from None
            raise

    def run_to(self, n):
        self._apply(self._cmd(f'to {int(n)}'))

    def advance_tick(self):
        self.run_to(self.tick + 1)

    def jet_raw(self, R):
        return [int(x, 16) for x in self._cmd(f'jet {_h(R)}')]

    def kick_value(self, cn, cd, gradient):
        """Values before rounding of both impulse components, in units of 2^-(fm + 128)."""
        return [int(x, 16) for x in self._cmd(f'kickval {int(cn)} {int(cd)} {int(bool(gradient))}')]

    def close(self):
        if self.proc is not None:
            try:
                self.proc.stdin.write('quit\n')
                self.proc.stdin.flush()
                self.proc.wait(timeout=10)
            except Exception:
                self.proc.kill()
                self.proc.wait()
            self.proc = None
            _CLOSED_CPU_NS[0] += self.cpu_ns
            if self in _LIVE:
                _LIVE.remove(self)
