"""Independent checker of G0 (protocol 'correctness_hard_gate', 'layout_independence'). Imports none of gpu_host,
compile_plan, campaign or the CUDA code. With its own decoder it reads the raw device output words, verifies the
sealed bundle, sample identity / order / input echo, recomputes every CPU interval with the frozen E2 RwForce,
classifies containment and width, checks obligations, run settings and bit equality across layouts.

    python -m experiments.gpu_force_feasibility_v1.checker DIR
"""

from __future__ import annotations

import gzip
import hashlib
import json
import statistics
import sys
from fractions import Fraction
from pathlib import Path

from mpmath import iv

ROOT = Path(__file__).resolve().parents[2]
PROTO = json.loads((Path(__file__).with_name("protocol.json")).read_text(encoding="utf-8"))
BUNDLE = ROOT / "docs/active/gpu_force_feasibility_v1/samples.json.gz"
BUNDLE_SHA_FILE = ROOT / "docs/active/gpu_force_feasibility_v1/samples.json.gz.sha256"
WORDS_OUT, ML = 48, 6
STATUS = {0: "OK", 1: "DOMAIN_UNPROVEN", 2: "REFUSED_DEVICE_WIDTH", 3: "REFUSED_DEVICE_PRECISION"}
OBLIGATIONS_ALL = 0b11                                  # R^2 > 0 and den > 0 for the rw:R1+R2 recip plan
EV = "rw:R1+R2"
N_LAYOUTS_MAIN = 12


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


def _words_mp(ws):
    """Own decoder of one device mpf (11 words: sign, limbs, bitcount, exp lo, exp hi, 6 limbs)."""
    sign, n, bc, lo, hi = ws[:5]
    if n == 0:
        return (0, 0, 0, 0), sign == 0 and bc == 0 and lo == 0 and hi == 0
    e = (hi << 32) | lo
    e = e - (1 << 64) if e >> 63 else e
    man = sum(ws[5 + i] << (32 * i) for i in range(n))
    canonical = man & 1 == 1 and man.bit_length() == bc and sign in (0, 1) and n == (bc + 31) // 32 and \
        all(w == 0 for w in ws[5 + n:5 + ML])
    return (sign, man, e, bc), canonical


def _cpu_force(p, cache={}):
    if p not in cache:
        from experiments.rewrite_pilot_a3 import adapter as AD
        from experiments.rewrite_pilot_a3 import rwforce as RW
        AD.prepare(EV)
        iv.prec = p
        cache[p] = RW.RwForce(AD._PLAN)
    return cache[p]


def cpu_g(p, r2):
    from exact_expression_gate_v1 import common as K
    f = _cpu_force(p)
    iv.prec = p
    try:
        return "OK", f(iv.make_mpf(r2))._mpi_
    except K.DomainStop as e:
        return ("DOMAIN_UNPROVEN" if e.kind == K.UNPROVEN else f"DOMAIN_{e.kind}"), None


def classify(gpu, cpu):
    (lg, ug), (lc, uc) = (_val(gpu[0]), _val(gpu[1])), (_val(cpu[0]), _val(cpu[1]))
    if not (lg <= lc and uc <= ug):
        return "UNSOUND", None
    if gpu == cpu:
        return "EXACT", Fraction(1)
    wc, wg = uc - lc, ug - lg
    if wc == 0:
        return "SOUND_WIDE", "inf"
    r = wg / wc
    return ("SOUND_TIGHT" if r <= 2 else "SOUND_WIDE"), r


def own_subsets(b):
    out = {}
    for p in (109, 163):
        out[f"main_p{p}"] = [x for x in b["main"] if x["p"] == p]
    for role, tag in (("TEST_ONLY_PRECISION", "test"), ("TEST_ONLY_DOMAIN_PROBE", "probe")):
        for p in sorted({x["p"] for x in b["test_only"] if x["role"] == role}):
            out[f"{tag}_p{p}"] = [x for x in b["test_only"] if x["role"] == role and x["p"] == p]
    return out


_CPU_CACHE = {}


def check(d, bundle_path=BUNDLE, bundle_sha_file=BUNDLE_SHA_FILE, require=None, expect_layouts=True, full=True):
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
    subs = own_subsets(b)
    trajs = {(t["N"], t["T"], t["p"]): t for t in b["trajectories"]}
    for t in b["trajectories"]:
        ok("bundle_trajectory_equals_reference", t["equals_reference"] and t["force_calls"] == t["expected_calls"])
    for (N, T, p), t in trajs.items():
        n = sum(1 for x in b["main"] if (x["N"], x["T"], x["p"]) == (N, T, p))
        ok("bundle_pair_count", n == 4 * t["pairs"] == 4 * N * (N - 1) // 2, f"N{N}")
    envf = d / "env.json"
    if envf.exists():
        env = json.loads(envf.read_text(encoding="utf-8"))
        ok("seal_clean", env["status_porcelain"] == "" and not env["sealed_sources_dirty"], env["status_porcelain"][:200])
        ok("env_bundle_sha", env["bundle_sha256"] == sealed)
    # ---- CPU intervals (frozen E2), computed once per used sample ----
    byid = {name: {x["id"]: x for x in xs} for name, xs in subs.items()}

    def cpu_of(name, x):
        key = (name, x["id"])
        if key not in _CPU_CACHE:
            st, g = cpu_g(x["p"], _dec_iv(x["r2"]))
            _CPU_CACHE[key] = (st, g)
            ok("bundle_cpu_equals_recomputed", (st, g) == (x["cpu_status"], _dec_iv(x["g_cpu"]) if x["g_cpu"] else None),
               f"{name} {x['id']}")
        return _CPU_CACHE[key]
    # ---- device runs ----
    stats = {}
    by_subset = {}
    for mf in sorted((d / "runs").glob("*.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        name = m["subset"]
        ids = m["sample_ids"]
        ok("run_subset_known", name in subs and all(i in byid[name] for i in ids) and ids == sorted(ids), name)
        if name not in subs or not all(i in byid[name] for i in ids):
            continue
        xs = [byid[name][i] for i in ids]
        if full:
            ok("run_covers_subset", ids == [x["id"] for x in subs[name]], mf.name)
        rawout = gzip.decompress((d / "runs" / (mf.stem + ".bin.gz")).read_bytes())
        ok("run_output_hash", hashlib.sha256(rawout).hexdigest() == m["out_sha256"], mf.name)
        ok("run_settings_clean", m["fault"] == 0 and m["work_limbs"] == 16 and m["tamper"] is None, mf.name)
        words = [int.from_bytes(rawout[4 * i:4 * i + 4], "little") for i in range(len(rawout) // 4)]
        nout = len(words) // WORDS_OUT
        ok("pair_count", nout == len(xs) and len(words) % WORDS_OUT == 0, f"{mf.name}: {nout} outputs for {len(xs)}")
        by_subset.setdefault(name, []).append((mf.name, rawout))
        st = stats.setdefault(name, {"EXACT": 0, "SOUND_TIGHT": 0, "SOUND_WIDE": 0, "UNSOUND": 0, "REFUSED": 0,
                                     "DOMAIN_OK": 0, "DOMAIN_MISMATCH": 0, "ratios": [], "runs": 0})
        st["runs"] += 1
        first = st["runs"] == 1
        for i in range(min(nout, len(xs))):
            o = words[i * WORDS_OUT:(i + 1) * WORDS_OUT]
            x = xs[i]
            where = f"{mf.name}#{i}"
            ok("output_index_echo", o[1] == i, where)
            e0, c0 = _words_mp(o[26:37])
            e1, c1 = _words_mp(o[37:48])
            ok("input_echo_equals_bundle", (e0, e1) == _dec_iv(x["r2"]), where)
            status = STATUS.get(o[0], f"STATUS_{o[0]}")
            cst, cg = cpu_of(name, x)
            if cst != "OK":
                good = status == cst and o[2] == 0
                ok("domain_decision", good, f"{where}: gpu {status} mask {o[2]} cpu {cst}")
                if first:
                    st["DOMAIN_OK" if good else "DOMAIN_MISMATCH"] += 1
                continue
            if status.startswith("REFUSED"):            # reported separately: not a pass, not UNSOUND
                if first:
                    st["REFUSED"] += 1
                continue
            if status != "OK":
                ok("domain_decision", False, f"{where}: gpu {status} cpu OK")
                if first:
                    st["DOMAIN_MISMATCH"] += 1
                continue
            ok("obligations_complete", o[2] == OBLIGATIONS_ALL, f"{where}: mask {o[2]}")
            g0, k0 = _words_mp(o[4:15])
            g1, k1 = _words_mp(o[15:26])
            ok("output_canonical", k0 and k1, where)
            cls, r = classify((g0, g1), cg)
            ok("containment", cls != "UNSOUND", f"{where}: gpu {(g0, g1)} cpu {cg}")
            if first:
                st[cls] += 1
                if r is not None:
                    st["ratios"].append(r)
    # ---- layout independence ----
    for name, runs in by_subset.items():
        ok("layouts_bit_identical", len({r for _, r in runs}) == 1, f"{name}: {len({r for _, r in runs})} variants")
        if expect_layouts and name.startswith("main"):
            ok("layouts_complete", len(runs) == N_LAYOUTS_MAIN, f"{name}: {len(runs)} runs")
    for name in (require or [n for n in subs]):
        ok("subset_present", name in by_subset, name)
    summary = {}
    for name, st in stats.items():
        rs = sorted(float(r) if r != "inf" else float("inf") for r in st.pop("ratios"))
        summary[name] = {**st, "width_ratio_median": statistics.median(rs) if rs else None,
                         "width_ratio_p95": rs[min(len(rs) - 1, int(0.95 * len(rs)))] if rs else None,
                         "width_ratio_max": rs[-1] if rs else None}
    bad = sum(v[1] for v in counts.values())
    main_un = sum(summary.get(n, {}).get("UNSOUND", 0) for n in ("main_p109", "main_p163"))
    return {"verdict": "EVIDENCE OK" if bad == 0 else "NOT_OK", "counts": counts, "issues": issues[:80],
            "summary": summary, "main_unsound": main_un}


def main():
    res = check(sys.argv[1])
    Path(sys.argv[1], "checker_verdict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(res["verdict"], {k: v for k, v in res["counts"].items() if v[1]}, res["issues"][:6])
    for k, v in res["summary"].items():
        print(k, v)


if __name__ == "__main__":
    main()
