"""Lang 2024 Ar2 potential with analytic V, V', V'' for the fixed-point Chin 4A runs (T7, survey_only).

Same public decimal parameters as c1b1_o1.model (parsed by model.parse from the .f90 file; model.Potential is V only and
stays the reference's potential). Term by term (r in bohr, V in hartree):
  short range   e^{-a r} P(r),  P = sum_i c_i r^{m_i}
                (e P)' = e (P' - a P),   (e P)'' = e (P'' - 2 a P' + a^2 P)
  dispersion    -C_k f_n(x) / r^{2k},  x = eta r,  f_n = 1 - e^{-x} S_n(x),  S_n = sum_{m<=n} x^m / m!
                df_n/dr = eta e^{-x} x^n / n!,   d2f_n/dr2 = eta^2 e^{-x} (x^{n-1} / (n-1)! - x^n / n!)
                BO first term: f += N/D - 1 (rational N = 1 + sum a_j r^{j+1}, D = 1 + sum b_j r^{j+1});
                REL first term: f -= 1 (a constant: derivatives unchanged)
The last evaluation is cached by (r, working precision): FxTrack asks for V' and then V'' at the same r.
"""
import os
from pathlib import Path

import mpmath as mm

from c1b1_o1 import model

PARAM_DPS = 160
TERMS = [('BO', -1, 3, 1), ('REL', 0, 2, 0), ('QED', 0, 3, 0)]       # as c1b1_o1.model.Potential


def pes_path():
    return Path(os.environ.get('C1B1_LANG_PES', 'D:/reference/ar2_lang2024/S2_ar2_pot.f90'))


def reference_potential(path=None):
    """c1b1_o1.model.Potential (V only) with parameters converted at PARAM_DPS digits."""
    params = model.parse(path or pes_path())
    with mm.workdps(PARAM_DPS):
        return model.Potential(params=params)


class LangForce:
    name = 'Ar2_Lang2024'

    def __init__(self, path=None):
        params = model.parse(path or pes_path())
        with mm.workdps(PARAM_DPS):
            self.p = {k: [mm.mpf(v) for v in vs] for k, vs in params.items()}
        self._key, self._val = None, None
        self.evaluations = 0

    def jet(self, r):
        r = mm.mpf(r)
        key = (r, mm.mp.prec)
        if key == self._key:
            return self._val
        self.evaluations += 1
        p = self.p
        v = d = dd = mm.mpf(0)
        ir = 1 / r
        for name, imin, kmin, kadd in TERMS:
            a = p['a_' + name]
            count = len(a) // 2
            for j, al in enumerate(p['alpha_' + name]):
                e = mm.exp(-al * r)
                P = P1 = P2 = mm.mpf(0)
                for i in range(count):
                    m = imin + i
                    c = a[j * count + i]
                    rm = r ** m
                    P += c * rm
                    P1 += c * m * rm * ir
                    P2 += c * m * (m - 1) * rm * ir * ir
                v += e * P
                d += e * (P1 - al * P)
                dd += e * (P2 - 2 * al * P1 + al * al * P)
            eta = p['eta_' + name][0]
            x = eta * r
            ex = mm.exp(-x)
            cs = p['C_' + name]
            nmax = 2 * (kmin + len(cs) - 1) + kadd
            terms, sums = [mm.mpf(1)], [mm.mpf(1)]
            for m in range(1, nmax + 1):
                terms.append(terms[-1] * x / m)
                sums.append(sums[-1] + terms[-1])
            for i, coef in enumerate(cs):
                k = kmin + i
                n = 2 * k + kadd
                f = 1 - ex * sums[n]
                f1 = eta * ex * terms[n]
                f2 = eta * eta * ex * (terms[n - 1] - terms[n])
                if i == 0 and name == 'BO':
                    N, N1, N2 = mm.mpf(1), mm.mpf(0), mm.mpf(0)
                    for jj, aa in enumerate(p['A']):
                        N += aa * r ** (jj + 1)
                        N1 += aa * (jj + 1) * r ** jj
                        N2 += aa * (jj + 1) * jj * r ** (jj - 1) if jj else 0
                    D, D1, D2 = mm.mpf(1), mm.mpf(0), mm.mpf(0)
                    for jj, bb in enumerate(p['B']):
                        D += bb * r ** (jj + 1)
                        D1 += bb * (jj + 1) * r ** jj
                        D2 += bb * (jj + 1) * jj * r ** (jj - 1) if jj else 0
                    W = N1 * D - N * D1
                    f += N / D - 1
                    f1 += W / (D * D)
                    f2 += (N2 * D - N * D2) / (D * D) - 2 * D1 * W / (D * D * D)
                if i == 0 and name == 'REL':
                    f -= 1
                g = ir ** (2 * k)
                g1 = -2 * k * g * ir
                g2 = 2 * k * (2 * k + 1) * g * ir * ir
                v -= coef * f * g
                d -= coef * (f1 * g + f * g1)
                dd -= coef * (f2 * g + 2 * f1 * g1 + f * g2)
        self._key, self._val = key, (v, d, dd)
        return self._val

    def V(self, r):
        return self.jet(r)[0]

    def dV(self, r):
        return self.jet(r)[1]

    def d2V(self, r):
        return self.jet(r)[2]
