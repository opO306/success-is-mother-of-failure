"""Information-only probe (C3 plan, designer question 2026-10-12): accumulated sweep vs one-shot sweep.

  python tools/c1b1_sweep_oneshot_probe.py OUT_JSON
Input: dot-plan dev panel G1 (E = 1/5 De, b = 4 bohr; not a T7 input), canonical start state.
For levels j = 0 and 1 of the M10 grid rule, the same Chin track (LangForceFX2, exact reduced mass) runs to its exit
twice from the same start:
  ACC  = c1b1_t7.ladder.FxTrackX as is: sweep += signed_angle(q_old, q_new) at 60 digits every substep;
  ONE  = the same arithmetic without the per-substep angle; instead an exact integer count of crossings of the
         negative x axis (y sign change while x < 0), and at the end
             sweep = 2 pi turns + atan2(q_end) - atan2(q_start)        (one evaluation, exact integer inputs).
Reported: raw states identical (sanity), CPU of each run, cost of the final one-shot evaluation, and the error of
ACC and ONE (at 60 digits) against ONE evaluated at 120 digits (the exact value of the same telescoping sum).
No world state is produced or changed.
"""
import json
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

import mpmath as mm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class OneShot:
    """Mixin: FxTrackX arithmetic, sweep replaced by an exact turn count."""

    def setup_turns(self):
        self.turns = 0
        self.q_start = list(self.qr)

    def advance_tick(self):
        for _ in range(self.sub):
            x0, y0 = self.qr
            self._substep()
            x1, y1 = self.qr
            if x0 < 0 and x1 < 0:
                if y0 >= 0 > y1:
                    self.turns += 1
                elif y0 < 0 <= y1:
                    self.turns -= 1
        self.substeps += self.sub
        self.tick += 1

    def oneshot(self, dps):
        with mm.workdps(dps):
            a0 = mm.atan2(self.q_start[1], self.q_start[0])
            a1 = mm.atan2(self.qr[1], self.qr[0])
            return 2 * mm.pi * self.turns + a1 - a0


def main(out):
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import grid
    from c1b1_t7.ladder import FxTrackX
    from c1b1_t7.lang import reference_potential
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, canonical_raw, relative

    class OneTrack(OneShot, FxTrackX):
        pass

    raw = canonical_raw('1/5', Q(4) ** 2, reference_potential())
    res = dict(script=Path(__file__).name, input='dev G1 (1/5 De, b = 4)', mpmath=mm.__version__, levels=[])
    for j in (0, 1):
        fp, fm = grid(j)
        row = dict(j=j, grid=[fp, fm])
        with mm.workdps(DPS):
            q0, p0 = relative(raw)
            mu = mm.mpf(MU.numerator) / MU.denominator
            acc = FxTrackX(LangForceFX2(), q0, p0, j, 'chin', fp, fm, mu, 40, MU)
            t = time.process_time()
            acc.run_to_exit(300_000)
            row['acc_cpu_s'] = time.process_time() - t
            one = OneTrack(LangForceFX2(), q0, p0, j, 'chin', fp, fm, mu, 40, MU)
            one.setup_turns()
            t = time.process_time()
            one.run_to_exit(300_000)
            row['one_cpu_s'] = time.process_time() - t
        t = time.process_time()
        s60 = one.oneshot(60)
        row['oneshot_eval_s'] = time.process_time() - t
        s120 = one.oneshot(120)
        with mm.workdps(130):
            row.update(identical_raw=(acc.qr, acc.pr_, acc.tick) == (one.qr, one.pr_, one.tick),
                       tick=acc.tick, substeps=acc.substeps, turns=one.turns,
                       sweep_acc=mm.nstr(acc.sweep, 50), sweep_one60=mm.nstr(s60, 50),
                       sweep_one120=mm.nstr(s120, 70),
                       err_acc=mm.nstr(abs(acc.sweep - s120), 3), err_one60=mm.nstr(abs(s60 - s120), 3),
                       nstr45_equal=mm.nstr(acc.sweep, 45) == mm.nstr(s60, 45))
        row['us_per_substep_acc'] = 1e6 * row['acc_cpu_s'] / acc.substeps
        row['us_per_substep_one'] = 1e6 * row['one_cpu_s'] / one.substeps
        res['levels'].append(row)
        print(json.dumps(row), flush=True)
        Path(out).write_text(json.dumps(res, indent=1), encoding='utf-8')
    print('PROBE DONE', flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
