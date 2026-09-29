"""Runtime wrapper V0 end-to-end survey (survey_only), evidence for runs/.

A  cap-128 rehearsal on the three whole trajectories of the witness prototype (1,640 / 5,775 / 21,056 steps): every step
   under the wrapper equals the plain full-cap run bit for bit; witness uses == the plain run's 256-bit decisions.
B  a REAL stop at the executor's own cap 16384 inside a real step: the relative position and the kick interval are the
   synthetic 2^-17000 near-tie (dt = 2 dt_kick, a 17,600-bit rational), so the step's first impulse is undecidable
   within 16384 bits. The wrapper must prove, re-verify from bytes, re-run the step from its start and end with a state
   whose first kick used exactly the mpmath-constructed raw. Both sides of the boundary. The run is built with
   validated_only=False (a synthetic stress state, not a physics claim); checker limits and Python's int/str digit limit
   are raised because the synthetic dt_kick has ~5,300 digits (real runtime inputs have dt = 40).
"""
import json
import sys
import time
from fractions import Fraction as Q
from pathlib import Path

import a_reference.c1b1_exact_impulse_checker_v2 as K2
import a_reference.c1b1_exact_impulse_crosscheck as XC
import a_reference.c1b1_runtime_wrapper as RW


def _case_a(case):
    import a_reference.c1b1_runtime_local_witness as W
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    e, bf, n = case
    st = X.canonical(e, bf * X.RE)

    def mk():
        return C.new_run(X.POS, X.DT, st["r_i"], st["p_i"], st["r_j"], st["p_j"], momentum_profile=X.MOM)
    t0 = time.time()
    ref, tel = mk(), X.Telemetry()
    refs = [W._raw(ref)]
    with X.instrumented(tel):
        for _ in range(n):
            C.step(ref)
            refs.append(W._raw(ref))
    t_plain = time.time() - t0
    run, states, statuses, uses = mk(), None, {}, 0
    states = [W._raw(run)]
    t0 = time.time()
    with W.precision_cap(128):
        for _ in range(n):
            o = RW.step(run)
            statuses[o.status] = statuses.get(o.status, 0) + 1
            uses += len(o.witnesses)
            if not o.advanced:
                break
            states.append(W._raw(run))
    return {"case": [str(e), str(bf), n], "equal_every_step": states == refs, "steps": len(states) - 1,
            "statuses": statuses, "witness_uses": uses, "plain_256_bit_decisions": tel.decisions.get(256, 0),
            "seconds_plain": round(t_plain, 1), "seconds_wrapped": round(time.time() - t0, 1)}


def _case_b(sign):
    sys.set_int_max_str_digits(0)
    import a_reference.c1b1_runtime_local_witness as W
    import a_reference.c1b1_stress_survey as X
    import a_reference.c1b1_two_atom as C
    dr0 = XC._dr(4.4, (0.6, 0.6, 0.5))
    _, dr, dt_kick, expected = XC.near_tie_item(dr0, 0, 17000, sign, dps=5700, dt_bits=17600)
    z = (Q(0),) * 3
    p = (Q(3), Q(-1), Q(2))                                   # atoms move, so the post-drift impulse is an ordinary one

    def mk():
        return C.new_run(X.POS, 2 * dt_kick, z, tuple(-x for x in p), tuple(Q(v, 1 << 48) for v in dr), p,
                         momentum_profile=X.MOM, validated_only=False)
    out = {"sign": sign, "expected_raw": str(expected)}
    run = mk()
    t0 = time.time()
    try:
        C.step(mk())
        out["plain_executor"] = "decided (unexpected)"
    except C.ReferenceUndecided:
        out["plain_executor"] = "ReferenceUndecided at cap 16384 (%.1fs)" % (time.time() - t0)
    cfg = RW.Config(limits=K2.Limits(digits_max=10 ** 5, bits_max=10 ** 8, seconds_max=3000))
    before = W._raw(run)
    t0 = time.time()
    o = RW.step(run, cfg)
    out.update({"status": o.status, "reason": o.reason, "seconds": round(time.time() - t0, 1),
                "witnesses": o.witnesses, "stops": len(o.stops)})
    if o.advanced:
        # the first kick of the step used the witness: reconstruct it from the stored state
        i, j = run.atoms
        out["witness_raw_equals_expected"] = bool(o.witnesses and o.witnesses[0]["raw"] == expected)
        out["t_steps"] = run.t_steps
        out["state_changed"] = W._raw(run) != before
    default = RW.step(mk())
    out["default_limits"] = {"status": default.status, "reason": default.reason}
    return out


def main(out_dir, workers=3):
    import concurrent.futures as cf
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases = ((Q(9), Q(1, 2), 1640), (Q(1, 2), Q(1, 2), 5775), (Q(1, 10), Q(2), 21056))
    with cf.ProcessPoolExecutor(workers) as pool:
        a = list(pool.map(_case_a, cases))
    for r in a:
        print("A", json.dumps(r), flush=True)
    with cf.ProcessPoolExecutor(2) as pool:
        b = list(pool.map(_case_b, (1, -1)))
    for r in b:
        print("B", json.dumps({k: v for k, v in r.items() if k != "witnesses"}), flush=True)
        for w in r.get("witnesses", []):
            print("  witness", json.dumps({k: w[k] for k in ("raw", "certificate_bytes", "certificate_sha256", "prover")}),
                  flush=True)
    (out / "summary.json").write_text(json.dumps({"A": a, "B": b, "kind": "survey_only"}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
