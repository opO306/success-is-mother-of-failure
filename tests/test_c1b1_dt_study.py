"""C1-B1 Delta t study data (designer 11th ed., steps 3-4): the recorded measurement stays consistent.

a_reference/fixtures/c1b1_dt_study_v1.json is a MEASUREMENT (it chooses nothing). These checks read it only:
its provenance names the current code, every run finished, the three error sources were measured separately,
and the facts reported to the designer still hold in the data. Delta t itself is not frozen here.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "a_reference" / "fixtures" / "c1b1_dt_study_v1.json").read_text(encoding="utf-8"))
REFS = {r["case"]: r for r in DATA["references"]}
RUNS = collections.defaultdict(dict)
for r in DATA["runs"]:
    RUNS[r["case"]][(r["dt"], r["profile"])] = r


def _observables(case):
    if case["kind"] == "bound":
        return ["two_periods"]
    return ["time"] if case["b"] == "0" else ["sweep", "time"]


def test_provenance_names_the_current_code() -> None:
    p = DATA["provenance"]
    assert p["uncommitted_changes_in_a_reference_or_audit"] is False
    for f, h in p["code_sha256"].items():
        assert hashlib.sha256((ROOT / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == h, f
    assert DATA["dts"] == [10, 20, 40, 80, 160] and DATA["contract"] == "c1b1-two-atom-v1"


def test_every_run_finished_without_domain_exit() -> None:
    assert len(DATA["runs"]) == 40 * 5 * 3
    assert {r["status"] for r in DATA["runs"]} == {"ok"}
    assert all(r["dP"] == ["0", "0", "0"] for r in DATA["runs"])        # total momentum exactly unchanged


def test_discretisation_error_is_second_order_everywhere() -> None:
    for c in DATA["cases"]:
        for k in _observables(c):
            rep = float(REFS[c["name"]]["represented"][k])
            err = [float(RUNS[c["name"]][(dt, "HP")][k]) - rep for dt in DATA["dts"]]
            for a, b in zip(err, err[1:]):
                assert 3.8 < b / a < 4.2, (c["name"], k, err)


def test_binary64_rounding_is_far_below_discretisation_fx_is_not_at_small_dt() -> None:
    fx_over = 0
    for c in DATA["cases"]:
        for k in _observables(c):
            rep = float(REFS[c["name"]]["represented"][k])
            for dt in DATA["dts"]:
                h, b, f = (float(RUNS[c["name"]][(dt, p)][k]) for p in ("HP", "B64", "FX64_32"))
                assert abs(b - h) < 1e-3 * abs(h - rep)                   # binary64: < 0.1% (worst 0.054%)
                fx_over += abs(f - h) > abs(h - rep)
    assert fx_over > 0                                                    # FX(64,32): exceeds it somewhere
