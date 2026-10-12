"""Information-only probe (not a world run): cost of ONE direct-integration 'dot' and the size of a distant atom's potential."""
import json, time, sys
import mpmath as mm
sys.path.insert(0, '/root/t7pkg')
from c1b1_t7.lang import reference_potential
from c1b1_t7.reference import scatter_many
from c1b1_t7.state import MU, relative
from c1b1_method_bench.ladder2 import DPS
V = reference_potential()
with mm.workdps(30):
    for r in ['7.1', '20', '40', '65', '100']:
        print('V(%s) = %s Eh' % (r, mm.nstr(V(mm.mpf(r)), 6)), flush=True)
    print('kT(300K) = %s Eh' % mm.nstr(mm.mpf(300) / mm.mpf('315775.02480407'), 6), flush=True)
jobs = {j['id']: j for j in json.load(open('/root/t7pkg/docs/active/C1B1_T7_INPUTS_V0.json'))['payload']['jobs']}
rows = {}
for l in open('/root/t7pkg/t7_rows_all.jsonl'):
    r = json.loads(l); rows[r['job']['id']] = r
for jid in ['H:45:0', 'O:ordinary', 'S:1/2:-1e-8', 'S:9/10:-1e-10']:
    with mm.workdps(DPS):
        q0, p0 = relative(jobs[jid]['raw'])
        mu = mm.mpf(MU.numerator) / MU.denominator
    re_ = rows[jid]['out_base']['r']
    for check in (False, True):
        t = time.process_time()
        x = scatter_many(V, mu, q0, p0, [re_], dps=40, check=check)
        dt = time.process_time() - t
        same = x['exits'][0]['sweep'][:30] == rows[jid]['out_base']['ref_sweep'][:30]
        print(jid, 'check' if check else 'single', 'cpu %.1f s' % dt, 'pen_T7 %.0f s' % rows[jid]['pen_cpu_s'],
              'ref_T7 %.1f s' % rows[jid]['ref_cpu_s'], 'same30', same, flush=True)
