"""T7 part-test run 1 diagnosis (survey_only): scatter_many vs cont2.scatter differ by 4-6e-18 in the sweep (design
1e-20). Which one moves with precision? Ar O-1 'ordinary', exit 20.0123, and bench Morse narrow band, exits 20.0731/20.4.
Rows: cont2.scatter (check off) and scatter_many (check off) at 40/60/80 digits, plus the pieces at 80 digits:
cont2 legs A(r0), A(r_e) and the tail int_{r0}^{r_e}.
  python tools/c1b1_t7_debug_reference.py
"""
import sys
from pathlib import Path

import mpmath as mm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def pieces(V, mu, q, p, re, dps):
    from c1b1_cont2 import scatter as c2
    with mm.workdps(dps):
        q, p, mu, re = [mm.mpf(x) for x in q], [mm.mpf(x) for x in p], mm.mpf(mu), mm.mpf(re)
        r0 = mm.sqrt(q[0] ** 2 + q[1] ** 2)
        H = (p[0] ** 2 + p[1] ** 2) / (2 * mu) + V(r0)
        L = q[0] * p[1] - q[1] * p[0]
        g = lambda r: 2 * mu * (H - V(r)) - L * L / (r * r)
        rt, mins = c2.turning_point(g, r0, dps)
        with mm.workdps(dps + 20):
            taylor = [mm.diff(g, rt, n) / mm.factorial(n) for n in range(1, 8)]
        w = lambda r: L / (r * r)
        a0, e0 = c2._leg(g, rt, r0, mins, w, dps, taylor)
        a1, e1 = c2._leg(g, rt, re, mins, w, dps, taylor)
        tail, et = mm.quad(lambda r: L / (r * r * mm.sqrt(g(r))), [r0, re], error=True)
        return dict(dps=dps, A_r0=mm.nstr(a0, 30), A_re=mm.nstr(a1, 30), A_re_minus_A_r0=mm.nstr(a1 - a0, 30),
                    tail=mm.nstr(tail, 30), err=[mm.nstr(e0, 3), mm.nstr(e1, 3), mm.nstr(et, 3)],
                    mins=[mm.nstr(m, 12) for m in mins], rt=mm.nstr(rt, 20))


def case(name, V, mu, q, p, exits):
    from c1b1_cont2 import scatter as c2
    from c1b1_t7.reference import scatter_many
    for dps in (40, 60, 80):
        many = scatter_many(V, mu, q, p, exits, dps=dps, check=False)
        for re, x in zip(exits, many['exits']):
            one = c2.scatter(V, mu, q, p, mm.mpf(re), dps=dps, check=False)
            print(name, dps, re, 'cont2', one['sweep'][:32], 'many', x['sweep'][:32], flush=True)
    for re in exits:
        for dps in (40, 80):
            print(name, re, pieces(V, mu, q, p, re, dps), flush=True)


def main():
    from c1b1_method_bench import orbit
    from c1b1_method_bench.potentials import MU, Morse
    from c1b1_method_bench.run import initial
    from c1b1_t7.lang import reference_potential
    from c1b1_t7.state import MU as MUX, relative
    import json
    root = Path(__file__).resolve().parents[1]
    row = next(r for r in json.loads((root / 'docs/active/C1B1_O1_INPUTS_V1.json').read_bytes())['payload']['inputs']
               if r['id'] == 'ordinary')
    q, p = relative(row['raw'])
    with mm.workdps(100):
        mu = mm.mpf(MUX.numerator) / MUX.denominator
    case('Ar_ordinary', reference_potential(), mu, q, p, ['20.0123'])
    pot = Morse()
    with mm.workdps(60):
        E = orbit.e_max(pot) * mm.mpf('0.6')
        b = orbit.orbit(pot, MU, E)['b_orb'] * (1 + mm.mpf('1e-8'))
    with mm.workdps(80):
        q, p, _ = initial(pot, MU, E, b)
    case('Morse_narrow', pot.V, MU, q, p, ['20.0731', '20.4'])


if __name__ == '__main__':
    main()
