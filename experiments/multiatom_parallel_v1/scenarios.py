"""FCC_N initial states of MULTIATOM_PARALLEL_V1 (protocol.json, scenario_family). Exact Fractions, no randomness."""

from __future__ import annotations

from fractions import Fraction as Q
from itertools import product

SPACING = Q(5)          # bohr per lattice unit; nearest neighbour 5*sqrt(2)


def fcc_sites(n):
    r = 1
    while True:                                   # grow the box until it surely holds the first n shells
        pts = [v for v in product(range(-r, r + 1), repeat=3) if sum(v) % 2 == 0]
        pts.sort(key=lambda v: (v[0] ** 2 + v[1] ** 2 + v[2] ** 2, v))
        if len(pts) >= n and pts[n - 1][0] ** 2 + pts[n - 1][1] ** 2 + pts[n - 1][2] ** 2 < (r + 1) ** 2:
            return pts[:n]
        r += 1


def initial(n):
    q0 = [[SPACING * c for c in s] for s in fcc_sites(n)]
    raw = [[Q((7 * i + 3 * k + 1) % 5 - 2) for k in range(3)] for i in range(n)]
    mean = [sum(raw[i][k] for i in range(n)) / n for k in range(3)]
    p0 = [[raw[i][k] - mean[k] for k in range(3)] for i in range(n)]
    return q0, p0


def pair_blocks(n, w):
    """Canonical pair list (i < j, lexicographic) split into w contiguous blocks whose sizes differ by at most 1."""
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    base, extra = divmod(len(pairs), w)
    out, at = [], 0
    for b in range(w):
        size = base + (1 if b < extra else 0)
        out.append(pairs[at:at + size])
        at += size
    return out
