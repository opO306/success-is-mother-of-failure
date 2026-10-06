"""XREPRO_RESOURCE_V1 comparator: it must see a one-character endpoint change, a cell change, a missing pass and
timing-only differences correctly (fault injection on a real run-2 record)."""

import copy
import gzip
import json
from pathlib import Path

from experiments.xrepro_resource_v1 import compare as C

ROOT = Path(__file__).resolve().parents[1]
RUN2 = ROOT / "docs/active/resource_evolution_v1/run2/results.json.gz"


def _pass():
    run = json.load(gzip.open(RUN2))["run"]
    return json.loads(run["T0__algebra__A3_high_1000__cpu2.json"])["workers"][0]["passes"][0]


def test_equal_pass_has_no_difference():
    p = _pass()
    assert C.first_diff(C.pass_view(p), C.pass_view(copy.deepcopy(p))) is None
    assert C.cells_ok(p)


def test_endpoint_change_is_found_with_its_position():
    p, q = _pass(), copy.deepcopy(_pass())
    s = q["endpoints_scaled"][7][1]
    q["endpoints_scaled"][7][1] = s[:-1] + ("1" if s[-1] != "1" else "3")
    d = C.first_diff(C.pass_view(p), C.pass_view(q))
    assert d is not None and d.startswith("/endpoints_scaled[7][1]")


def test_cell_change_is_found_and_not_rederived():
    q = copy.deepcopy(_pass())
    q["cells"][0] += 1
    assert not C.cells_ok(q)
    assert C.first_diff(C.pass_view(_pass()), C.pass_view(q)).startswith("/cells[0]")


def test_missing_pass_and_timing_fields():
    p = _pass()
    assert C.first_diff([p], [p, p]).endswith("length 1 vs 2")
    a, b = {"x": 1, "cpu_s": 1.0, "pid": 3, "inner": {"wall_s": 2}}, {"x": 1, "cpu_s": 9.0, "pid": 4, "inner": {}}
    assert C.first_diff(C.strip(a), C.strip(b)) is None
    assert C.first_diff(C.strip(a), C.strip({"x": 2})) is not None
