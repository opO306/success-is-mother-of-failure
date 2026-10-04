"""Expression DAG paths A and B of V0 with the domain obligation kept (V1 fix).

The node kinds, hash-consing and the B algebra (MERGE_MAX_TERMS = 2) are V0's, unchanged. V0's defect: B folds
G(r2) * 0 to the constant 0, so the G node becomes unreachable, is never evaluated, and the force's domain check
disappears with it (two coincident atoms returned cells instead of a refusal). V1 records every G node created by
build_kdk as an OBLIGATION tagged with the step whose positions it belongs to. A checkpoint is evaluated together
with all obligations up to it, so a simplification may change the value but never removes the duty that the
original expression be defined. The check is three-way: PROVEN / UNPROVEN at this precision / VIOLATED.
"""

from __future__ import annotations

from fractions import Fraction as Q

from mpmath import iv

from . import common as K
from exact_expression_gate_v0 import lang_iv as LI

MERGE_MAX_TERMS = 2


class DAG:
    def __init__(self, optimize: bool):
        self.opt = optimize
        self.nodes = []          # id -> node tuple
        self.index = {}          # node tuple -> id (hash-consing)
        self.created_calls = 0
        self.obligations = []    # (G node id, step tag) in creation order

    def _intern(self, node):
        self.created_calls += 1
        i = self.index.get(node)
        if i is None:
            i = len(self.nodes)
            self.nodes.append(node)
            self.index[node] = i
        return i

    def const(self, x):
        return self._intern(("c", Q(x)))

    def _as_lin(self, a):
        n = self.nodes[a]
        if n[0] == "c":
            return {}, n[1]
        if n[0] == "lin" and len(n[1]) <= MERGE_MAX_TERMS:
            return dict(n[1]), n[2]
        return {a: Q(1)}, Q(0)

    def lin(self, terms, const=Q(0)):
        if not self.opt:
            return self._intern(("lin", tuple((a, Q(k)) for a, k in terms), Q(const)))
        acc, c0 = {}, Q(const)
        for a, k in terms:
            k = Q(k)
            if k == 0:
                continue
            sub, sc = self._as_lin(a)
            c0 += k * sc
            for b, kb in sub.items():
                acc[b] = acc.get(b, Q(0)) + k * kb
        acc = {b: k for b, k in acc.items() if k != 0}
        if not acc:
            return self.const(c0)
        if c0 == 0 and len(acc) == 1:
            (b, k), = acc.items()
            if k == 1:
                return b
        return self._intern(("lin", tuple(sorted(acc.items())), c0))

    def add(self, a, b):
        return self.lin([(a, 1), (b, 1)])

    def sub(self, a, b):
        return self.lin([(a, 1), (b, -1)])

    def scale(self, a, k):
        return self.lin([(a, k)])

    def mul(self, a, b):
        if self.opt:
            na, nb = self.nodes[a], self.nodes[b]
            if na[0] == "c":
                return self.scale(b, na[1])
            if nb[0] == "c":
                return self.scale(a, nb[1])
            a, b = min(a, b), max(a, b)
        return self._intern(("mul", a, b))

    def G(self, r2, step):
        g = self._intern(("G", r2))
        self.obligations.append((g, step))
        return g

    def kids(self, i):
        n = self.nodes[i]
        if n[0] == "lin":
            return [a for a, _ in n[1]]
        if n[0] == "mul":
            return [n[1], n[2]]
        if n[0] == "G":
            return [n[1]]
        return []

    def reachable(self, roots):
        seen, stack, edges = set(), list(roots), 0
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            k = self.kids(i)
            edges += len(k)
            stack.extend(k)
        return len(seen), edges

    def _collect(self, roots):
        seen, stack = set(), list(roots)
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            stack.extend(self.kids(i))
        return seen

    def evaluate(self, roots, prec, memo=None):
        """Interval values of roots. Raises K.DomainStop at the first G node whose argument is not PROVEN."""
        iv.prec = prec
        val = {} if memo is None else memo
        for i in sorted(self._collect(roots) - set(val)):      # ids are topological (children created first)
            n = self.nodes[i]
            k = n[0]
            if k == "c":
                v = LI.c(n[1])
            elif k == "lin":
                v = LI.c(n[2])
                for a, co in n[1]:
                    v = v + LI.c(co) * val[a]
            elif k == "mul":
                v = val[n[1]] * val[n[2]]
            else:
                st = K.domain(val[n[1]])
                if st != K.PROVEN:
                    raise K.DomainStop(st, i)
                v = LI.G_of_R2(val[n[1]])
            val[i] = v
        return [val[r] for r in roots]

    def first_step_of(self, g):
        return min(s for x, s in self.obligations if x == g)


def build_kdk(dag: DAG, q0, p0, steps, checkpoints):
    """Symbolic unrounded KDK (same construction as V0). Returns {s: (q ids, p ids, obligation count)}."""
    n = len(q0)
    q = [[dag.const(x) for x in r] for r in q0]
    p = [[dag.const(x) for x in r] for r in p0]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    def forces(q, step):
        F = [[[] for _ in range(3)] for _ in range(n)]
        for i, j in pairs:
            d = [dag.sub(q[j][k], q[i][k]) for k in range(3)]
            r2 = dag.lin([(dag.mul(d[k], d[k]), 1) for k in range(3)]) if dag.opt else \
                dag.add(dag.add(dag.mul(d[0], d[0]), dag.mul(d[1], d[1])), dag.mul(d[2], d[2]))
            g = dag.G(r2, step)
            for k in range(3):
                f = dag.mul(g, d[k])
                F[j][k].append((f, K.H))
                F[i][k].append((f, -K.H))
        return F

    def kick(p, F):
        out = []
        for a in range(n):
            row = []
            for k in range(3):
                terms = F[a][k]
                if dag.opt:
                    row.append(dag.lin([(p[a][k], 1)] + terms))
                else:
                    x = p[a][k]
                    for f, coef in terms:
                        x = dag.add(x, dag.scale(f, coef))
                    row.append(x)
            out.append(row)
        return out

    snaps = {}
    F = forces(q, 0)
    for s in range(1, steps + 1):
        ph = kick(p, F)
        q = [[dag.add(q[a][k], dag.scale(ph[a][k], K.CDT)) for k in range(3)] for a in range(n)]
        F = forces(q, s)
        p = kick(ph, F)
        if s in checkpoints:
            snaps[s] = ([x for r in q for x in r], [x for r in p for x in r], len(dag.obligations))
    return snaps
