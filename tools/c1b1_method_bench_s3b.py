"""Method bench S3b study (survey_only): Q2_fin error of KDK h = 40/20 on the orbiting potentials T5/T6.

  'panel' jobs: one Gauss-Kronrod 15 panel of the b integral (q2.panels) -> true and modified-flow sin^2(chi_fin)
  'spot'  jobs: real KDK h = 40 at b = b_orb (1 + rho), rho = +-1e-7/1e-8 and -0.5, against the M7 prediction
               (checks the M7 shortcut beyond the S3 range |rho| >= 1e-6)
Rows are appended to JSONL by the fail-closed runner (c1b1_method_bench.runner).
  python tools/c1b1_method_bench_s3b.py OUT.jsonl [WORKERS] [--only-probe]
"""
import os
import sys
import time

import mpmath as mm

from c1b1_method_bench import orbit, q2, quadref
from c1b1_method_bench.potentials import MU, LennardJones, Morse
from c1b1_method_bench.run import run
from c1b1_method_bench.runner import run_jobs

POTS = dict(T5_morse=Morse, T6_lennard_jones=LennardJones)
FRACS = ['0.3', '0.6', '0.9', '1.5']             # 1.5 E_max: no orbiting (control)
RHO_MIN = mm.mpf('1e-8')
WIDTH = mm.mpf('0.5')                            # panel width: s units near the orbit, bohr for the control
B_CAP = mm.mpf(18)
HS = (40, 20)
DPS = int(os.environ.get('S3B_DPS', '40'))       # quadref digits for S3b (pre-run probe: 40 vs 80, see plan)
SPOTS = [('0.3', '1e-8'), ('0.3', '-1e-8'), ('0.6', '1e-8'), ('0.6', '-1e-8'), ('0.9', '1e-8'), ('0.9', '-1e-8'),
         ('0.6', '1e-7'), ('0.6', '-1e-7'), ('0.6', '-0.5')]


def config(pot, frac):
    with mm.workdps(60):
        return q2.panels(frac, pot, B_CAP, RHO_MIN, WIDTH)


def jobs():
    out = []
    for name, cls in POTS.items():
        for f in FRACS:
            out += [('panel', name, f, k) for k in range(len(config(cls(), f)[2]))]
        out += [('spot', name, f, r) for f, r in SPOTS]
    return out


def one(job):
    kind, name, frac, arg = job
    t0 = time.perf_counter()
    pot = POTS[name]()
    quadref.DPS = DPS
    try:
        E, b_orb, pans = config(pot, frac)
        if kind == 'panel':
            side, a, b = pans[arg]
            nodes = []
            with mm.workdps(40):
                rule = q2.gk15(a, b)
            for x, wk, wg in rule:
                with mm.workdps(60):
                    bb, jac = q2.b_of(side, x, b_orb)
                n = q2.node(pot, E, bb, HS)
                nodes.append(dict(x=mm.nstr(x, 30), b=mm.nstr(bb, 30), jac=mm.nstr(jac, 30), wk=mm.nstr(wk, 30),
                                  wg=mm.nstr(wg, 30), sin2_true=mm.nstr(n['sin2_true'], 30),
                                  sin2={h: mm.nstr(v, 30) for h, v in n['sin2'].items()},
                                  d_sweep={h: mm.nstr(v, 20) for h, v in n['d_sweep'].items()}))
            row = dict(status='ok', side=side, a=mm.nstr(a, 20), b_hi=mm.nstr(b, 20), nodes=nodes)
        else:
            with mm.workdps(60):
                bb = b_orb * (1 + mm.mpf(arg))
                L = bb * mm.sqrt(2 * MU * E)
            k = run(pot, 'kdk', E, bb, 40, max_steps=2_000_000)
            row = dict(status=k['status'], steps=k.get('steps'))
            if k['status'] == 'ok':
                mod = quadref.kdk_modified(pot, MU, k['q0'], k['p0'], 40, k['r_exit'], time=False)
                true = quadref.reference(pot, MU, E, L, k['r_exit'], time=False)
                with mm.workdps(DPS):
                    pred = mod['sweep'] - true['sweep']
                row.update(d_sweep=k['d_sweep'], pred_d_sweep=float(pred), ratio=k['d_sweep'] / float(pred),
                           err_sweep=k['err_sweep'])
        row.update(E=mm.nstr(E, 30), b_orb=mm.nstr(b_orb, 30) if b_orb is not None else None)
    except Exception as exc:                     # recorded, never hidden
        row = dict(status='error', error=repr(exc)[:300])
    row.update(job=list(job), wall_s=time.perf_counter() - t0, dps=DPS)
    return row


def main():
    out = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 4
    js = jobs()
    if '--only-probe' in sys.argv:
        js = [j for j in js if j[0] == 'panel' and j[2] == '0.6' and j[3] in (0, 36, 37, 73)]
    run_jobs(one, js, out, workers=workers, label='S3b ')


if __name__ == '__main__':
    main()
