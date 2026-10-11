"""S3 debug (survey_only): why quadref.reference failed closed at rho = +1e-6 on 3 of 6 killer inputs.
Hypothesis: the turning-point scan steps over the narrow forbidden band at the barrier top and returns the inner wall.
Prints, per input: forbidden band [ri, ro] around r*, band width vs scan step, and which root turning() returned.
  python tools/c1b1_method_bench_s3_debug_reference.py
"""
import sys

import mpmath as mm

sys.path.insert(0, 'tools')
from c1b1_method_bench import quadref  # noqa: E402
from c1b1_method_bench.potentials import MU  # noqa: E402
import c1b1_method_bench_s3 as s3  # noqa: E402


def root(f, a, b, n=400):
    fa = f(a)
    for _ in range(n):
        m = (a + b) / 2
        if (f(m) > 0) == (fa > 0): a, fa = m, f(m)
        else: b = m
    return (a + b) / 2


def main():
    step = 1 - (mm.mpf('0.005') / 20) ** (mm.mpf(1) / 3000)
    print('scan relative step', mm.nstr(step, 4))
    for name, cls in s3.POTS.items():
        pot = cls()
        for frac in s3.FRACS:
            for rho in ('1e-6', '1e-5'):
                E, bb, o = s3.killer_input(pot, frac, mm.mpf(rho))
                with mm.workdps(quadref.DPS):
                    L = bb * mm.sqrt(2 * MU * E)
                    pr2 = lambda r: 2 * MU * (E - pot.V(r)) - L * L / (r * r)
                    rs = o['r_star']
                    w = mm.mpf('0.2')                          # true band is ~0.01-0.05 bohr; a wide bracket can catch the wall root
                    assert pr2(rs) < 0 < pr2(rs + w) and pr2(rs - w) > 0
                    ro = root(pr2, rs, rs + w)
                    ri = root(pr2, rs - w, rs)
                    try:
                        rt = quadref.turning(pr2, mm.mpf(quadref.R0))
                        which = 'outer(ok)' if abs(rt - ro) < mm.mpf('1e-30') else ('inner wall (SKIPPED band)' if rt < ri else 'other')
                    except ValueError as exc:
                        rt, which = None, repr(exc)
                    print(name[:9], frac, rho, 'pr2(r*)', mm.nstr(pr2(rs), 3), 'band', mm.nstr(ro - ri, 4),
                          'band/(r* step)', mm.nstr((ro - ri) / (rs * step), 3), 'turning ->', which,
                          mm.nstr(rt, 8) if rt is not None else '')


if __name__ == '__main__':
    main()
