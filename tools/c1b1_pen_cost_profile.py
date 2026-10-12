"""Pen cost profile (survey_only, information only): where does one Chin 4A fixed-point substep spend its time?

One Ar input from the sealed T7 list (default O:ordinary), M10 level 0 (h = 40, grid (64, 96)) and level 1
(h = 20, grid (68, 100)), N ticks each under cProfile, plus a plain timing of the main pieces in isolation:
force jet, impulse rounding, drift, swept-angle update. Also reports whether gmpy2 backs mpmath.
  python tools/c1b1_pen_cost_profile.py INPUTS_JSON OUT_PREFIX [JOB_ID] [TICKS] [fx|fx2]
  (fx / fx2: use the fixed-point jet c1b1_t7.lang_fx.LangForceFX / lang_fx2.LangForceFX2 instead of
   c1b1_t7.lang.LangForce; cost plan C1 / C1.1)
"""
import cProfile
import io
import json
import pstats
import sys
import time
from pathlib import Path

import mpmath as mm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import grid
    from c1b1_method_bench.run import signed_angle
    from c1b1_t7.ladder import FxTrackX
    from c1b1_t7.lang import LangForce
    from c1b1_t7.state import MU, relative
    inputs, out = sys.argv[1], sys.argv[2]
    jid = sys.argv[3] if len(sys.argv) > 3 else 'O:ordinary'
    ticks = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    if len(sys.argv) > 5 and sys.argv[5] == 'fx':
        from c1b1_t7.lang_fx import LangForceFX as LangForce
    elif len(sys.argv) > 5 and sys.argv[5] == 'fx2':
        from c1b1_t7.lang_fx2 import LangForceFX2 as LangForce
    job = next(j for j in json.loads(Path(inputs).read_bytes())['payload']['jobs'] if j['id'] == jid)
    res = dict(job=jid, ticks=ticks, backend=mm.libmp.BACKEND, force=LangForce.__name__, levels=[])
    with mm.workdps(DPS):
        q0, p0 = relative(job['raw'])
        mu = mm.mpf(MU.numerator) / MU.denominator
        for j in (0, 1):
            fp, fm = grid(j)
            pot = LangForce()
            t = FxTrackX(pot, q0, p0, j, 'chin', fp, fm, mu, 40, MU)
            prof = cProfile.Profile()
            t0 = time.process_time()
            prof.enable()
            t.run_to(ticks)
            prof.disable()
            dt = time.process_time() - t0
            s = io.StringIO()
            pstats.Stats(prof, stream=s).sort_stats('tottime').print_stats(25)
            # isolated pieces at the kick precision of this level
            kdps = max(60, int(fm * 0.30103) + 40)
            reps = 200
            with mm.workdps(kdps):
                q = t.q_mpf()
                r = mm.sqrt(q[0] ** 2 + q[1] ** 2)
                a = time.process_time()
                for k in range(reps):
                    pot._key = None
                    pot.jet(r)
                jet_us = 1e6 * (time.process_time() - a) / reps
                a = time.process_time()
                for k in range(reps):
                    mm.exp(-r)
                exp_us = 1e6 * (time.process_time() - a) / reps
            with mm.workdps(DPS):
                q1 = t.q_mpf()
                q2 = [q1[0] + mm.mpf('1e-3'), q1[1] - mm.mpf('1e-3')]
                a = time.process_time()
                for k in range(reps):
                    signed_angle(q1, q2)
                ang_us = 1e6 * (time.process_time() - a) / reps
            res['levels'].append(dict(j=j, grid=[fp, fm], kick_dps=kdps, substeps=t.substeps, cpu_s=dt,
                                      us_per_substep=1e6 * dt / t.substeps, force_evaluations=pot.evaluations,
                                      jet_us=jet_us, exp_us=exp_us, signed_angle_us=ang_us, profile=s.getvalue()))
            print(j, 'us/substep %.0f jet %.0f exp %.1f angle %.0f evals/substep %.2f' % (
                1e6 * dt / t.substeps, jet_us, exp_us, ang_us, pot.evaluations / t.substeps), flush=True)
    with open(out + '.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print(res['levels'][0]['profile'][:3500])


if __name__ == '__main__':
    main()
