"""Expression DAG for the unrounded KDK map (paths A and B) and interval evaluation.

Node kinds:  ("c", Fraction)              exact constant
             ("lin", ((id, coeff), ...), const)   const + sum coeff * node   (exact rational coeffs)
             ("mul", a, b)                product of two nodes
             ("G", r2)                    Lang G(R2) = -dV/dR / R at R = sqrt(R2)
Path A builds only "c", "lin" with exactly two terms (plain add/sub/scale), "mul", "G" -- with hash-consing.
Path B (optimize=True) folds constants, drops zero terms, and merges a nested linear combination into its
parent only when the child has at most MERGE_MAX_TERMS terms (unbounded flattening copies every past force
term into every new momentum node: quadratic history size, found in the pre-seal quick run).
"""

from __future__ import annotations

from fractions import Fraction as Q

from mpmath import iv

from . import lang_iv as LI

R_MIN2 = LI.c(LI.L.R_MIN_BOHR ** 2)


MERGE_MAX_TERMS = 2


class DAG:
    def __init__(self, optimize: bool):
        self.opt = optimize
        self.nodes = []          # id -> node tuple
        self.index = {}          # node tuple -> id (hash-consing)
        self.created_calls = 0

    def _intern(self, node):
        self.created_calls += 1
        i = self.index.get(node)
        if i is None:
            i = len(self.nodes)
            self.nodes.append(node)
            self.index[node] = i
        return i

    # -- constructors -------------------------------------------------------------------------
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
        """const + sum coeff * node. terms: list of (node, coeff)."""
        if not self.opt:
            # A: no algebra, keep the literal structure (two-term nodes only)
            node = ("lin", tuple((a, Q(k)) for a, k in terms), Q(const))
            return self._intern(node)
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

    def G(self, r2):
        return self._intern(("G", r2))

    # -- size ---------------------------------------------------------------------------------
    def reachable(self, roots):
        seen, stack = set(), list(roots)
        edges = 0
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            n = self.nodes[i]
            kids = [a for a, _ in n[1]] if n[0] == "lin" else ([n[1], n[2]] if n[0] == "mul" else ([n[1]] if n[0] == "G" else []))
            edges += len(kids)
            stack.extend(kids)
        return len(seen), edges

    # -- interval evaluation (memoised per precision) ------------------------------------------
    def evaluate(self, roots, prec, memo=None):
        iv.prec = prec
        val = {} if memo is None else memo
        need = sorted(self._collect(roots) - set(val))
        for i in need:                       # ids are topologically ordered (children created first)
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
                r2 = val[n[1]]
                if not (r2.a > R_MIN2):
                    raise ValueError("R^2 enclosure reaches below r_min^2 (interval blow-up or domain)")
                v = LI.G_of_R2(r2)
            val[i] = v
        return [val[r] for r in roots]

    def _collect(self, roots):
        seen, stack = set(), list(roots)
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            n = self.nodes[i]
            if n[0] == "lin":
                stack.extend(a for a, _ in n[1])
            elif n[0] == "mul":
                stack.extend([n[1], n[2]])
            elif n[0] == "G":
                stack.append(n[1])
        return seen


def build_kdk(dag: DAG, q0, p0, mass, dt, steps, checkpoints):
    """Symbolic unrounded KDK. q0, p0: lists of 3-tuples of Fractions. Returns {checkpoint: (q ids, p ids)}."""
    n = len(q0)
    h = Q(dt) / 2
    cdt = Q(dt) / mass
    q = [[dag.const(x) for x in r] for r in q0]
    p = [[dag.const(x) for x in r] for r in p0]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    def forces(q):
        F = [[[] for _ in range(3)] for _ in range(n)]
        for i, j in pairs:
            d = [dag.sub(q[j][k], q[i][k]) for k in range(3)]
            r2 = dag.lin([(dag.mul(d[k], d[k]), 1) for k in range(3)]) if dag.opt else \
                dag.add(dag.add(dag.mul(d[0], d[0]), dag.mul(d[1], d[1])), dag.mul(d[2], d[2]))
            g = dag.G(r2)
            for k in range(3):
                f = dag.mul(g, d[k])            # G * (r_j - r_i): force direction on j
                F[j][k].append((f, h))
                F[i][k].append((f, -h))
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
    F = forces(q) if pairs else [[[] for _ in range(3)] for _ in range(n)]
    for s in range(1, steps + 1):
        ph = kick(p, F)
        q = [[dag.add(q[a][k], dag.scale(ph[a][k], cdt)) for k in range(3)] for a in range(n)]
        F = forces(q) if pairs else F
        p = kick(ph, F)
        if s in checkpoints:
            snaps[s] = ([x for r in q for x in r], [x for r in p for x in r])
    return snaps
