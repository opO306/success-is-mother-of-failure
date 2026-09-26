"""C1-B1 momentum-precision comparison (designer 15th ed.). Measurement only -- it chooses nothing.

Position FX(96,48), drift v2 (the adopted candidate) for every run; the MOMENTUM representation varies:
  fx64_48    FX(64,48)    the current profile (J rounds to 0 beyond ~438 bohr)
  fx80_64    FX(80,64)    wider fraction, same integer range (+-32768 a.u.)
  fx96_80    FX(96,80)
  fx128_112  FX(128,112)
  carry      CarryMomentum: coarse FX(64,48) (what the drift moves with) + residual on 2^-111 (sub-grid impulses kept)
  ref        FX(256,192): the rounding-free reference of the same integrator (J cutoff ~1e8 bohr)
J is rounded once to each representation's own (finest) grid.

Parts (fixtures/c1b1_momentum_compare_v1.json):
  A accuracy      40 study cases x dt 10/20/40 x 5 candidates (tests compare with the 80-digit references)
  B cutoff        the implicit cutoff R_c (on-axis |J| = half a unit at dt = 40) per fraction width, and V(R_c)
  C far pairs     two atoms at rest at 100 ... 20000 bohr, 2000 steps: accumulated momentum and approach vs ref
  D far field     three scattering cases followed out to 2500 bohr: final relative-momentum direction vs ref
  E budget        upper bounds of the momentum error a vanishing / rounded impulse can cause, vs the C1-B1 claim
  F conservation  exact total momentum; exchange / 90-degree rotation / translation; 5*10^4-step energy
  G cost          reference step time per candidate; native kernels (bench_state mtime / me2e) CPU and CUDA

Run: python -m a_reference.c1b1_momentum_compare
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
from fractions import Fraction as Q
from multiprocessing import Pool
from pathlib import Path

import mpmath

import a_reference.c1b1_drift_compare as DC
import a_reference.c1b1_dt_study as S
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_momentum_compare_v1.json"
POS = FixedPoint(96, 48)
MOMS = {"fx64_48": FixedPoint(64, 48), "fx80_64": FixedPoint(80, 64), "fx96_80": FixedPoint(96, 80),
        "fx128_112": FixedPoint(128, 112), "carry": C.CarryMomentum(), "ref": FixedPoint(256, 192)}
FINE_BITS = {"fx64_48": 48, "fx80_64": 64, "fx96_80": 80, "fx128_112": 112, "carry": 111, "ref": 192}
CANDS = ["fx64_48", "fx80_64", "fx96_80", "fx128_112", "carry"]
DT = Q(40)
CRITERION = 1e-5                                   # C1-B1 claim: sweep angle / time relative error <= 1e-5 at dt = 40


def _register():
    for k, m in MOMS.items():
        S.PROFILES[k] = (POS, m, "v2")


def make(cand, st, shift=Q(0), rot=False, swap=False):
    f = (lambda v: (v[1], -v[0], v[2])) if rot else (lambda v: v)
    tr = lambda v: tuple(x + shift for x in f(v))
    a = (tr(st["r_i"]), f(st["p_i"]), tr(st["r_j"]), f(st["p_j"]))
    if swap:
        a = (a[2], a[3], a[0], a[1])
    return C.new_run(POS, DT, *a, momentum_profile=MOMS[cand], validated_only=False)


def rest_state(R):
    return {"r_i": (-Q(R) / 2, Q(0), Q(0)), "p_i": (Q(0),) * 3, "r_j": (Q(R) / 2, Q(0), Q(0)), "p_j": (Q(0),) * 3}


# --- B / E: cutoff and error budget (analytic, from the frozen C1-A model) -------------------------------------------

def cutoff(F: int) -> float:
    """Largest R (bohr) where the on-axis impulse |F(R)| dt/2 still exceeds half a 2^-F unit (bisection, M = 1024)."""
    half = Q(1, 1 << (F + 1))
    lo, hi = Q(20), Q(10 ** 9)
    while hi - lo > max(Q(1, 100), lo / 10 ** 6):
        mid = (lo + hi) / 2
        if abs(C.force_high(mid * mid, 1024)) * (DT / 2) > half:
            lo = mid
        else:
            hi = mid
    return float(lo)


def budget_row(name):
    """Bounds on the relative momentum error |dp| / p of one scattering event at relative energy E:
      tail  -- impulse lost beyond R_c on the way out AND in: <= 2 |V(R_c)| mu / p^2 = |V(R_c)| / E
               (|int_Rc^inf F dR| = |V(R_c)|; straight flight at the asymptotic speed is the slowest possible, since
               V < 0 there speeds the pair up -- so the bound holds; the angular term only shortens the path)
      round -- J rounded to 2^-F at most 2^-(F+1) per component per kick, 2 kicks per step, over the steps spent
               inside R_c (2 R_c / (v dt), v = p / mu): |dp| <= sqrt(3) 2^-F 2 R_c mu / (p dt) -> / p
               = sqrt(3) 2^-F R_c / (dt E)
    E_min = the smallest relative energy for which tail + round <= 1e-5 (the C1-B1 accuracy claim)."""
    F = FINE_BITS[name]
    Rc = cutoff(F)
    V = abs(C.potential_high(Q(Rc) ** 2, 1024))
    a = float(V)                                           # tail = a / E
    b = math.sqrt(3) * 2.0 ** -F * Rc / 40                 # round = b / E
    E_min = (a + b) / CRITERION
    return {"candidate": name, "fraction_bits": F, "R_cut_bohr": Rc, "R_cut_nm": Rc * 0.0529177210903,
            "abs_V_at_R_cut_hartree": a, "tail_coefficient_hartree": a, "round_coefficient_hartree": b,
            "E_min_hartree": E_min, "E_min_over_De": E_min / float(C.DE_CONTRACT),
            "E_min_note": "above E_min the bound tail + round <= 1e-5 holds; below it the bound fails (not the error)"}


# --- C: far pairs -----------------------------------------------------------------------------------------------

FAR_R = [100, 200, 438, 1000, 1872, 5000, 7567, 20000]
N_FAR = 2000


def far_task(args):
    cand, R = args
    run = make(cand, rest_state(R))
    R0 = C.relative(POS, *run.atoms)[0]
    first_move = None
    for k in range(1, N_FAR + 1):
        C.step(run)
        if first_move is None and C.relative(POS, *run.atoms)[0] != R0:
            first_move = k
    p = C.exact(run.mom, run.atoms[1].p)[0]
    pd = C.drift_momentum(run.mom, run.atoms[1].p)[0]
    return {"candidate": cand, "R_bohr": R, "steps": N_FAR, "p_j_x": str(p), "p_j_x_drift": str(pd),
            "approach_bohr": str(C.relative(POS, *run.atoms)[0] - R0), "first_step_with_motion": first_move,
            "dP": [str(x) for x in C.total_momentum(run)]}


# --- D: far field -----------------------------------------------------------------------------------------------

FAR_FIELD = [(Q(1), Q(1, 2)), (Q(1), Q(1)), (Q(10), Q(1))]
R_OUT = 2500


def far_field_task(args):
    cand, e, b = args
    t0 = time.time()
    st = S.scattering_state(e, b)
    run = make(cand, {k: st[k] for k in ("r_i", "p_i", "r_j", "p_j")})
    passed, prev, at20, n = False, None, None, 0
    while True:
        C.step(run)
        n += 1
        q = C.relative(POS, *run.atoms)
        R2 = sum((x * x for x in q), Q(0))
        if prev is not None and R2 > prev:
            passed = True
        prev = R2
        if passed and at20 is None and R2 >= 400:
            at20 = C.exact(run.mom, run.atoms[1].p)
        if passed and R2 >= R_OUT ** 2:
            break
    p = C.exact(run.mom, run.atoms[1].p)
    ang = lambda v: mpmath.atan2(mpmath.mpf(v[1].numerator) / v[1].denominator, mpmath.mpf(v[0].numerator) / v[0].denominator)
    mpmath.mp.dps = 40
    return {"candidate": cand, "e": str(e), "b": str(b), "steps": n, "R_out": R_OUT,
            "angle_at_20": mpmath.nstr(ang(at20), 30), "angle_at_out": mpmath.nstr(ang(p), 30),
            "p_out": [str(x) for x in p], "dP": [str(x) for x in C.total_momentum(run)],
            "seconds": round(time.time() - t0, 1)}


# --- F: conservation and invariance ---------------------------------------------------------------------------------

def invariance_task(args):
    cand, name, st, n = args
    mom = MOMS[cand]

    def trace(run):
        out = []
        for _ in range(n):
            C.step(run)
            out.append((C.relative(POS, *run.atoms), run.atoms[0].p, run.atoms[1].p))
        return out
    base = trace(make(cand, st))
    res = {"candidate": cand, "state": name, "steps": n}
    for label, sh in (("1raw", Q(1, 1 << 48)), ("1e6+1raw", Q(10 ** 6) + Q(1, 1 << 48))):
        res[f"translation_{label}"] = trace(make(cand, st, shift=sh)) == base
    sw = trace(make(cand, st, swap=True))
    res["exchange"] = all(a[0] == tuple(-x for x in s[0]) and a[1] == s[2] and a[2] == s[1] for a, s in zip(base, sw))
    rt = trace(make(cand, st, rot=True))
    rr = lambda v: (v[1], -v[0], v[2])
    rraw = lambda v: (v[1], mom.neg(v[0]), v[2])
    res["rotation_90"] = all(rr(a[0]) == r[0] and rraw(a[1]) == r[1] and rraw(a[2]) == r[2] for a, r in zip(base, rt))
    run = make(cand, st)
    for _ in range(n):
        C.step(run)
    res["total_momentum_exact_zero"] = C.total_momentum(run) == (0, 0, 0)
    res["action_reaction_raw"] = run.atoms[0].p == tuple(mom.neg(v) for v in run.atoms[1].p)
    return res


N_LONG, EVERY = 50000, 2500


def long_task(args):
    cand, name, st = args
    t0 = time.time()
    run = make(cand, st)
    E0 = C.kinetic(run) + C.potential_high(sum((x * x for x in C.relative(POS, *run.atoms)), Q(0)))
    pts = []
    for k in range(1, N_LONG + 1):
        C.step(run)
        if k % EVERY == 0:
            q = C.relative(POS, *run.atoms)
            E = C.kinetic(run) + C.potential_high(sum((x * x for x in q), Q(0)))
            pts.append({"step": k, "rel": [str(x) for x in q], "dE_over_De": float((E - E0) / C.DE_CONTRACT)})
    return {"candidate": cand, "state": name, "points": pts, "seconds": round(time.time() - t0, 1)}


# --- G: cost ---------------------------------------------------------------------------------------------------

def step_cost_task(args):
    cand, n = args
    run = make(cand, DC.standard_state())
    C.step(run)
    t0 = time.perf_counter()
    for _ in range(n):
        C.step(run)
    return {"candidate": cand, "ms_per_step": (time.perf_counter() - t0) / n * 1e3}


def native_costs():
    from a_numeric_native.harness import cuda_device_present, find_nvcc, find_vcvars
    from a_physics_native import bench_state as B
    out = {"note": "position FX(96,48) + drift v2; mtime = ns per pair (drift, kick, bundle = drift+dr+R2+kick); "
                   "me2e = bundle + one C1-A F(R) evaluation at a binary64 R proxy; 3 repeats"}
    kinds = []
    if find_vcvars() is not None:
        kinds.append("cpu")
        if find_nvcc() is not None and cuda_device_present():
            kinds.append("cuda")
    for kind in kinds:
        exe = B.build(kind, tempfile.mkdtemp())
        for k in B.MOM_KINDS:
            rows = []
            for _ in range(3):
                t = B.run(exe, "mtime", k, 20000 if kind == "cpu" else 1 << 20, 20 if kind == "cpu" else 50)
                e = B.run(exe, "me2e", k, 400 if kind == "cpu" else 1 << 14)
                rows.append({"time": dict(l.split() for l in t.strip().splitlines()), "e2e": e.strip()})
            out[f"{kind}_{k}"] = rows
    return out


# --- main ----------------------------------------------------------------------------------------------------

def _run(item):
    key, task, args = item
    _register()
    return key, task.__name__, task(args)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


PARTIAL = ROOT / "runs" / "c1b1_momentum_compare_partial.jsonl"     # runs/ is outside Git
CODE_FILES = ("a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py", "a_reference/c1b1_drift_compare.py",
              "a_reference/c1b1_momentum_compare.py", "a_physics_native/bench_mom.hpp",
              "a_physics_native/bench_mom_io.hpp", "a_physics_native/bench_state.cpp",
              "a_physics_native/bench_state.cu", "a_physics_native/bench_state.py")
SECTION = {"far_field_task": "D_far_field", "long_task": "F_long", "run_case": "A_accuracy", "far_task": "C_far_pairs",
           "invariance_task": "F_invariance", "step_cost_task": "G_step_cost"}


def _jobs():
    """(key, task, args), longest first (one job per worker at a time -- no chunking)."""
    st = {"standard": DC.standard_state(), "orbit": DC.orbit_state(), "bound_f0.3": DC.study_state("bound", f=Q(3, 10)),
          "rest_1000": rest_state(1000), "far_tie": DC.far_tie_state()}
    heavy = ["ref", "carry", "fx128_112", "fx96_80", "fx80_64", "fx64_48"]
    jobs = [(f"far_field|{c}|{e}|{b}", far_field_task, (c, e, b)) for e, b in FAR_FIELD for c in heavy]
    jobs.sort(key=lambda j: (j[2][1] != 1, heavy.index(j[2][0])))           # E = 1 De first (the longest)
    jobs += [(f"long|{c}|{n}", long_task, (c, n, st[n])) for c in heavy for n in ("bound_f0.3", "orbit")]
    cs = S.cases()
    cstates = [S.scattering_state(c["e"], c["b"]) if c["kind"] == "scatter" else S.bound_state(c["f"]) for c in cs]
    old = {r["case"]: r for r in json.loads(S.OUT.read_text(encoding="utf-8"))["references"]}
    acc = []
    for c, cst in zip(cs, cstates):
        nom = old[c["name"]].get("nominal", {})
        t_ref = float(nom.get("time", nom.get("two_periods", 4e5)))
        for dt in (10, 20, 40):
            for cand in CANDS:
                cap = int(3 * t_ref / dt) + 200
                acc.append((cap, (f"acc|{c['name']}|{dt}|{cand}", S.run_case, (c, cst, dt, cand, cap))))
    jobs += [j for _, j in sorted(acc, key=lambda x: -x[0])]
    for c in CANDS + ["ref"]:
        jobs += [(f"far|{c}|{R}", far_task, (c, R)) for R in FAR_R]
        jobs += [(f"inv|{c}|{n}", invariance_task, (c, n, st[n], 40)) for n in ("standard", "orbit", "rest_1000", "far_tie")]
    return jobs


def _load_partial(head, code):
    done = {}
    if PARTIAL.exists():
        lines = PARTIAL.read_text(encoding="utf-8").splitlines()
        if lines and json.loads(lines[0]) == {"git_head": head, "code": code}:
            for l in lines[1:]:
                r = json.loads(l)
                done[r["key"]] = r
        else:
            PARTIAL.unlink()                                   # made by other code: never mixed in
    if not PARTIAL.exists():
        PARTIAL.parent.mkdir(parents=True, exist_ok=True)
        PARTIAL.write_text(json.dumps({"git_head": head, "code": code}) + "\n", encoding="utf-8")
    return done


def main(procs: int = 11):
    t0 = time.time()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit", "a_physics_native"],
                           capture_output=True, text=True, cwd=ROOT).stdout.strip()
    code = {f: _sha(ROOT / f) for f in CODE_FILES}
    native = native_costs()                                    # first, on an idle machine; fails early if broken
    print(f"native costs done in {time.time() - t0:.0f}s", flush=True)
    done = _load_partial(head, code)
    todo = [j for j in _jobs() if j[0] not in done]
    todo += [(f"cost|{c}", step_cost_task, (c, 200)) for c in CANDS + ["ref"] if f"cost|{c}" not in done]
    print(f"{len(done)} jobs already recorded, {len(todo)} to run", flush=True)
    with Pool(procs) as pool, PARTIAL.open("a", encoding="utf-8") as f:
        for i, (key, name, res) in enumerate(pool.imap_unordered(_run, todo, chunksize=1)):
            f.write(json.dumps({"key": key, "task": name, "result": res}) + "\n")
            f.flush()
            done[key] = {"key": key, "task": name, "result": res}
            if i % 25 == 0:
                print(f"  {i + 1}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
        budget = pool.map(budget_row, CANDS + ["ref"])
    out = {v: [] for v in SECTION.values()}
    order = [j[0] for j in _jobs()] + [f"cost|{c}" for c in CANDS + ["ref"]]
    for key in order:
        r = done[key]
        out[SECTION[r["task"]]].append(r["result"])
    doc = {"format": "c1b1-momentum-compare-v1", "contract": C.CONTRACT_VERSION, "dt": 40, "position": POS.name,
           "drift": "v2", "candidates": {k: m.name for k, m in MOMS.items()}, "fine_bits": FINE_BITS,
           "criterion": CRITERION,
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_audit_or_native": bool(dirty),
                          "code_sha256": code},
           **out, "B_E_budget": budget, "G_native": native, "seconds_this_session": round(time.time() - t0)}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
