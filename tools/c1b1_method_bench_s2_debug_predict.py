"""S2 failure gate: reproduce the single M7 'mpc' error (T3 Coulomb, E = 2 De, b = 6, h = 40) and test the
hypothesis that p_r^2 at the turning point chosen at the working precision becomes negative at the higher
internal precision mpmath.quad uses. Diagnostic only; changes nothing."""
import mpmath as mm

from c1b1_method_bench import quadref
from c1b1_method_bench.potentials import DE, MU, Coulomb
from c1b1_method_bench.run import run


def modified_pr2(pot, mu, q0, p0, h):
    """Same algebra as quadref.kdk_modified (copied here so the internals can be inspected)."""
    r0 = mm.sqrt(q0[0] ** 2 + q0[1] ** 2)
    L = q0[0] * p0[1] - q0[1] * p0[0]
    prr0 = (q0[0] * p0[0] + q0[1] * p0[1]) / r0
    U, d1, d2 = pot.V, pot.dV, pot.d2V
    h2 = h * h
    c = lambda r: 1 / (2 * mu) + h2 * d2(r) / (12 * mu * mu)
    W = lambda r: L * L / (2 * mu * r * r) + U(r) + h2 * (d1(r) * L * L / (12 * mu * mu * r ** 3) - d1(r) ** 2 / (24 * mu))
    Ht = c(r0) * prr0 ** 2 + W(r0)
    return (lambda r: (Ht - W(r)) / c(r)), r0


def main():
    pot = Coulomb()
    for h in (40, 20):
        row = run(pot, 'kdk', 2 * DE, 6, h)
        print('h', h, 'status', row['status'], 'r_exit', row['r_exit'], 'err_sweep', row['err_sweep'])
        for which in ('modified', 'true'):
            try:
                if which == 'modified':
                    quadref.kdk_modified(pot, MU, row['q0'], row['p0'], h, row['r_exit'])
                else:
                    E = 2 * DE; L = 6 * mm.sqrt(2 * MU * E)
                    quadref.reference(pot, MU, E, L, row['r_exit'])
                print('  ', which, 'ok')
            except Exception as exc:
                print('  ', which, 'FAILED', repr(exc)[:160])
        with mm.workdps(quadref.DPS):
            q0, p0 = [mm.mpf(x) for x in row['q0']], [mm.mpf(x) for x in row['p0']]
            pr2, r0 = modified_pr2(pot, MU, q0, p0, mm.mpf(h))
            rt = quadref.turning(pr2, r0)
            v60 = pr2(rt)
        for extra in (0, 10, 20, 40):
            with mm.workdps(quadref.DPS + extra):
                pr2x, _ = modified_pr2(pot, MU, [mm.mpf(x) for x in row['q0']], [mm.mpf(x) for x in row['p0']], mm.mpf(h))
                print('   pr2(rt) at dps', quadref.DPS + extra, '=', mm.nstr(pr2x(rt), 5))
        print('   rt', mm.nstr(rt, 30), 'pr2(rt)@60', mm.nstr(v60, 5))


if __name__ == '__main__':
    main()
