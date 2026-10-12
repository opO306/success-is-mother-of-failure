"""Cost plan C1 / C1.1: fixed-point Lang jets (c1b1_t7.lang_fx, lang_fx2) agree with the mpmath jet and give
bit-identical tracks."""
import importlib.util
import json
from pathlib import Path

import mpmath as mm
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _pes():
    from c1b1_t7.lang import pes_path
    if not pes_path().exists():
        pytest.fail(f'Lang PES file not found at {pes_path()} (set C1B1_LANG_PES); this test must not be skipped')


RS = [mm.mpf(3) * (mm.mpf(10) ** (mm.mpf(k) / 40)) for k in range(41)]           # 3 ... 30 bohr, log grid


def _cls(name):
    if name == 'fx2':
        from c1b1_t7.lang_fx2 import LangForceFX2
        return LangForceFX2
    from c1b1_t7.lang_fx import LangForceFX
    return LangForceFX


@pytest.mark.parametrize('force', ['fx', 'fx2'])
@pytest.mark.parametrize('dps', [60, 68, 77])
def test_fixed_point_jet_matches_mpmath_jet(dps, force):
    """|FX - exact| <= 2^-(W - 5) max(1, |value|), W = working precision bits (cost plan section 4.1)."""
    _pes()
    from c1b1_t7.lang import LangForce
    ref, fx = LangForce(), _cls(force)()
    for r in RS:
        with mm.workdps(dps):
            rr = +r
            W = mm.mp.prec
            got = fx.jet(rr)
        with mm.workdps(dps + 60):
            want = ref.jet(rr)
            for g, w in zip(got, want):
                assert abs(g - w) <= mm.ldexp(max(1, abs(w)), -(W - 5)), (mm.nstr(rr, 8), dps)


@pytest.mark.parametrize('force', ['fx', 'fx2'])
def test_fixed_point_cache_respects_precision(force):
    _pes()
    F = _cls(force)()
    with mm.workdps(20):
        a = F.dV(mm.mpf(7))
    with mm.workdps(60):
        b = F.dV(mm.mpf(7))
        c = F.d2V(mm.mpf(7))
        same = F.jet(mm.mpf(7))[2]           # inside the 60-digit block: run 1 compared at 53 bits (a new evaluation)
    assert F.evaluations == 2 and a != b and c == same


@pytest.mark.parametrize('j', [0, 1])
def test_tracks_are_bit_identical(j):
    """200 ticks of the T7 O:ordinary start on the M10 level-j grid: same raw state with all three jets."""
    _pes()
    from c1b1_method_bench.ladder2 import DPS
    from c1b1_method_bench.pen import grid
    from c1b1_t7.ladder import FxTrackX
    from c1b1_t7.lang import LangForce
    from c1b1_t7.lang_fx import LangForceFX
    from c1b1_t7.lang_fx2 import LangForceFX2
    from c1b1_t7.state import MU, relative
    raw = next(r for r in json.loads((ROOT / 'docs/active/C1B1_O1_INPUTS_V1.json').read_bytes())['payload']['inputs']
               if r['id'] == 'ordinary')['raw']
    fp, fm = grid(j)
    with mm.workdps(DPS):
        q0, p0 = relative(raw)
        mu = mm.mpf(MU.numerator) / MU.denominator
        out = []
        for cls in (LangForce, LangForceFX, LangForceFX2):
            t = FxTrackX(cls(), q0, p0, j, 'chin', fp, fm, mu, 40, MU)
            t.run_to(200)
            out.append((t.qr, t.pr_, t.sweep))
    assert out[0] == out[1] == out[2]


def test_replay_comparison_ignores_only_verification_fields():
    spec = importlib.util.spec_from_file_location('rp', ROOT / 'tools/c1b1_pen_fx_replay.py')
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    st = dict(tick=3, q_raw=['1', '2'], err_sweep=1e-12, ref_sweep='1')
    a = dict(status='accepted', j_out=1, level0=st, pairs=[dict(j=0, C_state=st, est_step_sweep='1e-10')],
             track_cost=[dict(j=0, extra=0, substeps=5, cpu_s=1.0)], world_kdk=dict(st, cpu_s=2.0))
    b = json.loads(json.dumps(a))
    b['level0']['err_sweep'] = 9.0
    b['track_cost'][0]['cpu_s'] = 7.0
    assert rp.diff_paths(rp.world(a), rp.world(b)) == []
    b['pairs'][0]['C_state']['q_raw'][1] = '3'
    assert rp.diff_paths(rp.world(a), rp.world(b)) == ['.pairs[0].C_state.q_raw[1]']
    b = json.loads(json.dumps(a))
    b['track_cost'][0]['substeps'] = 6
    assert rp.diff_paths(rp.world(a), rp.world(b)) == ['.track_substeps[0][2]']
