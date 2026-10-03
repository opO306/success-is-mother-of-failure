"""Independent fermion-operator evaluation. Standard library only.

No spatial-pair matrix formula, old normalization/mapping helper, PySCF FCI,
or old evaluator is imported. Input values are unmodified chemists h/g.
The operator is evaluated by creation/annihilation on ordered determinants.
"""
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import combinations
import math


def ladder(occupied, orbital, create):
    """a or a+; sign is occupied orbitals strictly below the operated one."""
    present = orbital in occupied
    if present == create:
        return None
    sign = -1 if sum(x < orbital for x in occupied) % 2 else 1
    result = tuple(sorted((*occupied, orbital))) if create else tuple(x for x in occupied if x != orbital)
    return result, sign


def operate(occupied, operations):
    sign = 1
    for orbital, create in operations:  # rightmost operator first
        out = ladder(occupied, orbital, create)
        if out is None:
            return None
        occupied, factor = out
        sign *= factor
    return occupied, sign


def singlet(pair):
    a, b = sorted(pair)
    if a == b:
        return [((2*a, 2*a+1), 1)], 0
    # Expanding (ab+ba)(alpha beta-beta alpha)/2 in ordered determinants
    # gives (D[a alpha,b beta] - D[a beta,b alpha])/sqrt(2).
    return [((2*a, 2*b+1), 1), ((2*a+1, 2*b), -1)], 1


def state_catalog(n):
    """Enumerate alpha/beta occupations first, deduplicate by physical pair."""
    identities = {tuple(sorted((alpha, beta))) for alpha in range(n) for beta in range(n)}
    result = []
    for pair in sorted(identities):
        terms, radical = singlet(pair)
        result.append(dict(pair=list(pair), occupation=[[p, pair.count(p)] for p in sorted(set(pair))],
                           S=0, Ms=0, normalization='closed_unit' if not radical else 'open_1_over_sqrt2',
                           determinants=[dict(occupied=list(d), sign=s) for d, s in terms]))
    return result


def element_terms(bra, ket):
    """Yield signed h/g references using only fermion operations."""
    bras, rb = singlet(bra)
    kets, rk = singlet(ket)
    for bd, bs in bras:
        for kd, ks in kets:
            for q in kd:
                for p in bd:
                    if p % 2 != q % 2:
                        continue
                    out = operate(kd, [(q, False), (p, True)])
                    if out is not None and out[0] == bd:
                        yield 'one_electron', (p//2, q//2), Fraction(bs*ks*out[1]), rb+rk, dict(fermion_sign=out[1], bra_sign=bs, ket_sign=ks)
            for q in kd:
                s = next(x for x in kd if x != q)
                for p in bd:
                    r = next(x for x in bd if x != p)
                    if p % 2 != q % 2 or r % 2 != s % 2:
                        continue
                    out = operate(kd, [(q, False), (s, False), (r, True), (p, True)])
                    if out is not None and out[0] == bd:
                        # Direct/exchange refer to uncrossed/crossed ordered
                        # determinant electron lines, before singlet signs.
                        uncrossed = (bd.index(p) == kd.index(q))
                        kind = 'Coulomb' if uncrossed else 'exchange'
                        yield kind, (p//2, q//2, r//2, s//2), Fraction(bs*ks*out[1], 2), rb+rk, dict(fermion_sign=out[1], bra_sign=bs, ket_sign=ks)


def value(h, g, bra, ket):
    terms = list(element_terms(bra, ket))
    radical = int(bra[0] != bra[1]) + int(ket[0] != ket[1])
    return math.fsum(float(c) * float((h if len(idx) == 2 else g)[idx]) for _, idx, c, _, _ in terms) / (math.sqrt(2)**radical)


def breakdown(h, g, bra, ket):
    raw = {key: Fraction(0) for key in ('one_electron', 'Coulomb', 'exchange')}
    entries = []
    radical = int(bra[0] != bra[1]) + int(ket[0] != ket[1])
    for kind, idx, coefficient, exponent, signs in element_terms(bra, ket):
        assert exponent == radical
        x = float((h if len(idx) == 2 else g)[idx])
        raw[kind] += coefficient * Fraction(x)
        entries.append(dict(kind=kind, indices=list(idx), input=x, input_hex=x.hex(),
                            coefficient=str(coefficient), sqrt2_denominator_power=radical, **signs))
    with localcontext() as ctx:
        ctx.prec = 100
        divisor = Decimal(2).sqrt()**radical
        dec = {k: Decimal(v.numerator)/Decimal(v.denominator)/divisor for k, v in raw.items()}
        result = sum(dec.values())
        return dict(value=float(result), decimal100=str(result),
                    contribution={k: str(v) for k, v in dec.items()},
                    exact_dyadic_numerators_before_radical={k: str(v) for k, v in raw.items()},
                    normalization_denominator=f'sqrt(2)^{radical}', terms=entries,
                    precision_scope='Exact dyadic term accumulation; 100-digit radical display; rounded binary64 MO input is not HP AO.')


def spin_zero(pair):
    """Check S+ annihilates the spin-adapted state with exact integer signs."""
    dets, _ = singlet(pair)
    raised = {}
    for det, coefficient in dets:
        for q in det:
            if q % 2:
                out = operate(det, [(q, False), (q-1, True)])
                if out is not None:
                    raised[out[0]] = raised.get(out[0], 0) + coefficient*out[1]
    return all(x == 0 for x in raised.values())


def alpha_beta_terms(pair):
    """Change determinant creation order by permutation parity, not a pair helper."""
    terms, radical = singlet(pair)
    result = []
    for det, coefficient in terms:
        blocked = sorted(det, key=lambda x: (x % 2, x//2))
        inversions = sum(blocked[i] > blocked[j] for i, j in combinations(range(len(det)), 2))
        coefficient *= (-1)**inversions
        alpha = next(x//2 for x in blocked if x % 2 == 0)
        beta = next(x//2 for x in blocked if x % 2 == 1)
        result.append((alpha, beta, coefficient/(math.sqrt(2)**radical)))
    return result


def e_product_element(k, bra, ket):
    """Localized spin-free K[pqrs] E_pq E_rs diagnostic, no matrix repair."""
    bras, rb = singlet(bra); kets, rk = singlet(ket)
    n = len(k); contributions = {}
    for kd, ks in kets:
        for s in kd:
            for r in range(s % 2, 2*n, 2):
                first = operate(kd, [(s, False), (r, True)])
                if first is None:
                    continue
                middle, fsign = first
                for q in middle:
                    for bd, bs in bras:
                        for p in bd:
                            if p % 2 != q % 2:
                                continue
                            second = operate(middle, [(q, False), (p, True)])
                            if second is not None and second[0] == bd:
                                idx = (p//2, q//2, r//2, s//2)
                                contributions[idx] = contributions.get(idx, 0) + ks*bs*fsign*second[1]
    total = math.fsum(c*float(k[idx]) for idx, c in contributions.items())/(math.sqrt(2)**(rb+rk))
    return total, [dict(indices=list(idx), integer_coefficient=c, input=float(k[idx])) for idx, c in sorted(contributions.items()) if c]
