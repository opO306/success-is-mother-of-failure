"""C1-B1 drift comparison (designer 14th ed., follow-up): three drift rules under identical conditions. Measurement only.

  v1     round(r + p dt / m)               position FX(96,48)   (the retired contract v1)
  v2     r + round(p dt / m)               position FX(96,48)   (contract v2, the interim default)
  exact  r + p dt / m, nothing rounded     position exact (ExactPosition: every sub-grid remainder kept)
All three: momentum FX(64,48), J rounded once to it, the same frozen C1-A force, the same dt, the same initial states.
"ref" (long runs only) = exact positions + momentum FX(256,192): the rounding-free trajectory of the same integrator.

Parts (all recorded in fixtures/c1b1_drift_compare_v1.json):
  A accuracy      the 40 study-1 cases x dt 10/20/40 x 3 rules (observables compared with the 80-digit references
                  of study 2 by the tests; runs go through c1b1_dt_study.run_case)
  B invariance    translation (1 raw, 3 raw, 10^6 bohr + 1 raw), exchange, 90-degree rotation, and a hierarchical
                  local-frame change (shift all positions by a grid-aligned offset mid-run, shift back at the end)
  C reversibility forward N, flip momenta, forward N, flip -> start?
  D slow motion   free drift of one atom for 10^4 steps at small momenta; two atoms at rest at 40 / 200 / 1000 bohr
  E long runs     2*10^5 steps at dt = 40 of a radial (L = 0) and an orbiting (L != 0) bound pair: energy, Lz and
                  position deviation from "ref" at checkpoints
  F cost          reference step time per rule, impulse time vs position representation, native kernels (bench_state)
  G/H bits        the lattice the exact rule needs: for 40Ar at dt = 40, for more species, for other dt

Run: python -m a_reference.c1b1_drift_compare
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
from functools import reduce
from math import gcd, lcm
from multiprocessing import Pool
from pathlib import Path

import a_reference.c1b1_dt_study as S
import a_reference.c1b1_two_atom as C
from a_numeric import FixedPoint

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "fixtures" / "c1b1_drift_compare_v1.json"
POS, MOM, HPM = FixedPoint(96, 48), FixedPoint(64, 48), FixedPoint(256, 192)
EXACT = C.ExactPosition()
RULES = {"v1": (POS, MOM, "v1"), "v2": (POS, MOM, "v2"), "exact": (EXACT, MOM, "v2")}
RAW = Q(1, 1 << 48)
P_TIE = Q(4995297890462500, 1 << 48)          # p dt / m exactly half a raw unit at dt = 40
DT = Q(40)


def _register():
    for k, v in RULES.items():
        S.PROFILES[k] = v


# --- states -----------------------------------------------------------------------------------------------------

def _vec(v):
    return tuple(Q(x) for x in v)


def tie_state(ri=(-4, 0, 0), rj=(4, 1, 0)):
    """After the first half kick p_j = (P_TIE, 0, 0), p_i = -p_j: both atoms drift on an exact tie (E_rel ~ 8.9 De)."""
    ri, rj = _vec(ri), _vec(rj)
    J = tuple(MOM.to_exact(j) for j in C.impulse(tuple(b - a for a, b in zip(ri, rj)), DT / 2, MOM))
    pj = tuple(t - j for t, j in zip((P_TIE, Q(0), Q(0)), J))
    return {"r_i": ri, "p_i": tuple(-x for x in pj), "r_j": rj, "p_j": pj}


def far_tie_state():
    """1000 bohr apart: J rounds to 0 on the momentum grid, so p stays at +-P_TIE and EVERY drift is a tie."""
    return {"r_i": _vec((-500, 0, 0)), "p_i": (-P_TIE, Q(0), Q(0)), "r_j": _vec((500, Q(1, 2), 0)),
            "p_j": (P_TIE, Q(0), Q(0))}


def standard_state():
    g = lambda x: FixedPoint(64, 32).to_exact(FixedPoint(64, 32).from_exact(Q(x)))
    pj = (g(-3.1), g(0.8), g(0.25))
    return {"r_i": (g(-4.1), g(-0.7), g(0.3)), "p_i": tuple(-x for x in pj), "r_j": (g(4.3), g(0.9), g(-0.2)),
            "p_j": pj}


def orbit_state():
    """Bound, L != 0: R = 8 bohr, tangential momentum of a circular orbit plus a radial 0.05 a.u. (on the MOM grid)."""
    R = Q(8)
    F = C.force_high(R * R)                                      # < 0: attractive at 8 bohr
    pt = MOM.to_exact(MOM.from_exact(Q(math.isqrt(int(C.AR40_MASS_ME / 2 * R * -F * (1 << 96))), 1 << 48)))
    pj = (Q(1, 20), pt, Q(0))
    return {"r_i": (-R / 2, Q(0), Q(0)), "p_i": tuple(-x for x in pj), "r_j": (R / 2, Q(0), Q(0)), "p_j": pj}


def study_state(kind, **kw):
    st = S.scattering_state(kw["e"], kw["b"]) if kind == "scatter" else S.bound_state(kw["f"])
    return {k: st[k] for k in ("r_i", "p_i", "r_j", "p_j")}


def states():
    return {"tie": tie_state(), "far_tie": far_tie_state(), "standard": standard_state(),
            "bound_f0.3": study_state("bound", f=Q(3, 10)), "scatter_e1_b0.5": study_state("scatter", e=Q(1), b=Q(1, 2)),
            "orbit": orbit_state()}


def accepted(st) -> bool:
    try:
        C.new_run(POS, DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=MOM)
        return True
    except C.IntegratorDomainExceeded:
        return False


def make(rule, st, shift=Q(0), rot=False, swap=False, mom=None):
    pos, m, dr = RULES[rule]
    f = (lambda v: (v[1], -v[0], v[2])) if rot else (lambda v: v)
    tr = lambda v: tuple(x + shift for x in f(v))
    a = (tr(st["r_i"]), f(st["p_i"]), tr(st["r_j"]), f(st["p_j"]))
    if swap:
        a = (a[2], a[3], a[0], a[1])
    return C.new_run(pos, DT, *a, momentum_profile=mom or m, validated_only=False, drift=dr)


# --- B: invariances -------------------------------------------------------------------------------------------------

def _trace(run, n):
    """Relative trajectory, and how many drift components were exact ties (the drift momentum is p_after -+ J)."""
    out, ties = [], 0
    for _ in range(n):
        C.step(run)
        J = C.exact(run.mom, run.J_cache)
        pi = tuple(x + j for x, j in zip(C.exact(run.mom, run.atoms[0].p), J))
        pj = tuple(x - j for x, j in zip(C.exact(run.mom, run.atoms[1].p), J))
        for p in pi + pj:
            ties += (p * run.dt / C.AR40_MASS_ME * (1 << 48)).denominator == 2
        out.append((C.relative(run.pos, *run.atoms), run.atoms[0].p, run.atoms[1].p))
    return out, ties


def _dev(a, b):
    """max |difference| of the relative position over a trajectory, in raw 2^-48 units."""
    return float(max((abs(x - y) for s, t in zip(a, b) for x, y in zip(s[0], t[0])), default=Q(0)) * (1 << 48))


def invariance_task(args):
    rule, name, st, n = args
    base, ties = _trace(make(rule, st), n)
    res = {"rule": rule, "state": name, "steps": n, "ties_met": ties, "contract_accepts": accepted(st)}
    for label, sh in (("1raw", RAW), ("3raw", 3 * RAW), ("1e6+1raw", Q(10 ** 6) + RAW)):
        t, _ = _trace(make(rule, st, shift=sh), n)
        res[f"translation_{label}"] = {"identical": t == base, "max_dev_raw": _dev(t, base)}
    sw, _ = _trace(make(rule, st, swap=True), n)
    res["exchange"] = all(a[0] == tuple(-x for x in s[0]) and a[1] == s[2] and a[2] == s[1] for a, s in zip(base, sw))
    rt, _ = _trace(make(rule, st, rot=True), n)
    pos = RULES[rule][0]
    rr = lambda v: (v[1], -v[0], v[2])
    rraw = lambda v: (v[1], MOM.neg(v[0]), v[2])
    res["rotation_90"] = all(rr(a[0]) == r[0] and rraw(a[1]) == r[1] and rraw(a[2]) == r[2] for a, r in zip(base, rt))
    # hierarchical local frame: after k steps every position is re-expressed in a frame shifted by `off`, the run
    # continues there, and at the end the positions are shifted back -> must equal the unshifted run bit for bit
    for k in (0, 7):
        for label, off in (("1raw", RAW), ("1e6+3raw", Q(10 ** 6) + 3 * RAW)):
            ref = make(rule, st)
            run = make(rule, st)
            for _ in range(k):
                C.step(ref)
                C.step(run)
            o = pos.from_exact(off)
            move = lambda atoms, d: tuple(C.Atom(a.species, tuple(pos.add(x, d) for x in a.r), a.p) for a in atoms)
            run.atoms = move(run.atoms, o)
            for _ in range(n - k):
                C.step(ref)
                C.step(run)
            back = move(run.atoms, pos.neg(o))
            res[f"frame_change_at_{k}_{label}"] = back == ref.atoms
    return res


# --- C: reversibility ------------------------------------------------------------------------------------------------

def reversibility_task(args):
    rule, name, st, shift, n = args
    run = make(rule, st, shift=shift)
    start = run.atoms
    for _ in range(n):
        C.step(run)
    flip = lambda atoms: tuple(C.Atom(a.species, a.r, tuple(run.mom.neg(v) for v in a.p)) for a in atoms)
    run.atoms = flip(run.atoms)
    for _ in range(n):
        C.step(run)
    end = flip(run.atoms)
    pos = run.pos
    dev = max(abs(pos.to_exact(x) - pos.to_exact(y)) for a, b in zip(end, start) for x, y in zip(a.r, b.r))
    pdev = max(abs(x - y) for a, b in zip(end, start) for x, y in zip(a.p, b.p))
    return {"rule": rule, "state": name, "shift_raw": int(shift / RAW) if shift < 1 else str(shift), "steps": n,
            "exact_return": end == start, "max_pos_dev_raw": float(dev * (1 << 48)), "max_mom_dev_raw": int(pdev)}


# --- D: slow motion ---------------------------------------------------------------------------------------------------

SLOW_P_RAW = [1, 100, 910, 911, 1500, 10 ** 4, 10 ** 6, 4995297890462500]
N_FREE = 10 ** 4


def free_drift_task(args):
    rule, p_raw = args
    pos, mom, dr = RULES[rule]
    a = C.Atom("Ar40", tuple(pos.from_exact(x) for x in (Q(3) + RAW, Q(0), Q(0))), (p_raw, 0, 0))
    r0 = pos.to_exact(a.r[0])
    for _ in range(N_FREE):
        a = C._drift(pos, mom, a, DT, rule=dr)[0]
    exact_move = N_FREE * MOM.to_exact(p_raw) * DT / C.AR40_MASS_ME
    moved = pos.to_exact(a.r[0]) - r0
    return {"rule": rule, "p_raw": p_raw, "p_au": float(MOM.to_exact(p_raw)), "steps": N_FREE,
            "exact_move_raw": float(exact_move * (1 << 48)), "moved_raw": float(moved * (1 << 48)),
            "error_raw": float((moved - exact_move) * (1 << 48)), "stalled": moved == 0 and exact_move != 0}


def rest_pair_task(args):
    rule, R, n = args
    st = {"r_i": (-Q(R) / 2, Q(0), Q(0)), "p_i": (Q(0),) * 3, "r_j": (Q(R) / 2, Q(0), Q(0)), "p_j": (Q(0),) * 3}
    run = make(rule, st)
    first_move = first_p = None
    R0 = C.relative(run.pos, *run.atoms)[0]
    for k in range(1, n + 1):
        C.step(run)
        if first_p is None and any(run.atoms[1].p):
            first_p = k
        if first_move is None and C.relative(run.pos, *run.atoms)[0] != R0:
            first_move = k
    rel = C.relative(run.pos, *run.atoms)
    return {"rule": rule, "R_bohr": R, "steps": n, "first_step_with_momentum": first_p,
            "first_step_with_motion": first_move, "final_R_minus_R0_bohr": str(rel[0] - R0),
            "final_p_raw": run.atoms[1].p[0]}


# --- E: long runs --------------------------------------------------------------------------------------------------

N_LONG, EVERY = 200000, 5000


def long_task(args):
    rule, name, st = args
    t0 = time.time()
    if rule == "ref":
        run = C.new_run(EXACT, DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=HPM,
                        validated_only=False)
    else:
        run = make(rule, st)
    E0 = C.kinetic(run) + C.potential_high(sum((x * x for x in C.relative(run.pos, *run.atoms)), Q(0)))
    L0 = C.angular_momentum(run)[2]
    pts = []
    for k in range(1, N_LONG + 1):
        C.step(run)
        if k % EVERY == 0:
            q = C.relative(run.pos, *run.atoms)
            E = C.kinetic(run) + C.potential_high(sum((x * x for x in q), Q(0)))
            pts.append({"step": k, "rel": [str(x) for x in q], "dE_over_De": float((E - E0) / C.DE_CONTRACT),
                        "dLz": float(C.angular_momentum(run)[2] - L0),
                        "pos_denominator_bits": max(run.pos.to_exact(x).denominator.bit_length()
                                                    for a in run.atoms for x in a.r),
                        "pos_numerator_bits": max(abs(run.pos.to_exact(x).numerator).bit_length()
                                                  for a in run.atoms for x in a.r)})
    return {"rule": rule, "state": name, "steps": N_LONG, "points": pts, "seconds": round(time.time() - t0, 1)}


# --- F: cost -------------------------------------------------------------------------------------------------------

def step_cost_task(args):
    rule, n = args
    run = make(rule, standard_state())
    C.step(run)
    t0 = time.perf_counter()
    for _ in range(n):
        C.step(run)
    per_step = (time.perf_counter() - t0) / n
    rel = C.relative(run.pos, *run.atoms)
    t0 = time.perf_counter()
    for _ in range(20):
        C.impulse(rel, DT / 2, MOM)
    per_impulse = (time.perf_counter() - t0) / 20
    R2 = sum((x * x for x in rel), Q(0))
    return {"rule": rule, "steps": n, "ms_per_step": per_step * 1e3, "ms_per_impulse": per_impulse * 1e3,
            "R2_numerator_bits": R2.numerator.bit_length(), "R2_denominator_bits": R2.denominator.bit_length()}


def native_costs():
    """bench_state kernels: state-update ops per pair and bundle + one C1-A F evaluation, CPU (1 thread) and CUDA."""
    from a_numeric_native.harness import cuda_device_present, find_nvcc, find_vcvars
    from a_physics_native import bench_state as B
    out = {"note": "timings, 3 repeats; e2e uses the C1-A F(R) evaluator at a binary64 R proxy (see design doc 9.2)"}
    configs = [("v1", 3), ("v2", 2), ("v2", 3), ("v2", 4), ("exact", 5)]
    kinds = []
    if find_vcvars() is not None:
        kinds.append("cpu")
        if find_nvcc() is not None and cuda_device_present():
            kinds.append("cuda")
    for kind in kinds:
        exe = B.build(kind, tempfile.mkdtemp())
        for rule, limbs in configs:
            rows = []
            for _ in range(3):
                t = B.run(exe, "time", rule, limbs, 20000 if kind == "cpu" else 1 << 20, 20 if kind == "cpu" else 50)
                e = B.run(exe, "e2e", rule, limbs, 400 if kind == "cpu" else 1 << 14)
                rows.append({"time": dict(l.split() for l in t.strip().splitlines()), "e2e": e.strip()})
            out[f"{kind}_{rule}_{limbs}limbs"] = rows
    return out


# --- G/H: the lattice the exact rule needs ----------------------------------------------------------------------------

# Illustrative isotope masses in u (AME2020 values typed from memory -- NOT verified against the source; the growth of
# the lattice depends on how many decimal digits a mass has, not on its value). 40Ar is the C1-B1 contract value.
SPECIES_U = {"40Ar": "39.9623831237", "4He": "4.00260325413", "20Ne": "19.9924401762", "1H": "1.00782503223",
             "12C": "12", "14N": "14.00307400443", "16O": "15.99491461957", "23Na": "22.9897692820",
             "84Kr": "83.9114977282", "132Xe": "131.9041550856"}
M_E_U = Q("5.485799090441e-4")


def _qgcd(qs):
    """gcd of positive rationals: gcd(numerators) / lcm(denominators) -- the lattice they generate."""
    return Q(reduce(gcd, (q.numerator for q in qs)), reduce(lcm, (q.denominator for q in qs)))


def lattice(species, dts, mom_bits=48, pos_bits=48):
    """The finest position spacing an exact drift can produce: generated by the initial grid 2^-pos_bits and every
    displacement quantum 2^-mom_bits dt / m_X. Returned as the number of bits of 1 / spacing (not a power of 2)."""
    qs = [Q(1, 1 << pos_bits)]
    for sp in species:
        m = Q(SPECIES_U[sp]) / M_E_U
        for dt in dts:
            qs.append(Q(1, 1 << mom_bits) * Q(dt) / m)
    u = _qgcd(qs)
    return {"species": list(species), "dts": [str(Q(d)) for d in dts], "unit_denominator_bits": (1 / u).numerator.bit_length()
            if (1 / u).denominator == 1 else None, "one_over_unit": str(1 / u),
            "width_for_pm_2^47_bohr": 1 + 47 + math.ceil(math.log2(1 / u))}


def lattice_table():
    order = list(SPECIES_U)
    rows = [lattice(order[:k], [40]) for k in range(1, len(order) + 1)]
    dt_rows = [lattice(["40Ar"], d) for d in ([40], [40, 20, 10], [40, 80, 160], [40, Q(40, 3)], [40, Q(1, 10)],
                                             [40, Q(40, 3), Q(40, 7), Q(40, 11)], [Q(40 * k, 64) for k in range(1, 65)])]
    both = [lattice(order, [40, Q(40, 3)]), lattice(order, [Q(40 * k, 64) for k in range(1, 65)])]
    # the chosen masses are exact decimals: how much of the growth is the decimal digit count
    digits = {sp: len(v.split(".")[1]) if "." in v else 0 for sp, v in SPECIES_U.items()}
    return {"species_growth": rows, "dt_growth": dt_rows, "species_and_dt": both, "mass_decimal_digits": digits,
            "masses_u": SPECIES_U, "m_e_u": str(M_E_U), "masses_note": "illustrative, typed from memory (AME2020), "
            "not verified; 40Ar is the contract value"}


def exact_bits_c1b1():
    q = RAW * DT / C.AR40_MASS_ME
    u = _qgcd([RAW, q])
    return {"displacement_quantum": str(q), "lattice_unit": str(u), "one_over_unit_bits": (1 / u).numerator.bit_length(),
            "fraction_bits_equivalent": math.log2(1 / u), "width_for_pm_2^47_bohr": 1 + 47 + math.ceil(math.log2(1 / u)),
            "v1_v2_width": 96}


# --- main ----------------------------------------------------------------------------------------------------------

def _run(task, args):
    _register()
    return task(args)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _json_default(x):
    if isinstance(x, Q):
        return str(x)
    raise TypeError(type(x))


def main(procs: int = 11):
    t0 = time.time()
    st = states()
    rules = list(RULES)
    jobs = []
    for r in rules:                                   # long runs first (the slowest)
        for name in ("bound_f0.3", "orbit"):
            jobs.append((long_task, (r, name, st[name])))
    for name in ("bound_f0.3", "orbit"):
        jobs.append((long_task, ("ref", name, st[name])))
    cs = S.cases()
    cstates = [S.scattering_state(c["e"], c["b"]) if c["kind"] == "scatter" else S.bound_state(c["f"]) for c in cs]
    old = {r["case"]: r for r in json.loads(S.OUT.read_text(encoding="utf-8"))["references"]}
    for c, cst in zip(cs, cstates):
        nom = old[c["name"]].get("nominal", {})
        t_ref = float(nom.get("time", nom.get("two_periods", 4e5)))
        for dt in (10, 20, 40):
            for r in rules:
                jobs.append((S.run_case, (c, cst, dt, r, int(3 * t_ref / dt) + 200)))
    for r in rules:
        for name in ("tie", "far_tie", "standard", "bound_f0.3", "scatter_e1_b0.5", "orbit"):
            jobs.append((invariance_task, (r, name, st[name], 40)))
        for name, shift in (("tie", Q(0)), ("tie", RAW), ("far_tie", Q(0)), ("far_tie", RAW), ("standard", Q(0)),
                            ("bound_f0.3", Q(0)), ("orbit", Q(0))):
            for n in (1, 15, 300):
                jobs.append((reversibility_task, (r, name, st[name], shift, n)))
        for p in SLOW_P_RAW:
            jobs.append((free_drift_task, (r, p)))
        for R in (40, 200, 1000):
            jobs.append((rest_pair_task, (r, R, 400)))
    with Pool(procs) as pool:
        results = pool.starmap(_run, jobs)
        costs = pool.starmap(_run, [(step_cost_task, (r, 200)) for r in rules])   # after the load: less contention
    out = {"A_accuracy": [], "B_invariance": [], "C_reversibility": [], "D_free_drift": [], "D_rest_pair": [],
           "E_long": []}
    kinds = {long_task: "E_long", S.run_case: "A_accuracy", invariance_task: "B_invariance",
             reversibility_task: "C_reversibility", free_drift_task: "D_free_drift", rest_pair_task: "D_rest_pair"}
    for (task, _), res in zip(jobs, results):
        out[kinds[task]].append(res)
    native = native_costs()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "a_reference", "audit", "a_physics_native"],
                           capture_output=True, text=True, cwd=ROOT).stdout.strip()
    doc = {"format": "c1b1-drift-compare-v1", "contract": C.CONTRACT_VERSION, "dt": 40,
           "rules": {"v1": "round(r + p dt/m), POS FX(96,48)", "v2": "r + round(p dt/m), POS FX(96,48)",
                     "exact": "r + p dt/m exactly (ExactPosition)", "ref": "exact positions + momentum FX(256,192)"},
           "momentum": "FX(64,48)", "states": {k: {kk: [str(x) for x in vv] for kk, vv in v.items()} for k, v in st.items()},
           "states_accepted_by_contract": {k: accepted(v) for k, v in st.items()},
           "provenance": {"git_head": head, "uncommitted_changes_in_a_reference_audit_or_native": bool(dirty),
                          "code_sha256": {f: _sha(ROOT / f) for f in (
                              "a_reference/c1b1_two_atom.py", "a_reference/c1b1_dt_study.py",
                              "a_reference/c1b1_drift_compare.py", "a_physics_native/bench_state.hpp",
                              "a_physics_native/bench_state.py")}},
           **out, "F_step_cost": costs, "F_native": native, "G_exact_bits_c1b1": exact_bits_c1b1(),
           "H_lattice": lattice_table(), "seconds": round(time.time() - t0)}
    OUT.write_text(json.dumps(doc, indent=1, default=_json_default), encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
