"""Independent checker of GPU_ONE_STEP_V1 (protocol 'checker'). Imports none of one_step, campaign, pv_host or any
GPU code. Its own literal forces loop and KDK use mpmath iv objects (the runner uses raw mpi primitives), the frozen
RwForce, K.domain, K.H, K.CDT, K.endpoints_key and K.decide.

    python -m experiments.gpu_one_step_v1.checker DIR
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

from mpmath import iv

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/active/gpu_one_step_v1/states.json.gz"
BUNDLE_SHA_FILE = ROOT / "docs/active/gpu_one_step_v1/states.json.gz.sha256"
EV = "rw:R1+R2"
_CACHE = {}


def _end(e):
    s, h, x, bc = e
    m = int(h, 16)
    return (0, 0, 0, 0) if m == 0 else (s, m, x, bc)


def _rows(rows):
    return None if rows is None else [[(_end(e[0]), _end(e[1])) for e in r] for r in rows]


def _force(p):
    if ("force", p) not in _CACHE:
        from experiments.rewrite_pilot_a3 import adapter as AD
        from experiments.rewrite_pilot_a3 import rwforce as RW
        AD.prepare(EV)
        iv.prec = p
        _CACHE[("force", p)] = RW.RwForce(AD._PLAN)
    return _CACHE[("force", p)]


def my_forces(q, p):
    """(kind or 'OK', first stop pair, F as iv rows)."""
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    force = _force(p)
    iv.prec = p
    h, zero = LI.c(K.H), LI.c(Fraction(0))
    n = len(q)
    F = [[zero] * 3 for _ in range(n)]
    pid = 0
    for i in range(n):
        for j in range(i + 1, n):
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
            st = K.domain(r2)
            if st != K.PROVEN:
                return "DOMAIN_STOP_" + st, pid, None
            try:
                g = force(r2)
            except K.DomainStop as e:
                return "DOMAIN_STOP_" + e.kind, pid, None
            for k in range(3):
                t = (h * g) * d[k]
                F[j][k] = F[j][k] + t
                F[i][k] = F[i][k] - t
            pid += 1
    return "OK", None, F


def my_step(q_raw, p_raw, p):
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    iv.prec = p
    q = [[iv.make_mpf(x) for x in r] for r in q_raw]
    pm = [[iv.make_mpf(x) for x in r] for r in p_raw]
    cdt = LI.c(K.CDT)
    raw = lambda rows: None if rows is None else [[x._mpi_ for x in r] for r in rows]   # noqa: E731
    out = {"F0": None, "p_half": None, "q1": None, "F1": None, "p1": None, "status": None, "stop_stage": None,
           "stop_pair": None, "endpoints_key": None, "decide": None}
    st, pid, F0 = my_forces(q, p)
    if st != "OK":
        out.update(status=st, stop_stage="F0", stop_pair=pid)
        return out
    ph = [[pm[a][k] + F0[a][k] for k in range(3)] for a in range(len(q))]
    q1 = [[q[a][k] + ph[a][k] * cdt for k in range(3)] for a in range(len(q))]
    out.update(F0=raw(F0), p_half=raw(ph), q1=raw(q1))
    st, pid, F1 = my_forces(q1, p)
    if st != "OK":
        out.update(status=st, stop_stage="F1", stop_pair=pid)
        return out
    p1 = [[ph[a][k] + F1[a][k] for k in range(3)] for a in range(len(q))]
    out.update(F1=raw(F1), p1=raw(p1), status="OK")
    qv, pv = [x for r in q1 for x in r], [x for r in p1 for x in r]
    out["endpoints_key"] = K.endpoints_key(qv + pv)
    try:
        cells = K.decide(qv, pv)
        out["decide"] = "UNDECIDED_AT_PRECISION" if cells is None else cells
    except K.OutOfRange:
        out["decide"] = "OUT_OF_RANGE"
    return out


def check(d, bundle_path=BUNDLE, bundle_sha_file=BUNDLE_SHA_FILE, expect_layouts=True):
    d = Path(d)
    issues, counts = [], {}

    def ok(name, cond, detail=""):
        counts.setdefault(name, [0, 0])
        counts[name][0 if cond else 1] += 1
        if not cond:
            issues.append(f"{name}: {detail}")

    raw = Path(bundle_path).read_bytes()
    sealed = Path(bundle_sha_file).read_text(encoding="utf-8").strip()
    ok("bundle_hash_matches_sealed_file", hashlib.sha256(raw).hexdigest() == sealed)
    b = json.loads(gzip.decompress(raw))
    for t in b["trajectories"]:
        ok("bundle_trajectory_equals_reference", t["equals_reference"], f"N{t['N']}")
    sts = {("main", x["id"]): x for x in b["main"]}
    sts.update({("test", x["id"]): x for x in b["test_only"]})
    envf = d / "env.json"
    if envf.exists():
        env = json.loads(envf.read_text(encoding="utf-8"))
        ok("seal_clean", env["status_porcelain"] == "" and not env["sealed_sources_dirty"], env["status_porcelain"][:200])
        ok("env_bundle_sha", env["bundle_sha256"] == sealed)

    def ref(key, x):
        if key not in _CACHE:
            o = my_step(_rows(x["q"]), _rows(x["p_mom"]), x["p"])
            _CACHE[key] = o
            if x.get("role", "MAIN") == "MAIN":
                ok("own_F0_equals_recorded_F_s", o["F0"] == _rows(x["F"]), str(key))
                ok("own_step_equals_recorded_next_state", (o["q1"], o["p1"], o["F1"]) ==
                   (_rows(x["next_q"]), _rows(x["next_p_mom"]), _rows(x["next_F"])), str(key))
            else:
                stage, kind, pid = x["cpu_outcome"]
                want = ("OK", None, None) if stage == "OK" else ("DOMAIN_STOP_" + kind, stage, pid)
                ok("own_probe_equals_bundle_outcome", (o["status"], o["stop_stage"], o["stop_pair"]) == want, str(key))
        return _CACHE[key]

    stats = {"steps_exact": 0, "steps_mismatch": 0, "stops_exact": 0, "stops_mismatch": 0, "refused": 0, "runs": 0}
    layouts = {}
    for f in sorted((d / "runs").glob("*.json.gz")):
        r = json.loads(gzip.decompress(f.read_bytes()))
        key = (r["state_kind"], r["state_id"])
        x = sts.get(key)
        ok("run_state_known", x is not None, f.name)
        if x is None:
            continue
        stats["runs"] += 1
        ok("run_settings_clean", r["fault"] == 0 and r["pvfault"] == 0 and r["g0fault"] == 0 and r["work_limbs"] == 16
           and r["upload_p"] == x["p"] and r["p"] == x["p"], f.name)
        o = ref(key, x)
        q0, p0 = _rows(x["q"]), _rows(x["p_mom"])
        ok("C0_runner_inputs_equal_bundle", (_rows(r["echo_q0"]), _rows(r["echo_p0"])) == (q0, p0), f.name)
        ok("C0_gpu_position_echo_q0", _rows(r["gpu_echo_q0"]) == q0, f.name)
        if r["status"].startswith("REFUSED"):
            stats["refused"] += 1
            continue
        ok("status_equal", (r["status"], r["stop_stage"], r["stop_pair"]) == (o["status"], o["stop_stage"], o["stop_pair"]),
           f"{f.name}: gpu {(r['status'], r['stop_stage'], r['stop_pair'])} cpu {(o['status'], o['stop_stage'], o['stop_pair'])}")
        for c, name in (("F0", "C1_F0"), ("p_half", "C2_p_half"), ("q1", "C3_q1"), ("F1", "C4_F1"), ("p1", "C5_p1")):
            ok(name, _rows(r[c]) == o[c], f.name)
        if o["q1"] is not None and o["stop_stage"] != "F0":
            ok("C3_gpu_position_echo_q1", _rows(r["gpu_echo_q1"]) == o["q1"], f.name)
        ok("C6_endpoints_key", r["endpoints_key"] == o["endpoints_key"], f.name)
        ok("C6_decide", r["decide"] == o["decide"], f.name)
        good = all(_rows(r[c]) == o[c] for c in ("F0", "p_half", "q1", "F1", "p1")) and \
            r["endpoints_key"] == o["endpoints_key"] and r["status"] == o["status"]
        if o["status"] == "OK":
            stats["steps_exact" if good else "steps_mismatch"] += 1
        else:
            stats["stops_exact" if good and (r["stop_stage"], r["stop_pair"]) == (o["stop_stage"], o["stop_pair"])
                  else "stops_mismatch"] += 1
        view = json.dumps({k: r[k] for k in ("F0", "p_half", "q1", "F1", "p1", "status", "stop_stage", "stop_pair",
                                             "endpoints_key", "decide")}, sort_keys=True)
        layouts.setdefault(key, []).append((r["block"], r["grid"], view))
    for key, runs in layouts.items():
        ok("layouts_identical", len({v for _, _, v in runs}) == 1, f"{key}: {len(runs)} runs")
        if expect_layouts and key[0] == "main":
            ok("layouts_complete", len(runs) >= 4, f"{key}: {len(runs)}")
    if expect_layouts:
        for key in sts:
            ok("state_present", key in layouts, str(key))
    bad = sum(v[1] for v in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "counts": counts, "issues": issues[:80], "stats": stats}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], {k: v for k, v in res["counts"].items() if v[1]}, res["issues"][:6], res["stats"])


if __name__ == "__main__":
    main()
