"""PART B4: derivative certificate table for the event-lineage candidate (A2 range only).

Generation (offline, never at run time): for every cell [m/1024, (m+1)/1024] bohr, m = 7065 .. 7679 (covers
[6.9, 7.5]), V' and V'' enclosures from the existing a_reference.c1b1_energy_bound.radial_derivatives(a, b) and
G'(s) = (V'(R) - R V''(R)) / (2 R^3) (s = R^2) by exact interval arithmetic over the cell. Values are stored as exact
rational strings in a gzip JSON. The checker (checker.py) re-derives everything in a separate process and never reads
any PASS flag written here.

    python -m experiments.state_object_event_pilot_v0.derivative_certificate generate --out FILE [--workers N]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from fractions import Fraction as Q
from math import isqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
M_LO, M_HI = 7065, 7679                 # cells m/1024 .. (m+1)/1024, inclusive of m_hi
SCALE = 1024
GENERATOR_SOURCES = ["experiments/state_object_event_pilot_v0/derivative_certificate.py",
                     "a_reference/c1b1_energy_bound.py", "a_reference/c1b1_outer_bound.py",
                     "a_reference/c1b1_outer_bootstrap.py", "a_reference/ar2_lang2024.py"]


class EventDerivativeDomainUnsupported(Exception):
    """EVENT_DERIVATIVE_DOMAIN_UNSUPPORTED: the event's R range is not inside the certificate (no extrapolation)."""


def _lf(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _imul(x, y):
    p = (x[0] * y[0], x[0] * y[1], x[1] * y[0], x[1] * y[1])
    return min(p), max(p)


def _idiv_pos(x, y):
    if not y[0] > 0:
        raise ValueError("divisor interval must be positive")
    p = (x[0] / y[0], x[0] / y[1], x[1] / y[0], x[1] / y[1])
    return min(p), max(p)


def g_prime(V1, V2, a, b):
    """Enclosure of (V' - R V'') / (2 R^3) for R in [a, b] from enclosures V1 of V', V2 of V''."""
    RV2 = _imul((a, b), V2)
    num = (V1[0] - RV2[1], V1[1] - RV2[0])
    return _idiv_pos(num, (2 * a ** 3, 2 * b ** 3))


def cell(m):
    from a_reference.c1b1_energy_bound import radial_derivatives
    a, b = Q(m, SCALE), Q(m + 1, SCALE)
    d = radial_derivatives(a, b)
    V1, V2 = (d[1].lo, d[1].hi), (d[2].lo, d[2].hi)
    Gp = g_prime(V1, V2, a, b)
    return {"m": m, "V1": [str(V1[0]), str(V1[1])], "V2": [str(V2[0]), str(V2[1])], "Gp": [str(Gp[0]), str(Gp[1])]}


def generate(out, workers=1):
    t0, c0 = time.perf_counter(), time.process_time()
    ms = list(range(M_LO, M_HI + 1))
    if workers > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(workers) as pool:
            cells = pool.map(cell, ms, chunksize=8)
    else:
        cells = [cell(m) for m in ms]
    body = {"schema": "soe-pilot-v0-derivative-certificate-v1", "domain_R_bohr": [f"{M_LO}/{SCALE}", f"{M_HI + 1}/{SCALE}"],
            "cell_width": f"1/{SCALE}", "cells": cells,
            "protocol_sha256_lf": _lf(HERE / "protocol.json"),
            "generator_source_sha256_lf": {s: _lf(ROOT / s) for s in GENERATOR_SOURCES},
            "generation": {"wall_s": time.perf_counter() - t0, "parent_cpu_s": time.process_time() - c0, "workers": workers}}
    raw = json.dumps(body, indent=0, sort_keys=True).encode()
    with gzip.GzipFile(out, "wb", mtime=0) as f:
        f.write(raw)
    return body


class Table:
    """Run-time lookup only: hull of G' over the certificate cells that cover [sqrt(a), sqrt(b)]."""

    def __init__(self, path):
        with gzip.open(path, "rb") as f:
            body = json.loads(f.read())
        self.sha256 = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        cells = body["cells"]
        if [c["m"] for c in cells] != list(range(M_LO, M_HI + 1)):
            raise ValueError("certificate cells are not the declared contiguous grid")
        self.gp = [(Q(c["Gp"][0]), Q(c["Gp"][1])) for c in cells]

    @staticmethod
    def cell_range(a: Q, b: Q):
        """Indices m of the closed cells [m/1024, (m+1)/1024] covering R in [sqrt(a), sqrt(b)], a <= b (exact)."""
        lo_y, hi_y = a * SCALE * SCALE, b * SCALE * SCALE
        m_lo = isqrt(lo_y.numerator // lo_y.denominator)              # floor(sqrt(lo_y))
        n = hi_y.numerator // hi_y.denominator
        s = isqrt(n)
        ceil_hi = s if (s * s == hi_y) else s + 1                        # ceil(sqrt(hi_y))
        return m_lo, max(m_lo, ceil_hi - 1)

    def gprime_hull(self, a: Q, b: Q):
        m_lo, m_hi = self.cell_range(a, b)
        if m_lo < M_LO or m_hi > M_HI:
            raise EventDerivativeDomainUnsupported(f"R range cells {m_lo}..{m_hi} outside {M_LO}..{M_HI}")
        cs = self.gp[m_lo - M_LO:m_hi - M_LO + 1]
        return min(c[0] for c in cs), max(c[1] for c in cs), (m_lo, m_hi)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["generate"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args(argv)
    body = generate(a.out, a.workers)
    print(json.dumps({"cells": len(body["cells"]), **body["generation"]}))


if __name__ == "__main__":
    main()
