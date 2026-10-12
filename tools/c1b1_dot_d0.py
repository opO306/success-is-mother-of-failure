"""D0 of the dot / dotted-line plan V0 (docs/active/C1B1_DOT_DOTTED_LINE_PLAN_V0.md section 3), information only.

Precision and time breakdown of the radial-quadrature "dot" before M11 is implemented. No world state is produced.
  python tools/c1b1_dot_d0.py FIXTURE OUT_JSON
Inputs fixed in the plan: dev panel G1, B2, B3, H1 (full core), G1-G6 (turning point and barrier tops only).
Per full-core input:
  A-core: c1b1_cont2.scatter turning_point / _leg with V = c1b1_t7.lang_fx2.LangForceFX2.V at 40, 60, 80 digits:
          2A (angle legs in to the turning point and back out to 20), T_ret (time legs), x = T_ret / 40,
          V-call counts and CPU per part (turning point, Taylor patch, angle leg, time leg).
  B-core: c1b1_method_bench.quadref.legs (r_start = r1 = 20) at 80 digits with c1b1_t7.lang.reference_potential.
  Differences converted to grid units at the exit radius 20: momentum |p| dtheta 2^80, position 20 dtheta 2^48,
  position from a time difference v dT 2^48, and the tick quantity dx.
Results are written after every input (partial results survive an interruption).
"""
import hashlib
import json
import platform
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

G = {'G1': ('1/5', '4'), 'G2': ('7/10', '8'), 'G3': ('2', '3'), 'G4': ('2', '9'), 'G5': ('5', '1/2'),
     'G6': ('1/20', '5')}
B = {'B1': ('1/5', '1e-3'), 'B2': ('1/5', '-1e-7'), 'B3': ('3/10', '-1e-5'), 'B4': ('3/10', '1e-9'),
     'B5': ('7/10', '1e-5'), 'B6': ('7/10', '-1e-9')}
H = {'H1': ('27', '0'), 'H2': ('27', '71129/40000')}
FULL = ['G1', 'B2', 'B3', 'H1']
DPS_A = [40, 60, 80]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def panel(fixture, V):
    from c1b1_t7.state import canonical_raw
    orbit = {Q(r['e']): Q(r['b_orb']) for r in fixture['energies']}
    out = {}
    for k, (e, b) in G.items():
        out[k] = dict(e=e, b=b, rho=None, raw=canonical_raw(e, Q(b) ** 2, V))
    for k, (e, rho) in B.items():
        b = orbit[Q(e)] * (1 + Q(rho))
        out[k] = dict(e=e, b=str(b), rho=rho, raw=canonical_raw(e, b * b, V))
    for k, (e, b) in H.items():
        out[k] = dict(e=e, b=b, rho=None, raw=canonical_raw(e, Q(b) ** 2, V))
    return out


class Counted:
    def __init__(self, f):
        self.f, self.n = f, 0

    def __call__(self, r):
        self.n += 1
        return self.f(r)


def start(raw, dps):
    """q, p, mu, H-ready quantities inside the dps block (every Fraction -> mpf conversion happens here)."""
    from c1b1_t7.state import MU, relative
    q, p = relative(raw)                                  # exact grid values
    mu = mm.mpf(MU.numerator) / MU.denominator
    r0 = mm.sqrt(q[0] ** 2 + q[1] ** 2)
    if r0 != 20:
        raise ValueError('start radius is not exactly 20')
    L = q[0] * p[1] - q[1] * p[0]
    return q, p, mu, r0, L


def a_core(raw, dps):
    from c1b1_cont2 import scatter as c2
    from c1b1_t7.lang_fx2 import LangForceFX2
    V = Counted(LangForceFX2().V)
    cpu, calls = {}, {}
    with mm.workdps(dps):
        q, p, mu, r0, L = start(raw, dps)
        Hm = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + V(r0)
        g = lambda r: 2 * mu * (Hm - V(r)) - L * L / (r * r)

        def part(name, fn):
            n0, t0 = V.n, time.process_time()
            res = fn()
            cpu[name], calls[name] = time.process_time() - t0, V.n - n0
            return res

        rt, mins = part('turning_point', lambda: c2.turning_point(g, r0, dps))

        def tay():
            with mm.workdps(dps + 20):
                return [mm.diff(g, rt, n) / mm.factorial(n) for n in range(1, 8)]
        taylor = part('taylor', tay)
        a, ea = part('angle_leg', lambda: c2._leg(g, rt, r0, mins, lambda r: L / (r * r), dps, taylor))
        t, et = part('time_leg', lambda: c2._leg(g, rt, r0, mins, lambda r: mu, dps, taylor))
        pnorm = mm.sqrt(p[0] ** 2 + p[1] ** 2)
        return dict(two_A=2 * a, T_ret=2 * t, x=2 * t / 40, r_t=rt, barrier_tops=mins,
                    g_at_tops=[g(m) / (2 * mu * (Hm - V(r0))) for m in mins], pnorm=pnorm, v=pnorm / mu,
                    quad_err=max(ea, et), cpu=cpu, v_calls=calls)


def b_core(raw, Vref):
    from c1b1_method_bench import quadref
    V = Counted(Vref)
    with mm.workdps(80):
        q, p, mu, r0, L = start(raw, 80)
        E = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + V(r0)
        pr2 = lambda r: 2 * mu * (E - V(r)) - L * L / (r * r)
        t0 = time.process_time()
        sweep, T, rt = quadref.legs(pr2, lambda r, pr: L / (r * r * pr), lambda r, pr: mu / pr, mm.mpf(20),
                                    mm.mpf(20))
        return dict(two_A=sweep, T_ret=T, x=T / 40, r_t=rt, cpu=time.process_time() - t0, v_calls=V.n)


def s(x, n=25):
    return mm.nstr(x, n)


def main(fixture_path, out_path):
    from c1b1_t7.lang import pes_path, reference_potential
    fixture = json.loads(Path(fixture_path).read_bytes())
    Vref = reference_potential()
    res = dict(script_sha256=sha(__file__), fixture_sha256=sha(fixture_path), pes_sha256=sha(pes_path()),
               mpmath=mm.__version__, backend=mm.libmp.BACKEND, python=sys.version.split()[0],
               platform=platform.platform(), inputs={}, barrier_check={}, full={})
    pan = panel(fixture, Vref)
    res['inputs'] = {k: {kk: vv for kk, vv in v.items() if kk != 'raw'} | dict(raw=[str(x) for x in v['raw']])
                     for k, v in pan.items()}

    def save():
        Path(out_path).write_text(json.dumps(res, indent=1), encoding='utf-8')

    save()
    for k in G:                                           # barrier tops only (orbit boundary present at 2 De?)
        with mm.workdps(40):
            from c1b1_cont2 import scatter as c2
            from c1b1_t7.lang_fx2 import LangForceFX2
            F = LangForceFX2()
            q, p, mu, r0, L = start(pan[k]['raw'], 40)
            Hm = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + F.V(r0)
            g = lambda r: 2 * mu * (Hm - F.V(r)) - L * L / (r * r)
            try:
                rt, mins = c2.turning_point(g, r0, 40)
                res['barrier_check'][k] = dict(r_t=s(rt, 12), tops=[s(m, 12) for m in mins],
                                               g_rel=[s(g(m) / (2 * mu * (Hm - F.V(r0))), 6) for m in mins])
            except Exception as exc:                      # recorded, never hidden
                res['barrier_check'][k] = dict(error=repr(exc)[:300])
        print(k, res['barrier_check'][k], flush=True)
        save()
    for k in FULL:
        row = {}
        a = {}
        for d in DPS_A:
            try:
                a[d] = a_core(pan[k]['raw'], d)
                row[f'A{d}'] = dict(two_A=s(a[d]['two_A'], d), T_ret=s(a[d]['T_ret'], d), r_t=s(a[d]['r_t'], 20),
                                    tops=[s(m, 15) for m in a[d]['barrier_tops']],
                                    g_rel_tops=[s(x, 6) for x in a[d]['g_at_tops']],
                                    quad_err=s(a[d]['quad_err'], 3), cpu=a[d]['cpu'], v_calls=a[d]['v_calls'])
            except Exception as exc:
                row[f'A{d}'] = dict(error=repr(exc)[:300])
            print(k, f'A{d}', row[f'A{d}'].get('cpu', row[f'A{d}']), flush=True)
            res['full'][k] = row
            save()
        try:
            b = b_core(pan[k]['raw'], Vref)
            row['B80'] = dict(two_A=s(b['two_A'], 80), T_ret=s(b['T_ret'], 80), r_t=s(b['r_t'], 20), cpu=b['cpu'],
                              v_calls=b['v_calls'])
        except Exception as exc:
            b = None
            row['B80'] = dict(error=repr(exc)[:300])
        print(k, 'B80', row['B80'].get('cpu', row['B80']), flush=True)
        if 80 in a:
            with mm.workdps(100):
                ref = a[80]
                P2, X2 = mm.mpf(2) ** 80, mm.mpf(2) ** 48

                def grid(th, T):
                    dth, dT = abs(th - ref['two_A']), abs(T - ref['T_ret'])
                    return dict(dtheta=s(dth, 3), dT=s(dT, 3), dx=s(dT / 40, 3),
                                mom_units=s(ref['pnorm'] * dth * P2, 3), pos_units=s(20 * dth * X2, 3),
                                pos_from_time_units=s(ref['v'] * dT * X2, 3))
                cmp = {f'A{d}-A80': grid(a[d]['two_A'], a[d]['T_ret']) for d in (40, 60) if d in a}
                if b is not None:
                    cmp['B80-A80'] = grid(b['two_A'], b['T_ret'])
                cmp['margin_rule_mom_units'] = s(mm.mpf(10) ** -30 * ref['pnorm'] * P2, 3)
                cmp['margin_rule_pos_units'] = s(mm.mpf(10) ** -30 * 10 * X2, 3)
                row['compare'] = cmp
        print(k, 'compare', row.get('compare'), flush=True)
        res['full'][k] = row
        save()
    print('D0 DONE', flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
