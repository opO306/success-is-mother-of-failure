"""Lang 2024 Ar2 jet (V, V', V'') in integer fixed point (cost plan C1, survey_only).

Same formula and parameters as c1b1_t7.lang.LangForce (which stays unchanged and is the reference in the tests).
Every polynomial, rational and damping-series operation runs on Python integers scaled by 2^P,
P = working precision bits + 160:  mul(a, b) = (a b) >> P,  div(a, b) = (a << P) // b  (floor, deterministic).
Only the nine exponentials are evaluated with mpmath (at P + 16 bits) and converted. The result is returned as mpf at
the working precision, so the kick code and its single rounding are unchanged.
Accuracy target (cost plan section 3): |jet(FX) - exact| <= 2^-(fm + 128) max(1, |value|), far below the kick's
1e-30-unit tie guard; then the rounded impulses equal those of LangForce except in a ~1e-36 band (argument, not proof;
the T7 bit-identity replay checks it).
"""
from fractions import Fraction

import mpmath as mm

from c1b1_o1 import model

from .lang import TERMS, pes_path

EXTRA_BITS = 160
EXP_GUARD = 16


class LangForceFX:
    name = 'Ar2_Lang2024_fx'

    def __init__(self, path=None):
        self.params = model.parse(path or pes_path())
        self._fixed = {}
        self._key, self._val = None, None
        self.evaluations = 0

    def _params(self, P):
        """The public decimal parameters rounded once to the 2^-P grid, exactly (Fraction from the decimal string)."""
        if P not in self._fixed:
            self._fixed[P] = {k: [round(Fraction(v) * (1 << P)) for v in vs] for k, vs in self.params.items()}
        return self._fixed[P]

    @staticmethod
    def _exp_neg(X, P):
        """floor(exp(-X 2^-P) 2^P) evaluated at P + EXP_GUARD bits (X >= 0 fixed point)."""
        with mm.workprec(P + EXP_GUARD):
            return int(mm.floor(mm.ldexp(mm.exp(-mm.ldexp(mm.mpf(X), -P)), P)))

    def jet(self, r):
        r = mm.mpf(r)
        key = (r, mm.mp.prec)
        if key == self._key:
            return self._val
        self.evaluations += 1
        W = mm.mp.prec
        P = W + EXTRA_BITS
        prm = self._params(P)
        ONE = 1 << P
        man, ex = r.man_exp
        R = man << (ex + P) if ex + P >= 0 else man >> -(ex + P)
        mul = lambda a, b: (a * b) >> P
        div = lambda a, b: (a << P) // b
        IR = (1 << (2 * P)) // R
        pw = {0: ONE, 1: R, -1: IR}
        for m in range(2, 7):
            pw[m] = mul(pw[m - 1], R)
        for m in range(2, 19):
            pw[-m] = mul(pw[-m + 1], IR)
        v = d = dd = 0
        for name, imin, kmin, kadd in TERMS:
            a = prm['a_' + name]
            count = len(a) // 2
            for j, al in enumerate(prm['alpha_' + name]):
                e = self._exp_neg(mul(al, R), P)
                Pv = P1 = P2 = 0
                for i in range(count):
                    m = imin + i
                    c = a[j * count + i]
                    Pv += mul(c, pw[m])
                    if m:
                        P1 += mul(c * m, pw[m - 1])
                        if m != 1:
                            P2 += mul(c * m * (m - 1), pw[m - 2])
                alP, alP1 = mul(al, Pv), mul(al, P1)
                v += mul(e, Pv)
                d += mul(e, P1 - alP)
                dd += mul(e, P2 - 2 * alP1 + mul(al, alP))
            eta = prm['eta_' + name][0]
            x = mul(eta, R)
            exn = self._exp_neg(x, P)
            cs = prm['C_' + name]
            nmax = 2 * (kmin + len(cs) - 1) + kadd
            terms, sums = [ONE], [ONE]
            for m in range(1, nmax + 1):
                terms.append(mul(terms[-1], x) // m)
                sums.append(sums[-1] + terms[-1])
            eta2 = mul(eta, eta)
            for i, coef in enumerate(cs):
                k = kmin + i
                n = 2 * k + kadd
                f = ONE - mul(exn, sums[n])
                f1 = mul(eta, mul(exn, terms[n]))
                f2 = mul(eta2, mul(exn, terms[n - 1] - terms[n]))
                if i == 0 and name == 'BO':
                    N, N1, N2 = ONE, 0, 0
                    for jj, aa in enumerate(prm['A']):
                        N += mul(aa, pw[jj + 1])
                        N1 += mul(aa * (jj + 1), pw[jj])
                        if jj:
                            N2 += mul(aa * (jj + 1) * jj, pw[jj - 1])
                    D, D1, D2 = ONE, 0, 0
                    for jj, bb in enumerate(prm['B']):
                        D += mul(bb, pw[jj + 1])
                        D1 += mul(bb * (jj + 1), pw[jj])
                        if jj:
                            D2 += mul(bb * (jj + 1) * jj, pw[jj - 1])
                    DD = mul(D, D)
                    Wn = mul(N1, D) - mul(N, D1)
                    f += div(N, D) - ONE
                    f1 += div(Wn, DD)
                    f2 += div(mul(N2, D) - mul(N, D2), DD) - div(2 * mul(D1, Wn), mul(DD, D))
                if i == 0 and name == 'REL':
                    f -= ONE
                g, g1, g2 = pw[-2 * k], -2 * k * pw[-2 * k - 1], 2 * k * (2 * k + 1) * pw[-2 * k - 2]
                v -= mul(coef, mul(f, g))
                d -= mul(coef, mul(f1, g) + mul(f, g1))
                dd -= mul(coef, mul(f2, g) + 2 * mul(f1, g1) + mul(f, g2))
        out = tuple(mm.ldexp(mm.mpf(z), -P) for z in (v, d, dd))
        self._key, self._val = key, out
        return out

    def V(self, r):
        return self.jet(r)[0]

    def dV(self, r):
        return self.jet(r)[1]

    def d2V(self, r):
        return self.jet(r)[2]
