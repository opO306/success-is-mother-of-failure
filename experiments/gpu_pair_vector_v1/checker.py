"""Independent checker of GPU_PAIR_VECTOR_V1 (protocol 'checker'). Imports none of pv_host, pv1.cu, campaign, nor
G0's GPU code. With its own literal forces loop (mpmath iv, the frozen RwForce, K.domain, K.H) it recomputes d, r2, G,
J for every pair and F for every state, checks its F against the F recorded from the real runs, and compares every
device word it decodes itself.

    python -m experiments.gpu_pair_vector_v1.checker DIR
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
BUNDLE = ROOT / "docs/active/gpu_pair_vector_v1/states.json.gz"
BUNDLE_SHA_FILE = ROOT / "docs/active/gpu_pair_vector_v1/states.json.gz.sha256"
WF, WA, WM = 114, 26, 22
ST = {0: "PROVEN", 1: "UNPROVEN", 2: "VIOLATED", 3: "REFUSED_DEVICE_WIDTH", 4: "REFUSED_DEVICE_PRECISION"}
EV = "rw:R1+R2"
N_LAYOUTS = 12
_CACHE = {}


def _dec_end(e):
    s, h, x, bc = e
    m = int(h, 16)
    return (0, 0, 0, 0) if m == 0 else (s, m, x, bc)


def _dec_iv(e):
    return (_dec_end(e[0]), _dec_end(e[1]))


def _val(t):
    s, m, e, bc = t
    v = Fraction(m) * Fraction(2) ** e
    return -v if s else v


def _mp(ws):
    sign, n, bc, lo, hi = ws[:5]
    if n == 0:
        return (0, 0, 0, 0)
    e = (hi << 32) | lo
    e = e - (1 << 64) if e >> 63 else e
    return (sign, sum(ws[5 + i] << (32 * i) for i in range(n)), e, bc)


def _iv(ws):
    return (_mp(ws[:11]), _mp(ws[11:22]))


def _words(raw):
    return [int.from_bytes(raw[4 * i:4 * i + 4], "little") for i in range(len(raw) // 4)]


def _force(p):
    key = ("force", p)
    if key not in _CACHE:
        from experiments.rewrite_pilot_a3 import adapter as AD
        from experiments.rewrite_pilot_a3 import rwforce as RW
        AD.prepare(EV)
        iv.prec = p
        _CACHE[key] = RW.RwForce(AD._PLAN)
    return _CACHE[key]


def own_forces(q_raw, p):
    """Literal CPU loop: per pair (status, r2, G, J) for every pair (statuses of all pairs, J only when PROVEN), the
    first non-PROVEN pair, and F if every pair is PROVEN."""
    import exact_expression_gate_v0.lang_iv as LI
    from exact_expression_gate_v1 import common as K
    force = _force(p)
    iv.prec = p
    q = [[iv.make_mpf(x) for x in row] for row in q_raw]
    h, zero = LI.c(K.H), LI.c(Fraction(0))
    n = len(q)
    F = [[zero] * 3 for _ in range(n)]
    pairs, first = [], None
    for i in range(n):
        for j in range(i + 1, n):
            d = [q[j][k] - q[i][k] for k in range(3)]
            r2 = (d[0] * d[0] + d[1] * d[1]) + d[2] * d[2]
            st = K.domain(r2)
            if st != K.PROVEN:
                first = len(pairs) if first is None else first
                pairs.append((st, r2._mpi_, None, None))
                continue
            try:
                g = force(r2)
            except K.DomainStop as e:
                first = len(pairs) if first is None else first
                pairs.append((e.kind, r2._mpi_, None, None))
                continue
            J = [(h * g) * d[k] for k in range(3)]
            pairs.append((st, r2._mpi_, g._mpi_, tuple(x._mpi_ for x in J)))
            if first is None:
                for k in range(3):
                    F[j][k] = F[j][k] + J[k]
                    F[i][k] = F[i][k] - J[k]
    return pairs, first, (None if first is not None else [[x._mpi_ for x in r] for r in F])


def classify(gpu_J, cpu_J):
    if gpu_J == cpu_J:
        return "PAIR_EXACT"
    for g, c in zip(gpu_J, cpu_J):
        if not (_val(g[0]) <= _val(c[0]) and _val(c[1]) <= _val(g[1])):
            return "PAIR_UNSOUND"
    return "PAIR_SOUND_ONLY"


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
    states = {("main", x["id"]): x for x in b["main"]}
    states.update({("test", x["id"]): x for x in b["test_only"]})
    envf = d / "env.json"
    if envf.exists():
        env = json.loads(envf.read_text(encoding="utf-8"))
        ok("seal_clean", env["status_porcelain"] == "" and not env["sealed_sources_dirty"], env["status_porcelain"][:200])
        ok("env_bundle_sha", env["bundle_sha256"] == sealed)

    def cpu(key, x):
        if key not in _CACHE:
            q = [[_dec_iv(e) for e in row] for row in x["q"]]
            pairs, first, F = own_forces(q, x["p"])
            _CACHE[key] = (pairs, first, F)
            ok("cpu_first_stop_equals_bundle", (first, (pairs[first][0] if first is not None else "PROVEN")) ==
               (x["cpu_first_stop_pair"], x["cpu_status"]), str(key))
            if x["F_cpu"] is not None:
                ok("own_loop_F_equals_recorded_run_F", F == [[_dec_iv(e) for e in r] for r in x["F_cpu"]], str(key))
        return _CACHE[key]

    stats = {"PAIR_EXACT": 0, "PAIR_SOUND_ONLY": 0, "PAIR_UNSOUND": 0, "DOMAIN_MISMATCH": 0, "REFUSED": 0,
             "F_EXACT": 0, "F_DIFF": 0, "pairs_checked": 0, "states_checked": 0}
    layouts = {}
    for mf in sorted((d / "runs").glob("*.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        key = (m["state_kind"], m["state_id"])
        x = states.get(key)
        ok("run_state_known", x is not None, mf.name)
        if x is None:
            continue
        stem = mf.name[:-5]
        rf = gzip.decompress((d / "runs" / f"{stem}.full.gz").read_bytes())
        ra = gzip.decompress((d / "runs" / f"{stem}.atoms.gz").read_bytes())
        re_ = gzip.decompress((d / "runs" / f"{stem}.echo.gz").read_bytes())
        ok("run_output_hashes", hashlib.sha256(rf).hexdigest() == m["full_sha256"] and
           hashlib.sha256(ra).hexdigest() == m["atoms_sha256"], mf.name)
        ok("run_settings_clean", m["fault"] == 0 and m["g0fault"] == 0 and m["work_limbs"] == 16 and m["tamper"] is None,
           mf.name)
        N, p = x["N"], x["p"]
        P = N * (N - 1) // 2
        first_run = key not in layouts
        layouts.setdefault(key, []).append((m["block"], m["grid_arg"], rf, ra))
        # positions echo
        ew = _words(re_)
        echo = [[_iv(ew[(3 * a + k) * WM:(3 * a + k + 1) * WM]) for k in range(3)] for a in range(N)] \
            if len(ew) == N * 3 * WM else None
        ok("positions_echo_equals_bundle", echo == [[_dec_iv(e) for e in row] for row in x["q"]], mf.name)
        pairs, first, F = cpu(key, x)
        fw = _words(rf)
        ok("pair_count", len(fw) == P * WF, f"{mf.name}: {len(fw) // WF} records for {P} pairs")
        gfirst = None
        for pid in range(min(P, len(fw) // WF)):
            o = fw[pid * WF:(pid + 1) * WF]
            where = f"{mf.name}#{pid}"
            ok("pair_id_echo", o[1] == pid, where)
            ok("precision_echo", o[3] == p, f"{where}: device p {o[3]} state p {p}")
            gst = ST.get(o[0], f"S{o[0]}")
            cst, cr2, cg, cJ = pairs[pid]
            if gst != "PROVEN" and gfirst is None:
                gfirst = pid
            if gst.startswith("REFUSED"):
                if first_run:
                    stats["REFUSED"] += 1
                continue
            if gst != cst:
                ok("domain_status", False, f"{where}: gpu {gst} cpu {cst}")
                if first_run:
                    stats["DOMAIN_MISMATCH"] += 1
                continue
            ok("domain_status", True)
            ok("r2_equal", _iv(o[4:26]) == cr2, where)
            if cst != "PROVEN":
                continue
            ok("obligations_complete", o[2] == 0b11, f"{where}: mask {o[2]}")
            ok("G_equal", _iv(o[26:48]) == cg, where)
            gJ = tuple(_iv(o[48 + 22 * k:70 + 22 * k]) for k in range(3))
            cls = classify(gJ, cJ)
            ok("pair_J_exact", cls == "PAIR_EXACT", f"{where}: {cls}")
            if first_run:
                stats[cls] += 1
                stats["pairs_checked"] += 1
        ok("first_stop_pair", gfirst == first, f"{mf.name}: gpu {gfirst} cpu {first}")
        # atoms
        aw = _words(ra)
        ok("atom_count", len(aw) == 3 * N * WA, mf.name)
        if F is not None and len(aw) == 3 * N * WA:
            for t in range(3 * N):
                o = aw[t * WA:(t + 1) * WA]
                a, k = divmod(t, 3)
                where = f"{mf.name} atom {a} k {k}"
                ok("atom_id_echo", (o[0], o[1]) == (a, k), where)
                ok("atom_precision_echo", o[2] == p, where)
                ok("atom_status", o[3] == 0, where)
                same = _iv(o[4:26]) == F[a][k]
                ok("atom_F_exact", same, where)
                if first_run:
                    stats["F_EXACT" if same else "F_DIFF"] += 1
        if first_run:
            stats["states_checked"] += 1
    for key, runs in layouts.items():
        ok("layouts_bit_identical", len({(rf, ra) for _, _, rf, ra in runs}) == 1, f"{key}: {len(runs)} runs")
        if expect_layouts and key[0] == "main":
            ok("layouts_complete", len(runs) == N_LAYOUTS, f"{key}: {len(runs)}")
    if expect_layouts:
        for key in states:
            ok("state_present", key in layouts, str(key))
    bad = sum(v[1] for v in counts.values())
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "counts": counts, "issues": issues[:80], "stats": stats}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], {k: v for k, v in res["counts"].items() if v[1]}, res["issues"][:6], res["stats"])


if __name__ == "__main__":
    main()
