// B2: CUDA evaluator of the C1-A Ar-Ar V(R) and F(R) = -dV/dR, each the exact model value rounded once
// (contract c1a-ar2-lang2024-v1). One GPU thread per query.
//
// designer 9th ed. item 5 (B2 after B1 matched B0 / the reference). The DEVICE arithmetic is written
// separately from ar2_core.hpp (host): fixed-width magnitudes of DL 32-bit limbs, sign-magnitude integers,
// fixed-point intervals at 2^-M with outward rounding, Knuth division, e^-x by Taylor + squaring, binary64
// and FX rounding. The host part only parses queries and prints answers (ar2_core.hpp's read_queries /
// write_answers are reused for that -- disclosed).
//
// Width: estimated largest intermediate at M = 768 ~1800 bits (1/R^17 numerators near r_min ~1670 bits,
// g'(R) products); MEASURED over the fixture with every query forced to M = 768: 57 limbs = 1824 bits
// (AR2_TRACK_WIDTH build). DL = 96 limbs (3072 bits) leaves ~1250 bits of margin -- measured, not proven. Any
// operation whose result would not fit POISONS it, poison propagates, and a poisoned answer is refused
// ("device_width") -- never rounded. Precision M = 96, 192, 384, 768 (NATIVE_AR2_MAX_ATTEMPTS = 4); still
// undecided -> refused ("device_precision_cap"), where B0 would go on to 3072.
//
// Layout (E9): <block_size> threads per block, <grid_blocks> blocks per launch, <launch_chunk> queries per
// launch; each block walks its queries grid-stride. No layout may change an answer.
// Usage: ar2_b2 <block_size> <grid_blocks> <launch_chunk> <queries.txt> <answers.txt>   (0 = default)
#include <cuda_runtime.h>

#include "ar2_core.hpp"  // host I/O only

static Int accumulate(const std::vector<Int>& xs) {  // required by anvm_core; unused
    Int s;
    for (const Int& x : xs) s = iadd(s, x);
    return s;
}

#if INJECT == 206
#define DL 36  // defect: device width too small for M = 384 -- must surface as refusals, never as wrong bits
#else
#define DL 96
#endif
#define POISON (DL + 1)
#ifndef NATIVE_AR2_MAX_ATTEMPTS
#define NATIVE_AR2_MAX_ATTEMPTS 4
#endif
#define M0 96

// ---------------------------------------------------------------------------
// Device magnitudes
// ---------------------------------------------------------------------------
struct DN {
    int n;  // limbs in use; POISON = overflowed
    uint32_t w[DL];
};
__device__ __forceinline__ bool bad(const DN& a) { return a.n == POISON; }
#ifdef AR2_TRACK_WIDTH
__device__ int g_max_limbs;  // measurement build only: the widest trimmed magnitude seen
#endif
__device__ __noinline__ void dn_trim(DN& r) {
    if (bad(r)) return;
    while (r.n > 0 && r.w[r.n - 1] == 0) r.n--;
#ifdef AR2_TRACK_WIDTH
    atomicMax(&g_max_limbs, r.n);
#endif
}
__device__ __noinline__ void dn_u64(DN& r, uint64_t v) {
    r.n = 0;
    while (v) { r.w[r.n++] = (uint32_t)v; v >>= 32; }
}
__device__ __noinline__ void dn_copy(DN& r, const DN& a) {
    r.n = a.n;
    if (bad(a)) return;
    for (int i = 0; i < a.n; i++) r.w[i] = a.w[i];
}
__device__ __noinline__ int dn_bitlen(const DN& a) {
    if (bad(a)) return DL * 32 + 1;
    return a.n ? (a.n - 1) * 32 + 32 - __clz(a.w[a.n - 1]) : 0;
}
__device__ __noinline__ int dn_cmp(const DN& a, const DN& b) {  // a poisoned operand compares as 0 (result is poisoned anyway)
    if (bad(a) || bad(b)) return 0;
    if (a.n != b.n) return a.n < b.n ? -1 : 1;
    for (int i = a.n - 1; i >= 0; i--)
        if (a.w[i] != b.w[i]) return a.w[i] < b.w[i] ? -1 : 1;
    return 0;
}
__device__ __noinline__ void dn_add(DN& r, const DN& a, const DN& b) {  // r may alias a or b
    if (bad(a) || bad(b)) { r.n = POISON; return; }
    int n = max(a.n, b.n);
    uint64_t c = 0;
    for (int i = 0; i < n; i++) {
        uint64_t t = c + (i < a.n ? a.w[i] : 0) + (i < b.n ? b.w[i] : 0);
        r.w[i] = (uint32_t)t;
        c = t >> 32;
    }
    if (c) {
        if (n == DL) { r.n = POISON; return; }
        r.w[n++] = (uint32_t)c;
    }
    r.n = n;
}
__device__ __noinline__ void dn_sub(DN& r, const DN& a, const DN& b) {  // a >= b; r may alias
    if (bad(a) || bad(b)) { r.n = POISON; return; }
    int64_t br = 0;
    for (int i = 0; i < a.n; i++) {
        int64_t t = (int64_t)a.w[i] - br - (i < b.n ? (int64_t)b.w[i] : 0);
        br = t < 0;
        r.w[i] = (uint32_t)(t + (br ? ((int64_t)1 << 32) : 0));
    }
    r.n = a.n;
    dn_trim(r);
}
__device__ __noinline__ void dn_mul(DN& r, const DN& a, const DN& b) {  // r must not alias
    if (bad(a) || bad(b)) { r.n = POISON; return; }
    if (!a.n || !b.n) { r.n = 0; return; }
    if (dn_bitlen(a) + dn_bitlen(b) > DL * 32) { r.n = POISON; return; }
    // the product fits in DL limbs, so every partial product at limb >= DL is zero and is skipped
    int n = min(a.n + b.n, DL);
    for (int i = 0; i < n; i++) r.w[i] = 0;
    for (int i = 0; i < a.n; i++) {
        uint64_t c = 0;
        for (int j = 0; j < b.n && i + j < n; j++) {
            uint64_t t = (uint64_t)a.w[i] * b.w[j] + r.w[i + j] + c;
            r.w[i + j] = (uint32_t)t;
            c = t >> 32;
        }
        if (i + b.n < n) r.w[i + b.n] = (uint32_t)c;
    }
    r.n = n;
    dn_trim(r);
}
__device__ __noinline__ void dn_mul_small(DN& r, const DN& a, uint32_t k) {  // r may alias
    if (bad(a)) { r.n = POISON; return; }
    uint64_t c = 0;
    for (int i = 0; i < a.n; i++) {
        uint64_t t = (uint64_t)a.w[i] * k + c;
        r.w[i] = (uint32_t)t;
        c = t >> 32;
    }
    r.n = a.n;
    if (c) {
        if (r.n == DL) { r.n = POISON; return; }
        r.w[r.n++] = (uint32_t)c;
    }
    dn_trim(r);
}
__device__ __noinline__ void dn_shl(DN& r, const DN& a, int s) {  // r may alias
    if (bad(a)) { r.n = POISON; return; }
    if (!a.n) { r.n = 0; return; }
    int wq = s >> 5, b = s & 31;
    int n = a.n + wq + 1;
    if (n > DL) {
        if (dn_bitlen(a) + s > DL * 32) { r.n = POISON; return; }
        n = DL;
    }
    for (int i = n - 1; i >= 0; i--) {
        int src = i - wq;
        uint32_t hi = (src >= 0 && src < a.n) ? a.w[src] : 0;
        uint32_t lo = (src - 1 >= 0 && src - 1 < a.n) ? a.w[src - 1] : 0;
        r.w[i] = b ? (hi << b) | (lo >> (32 - b)) : hi;
    }
    r.n = n;
    dn_trim(r);
}
__device__ __noinline__ bool dn_low_zero(const DN& a, int s) {  // a mod 2^s == 0
    if (bad(a)) return true;
    int wq = s >> 5, b = s & 31;
    for (int i = 0; i < min(wq, a.n); i++)
        if (a.w[i]) return false;
    return !(b && wq < a.n && (a.w[wq] & ((1u << b) - 1)));
}
__device__ __noinline__ void dn_shr(DN& r, const DN& a, int s, bool up) {  // floor / ceil; r may alias
    if (bad(a)) { r.n = POISON; return; }
    bool inexact = !dn_low_zero(a, s);
    int wq = s >> 5, b = s & 31;
    int n = a.n - wq;
    if (n <= 0) {
        r.n = 0;
    } else {
        for (int i = 0; i < n; i++) {
            uint32_t lo = a.w[i + wq], hi = i + wq + 1 < a.n ? a.w[i + wq + 1] : 0;
            r.w[i] = b ? (lo >> b) | (hi << (32 - b)) : lo;
        }
        r.n = n;
        dn_trim(r);
    }
    if (up && inexact) {
        DN one;
        dn_u64(one, 1);
        dn_add(r, r, one);
    }
}
// r = floor / ceil (a / d), d small; returns whether exact; r may alias
__device__ __noinline__ bool dn_div_small(DN& r, const DN& a, uint32_t d, bool up) {
    if (bad(a)) { r.n = POISON; return true; }
    uint64_t rem = 0;
    for (int i = a.n - 1; i >= 0; i--) {
        uint64_t cur = (rem << 32) | a.w[i];
        r.w[i] = (uint32_t)(cur / d);
        rem = cur % d;
    }
    r.n = a.n;
    dn_trim(r);
    if (up && rem) {
        DN one;
        dn_u64(one, 1);
        dn_add(r, r, one);
    }
    return rem == 0;
}
// Knuth algorithm D: q = floor(a / b), returns whether the remainder is 0. q must not alias.
__device__ __noinline__ bool dn_div(DN& q, const DN& a, const DN& b) {
    if (bad(a) || bad(b) || !b.n) { q.n = POISON; return true; }
    if (dn_cmp(a, b) < 0) { q.n = 0; return a.n == 0; }
    int n = b.n, m = a.n - n;
    if (n == 1) return dn_div_small(q, a, b.w[0], false);
    int s = __clz(b.w[n - 1]);
    uint32_t bn[DL], an[DL + 1];
    for (int i = n - 1; i > 0; i--) bn[i] = (b.w[i] << s) | (s ? b.w[i - 1] >> (32 - s) : 0);
    bn[0] = b.w[0] << s;
    an[a.n] = s ? a.w[a.n - 1] >> (32 - s) : 0;
    for (int i = a.n - 1; i > 0; i--) an[i] = (a.w[i] << s) | (s ? a.w[i - 1] >> (32 - s) : 0);
    an[0] = a.w[0] << s;
    const uint64_t B = 1ull << 32;
    for (int j = m; j >= 0; j--) {
        uint64_t num = ((uint64_t)an[j + n] << 32) | an[j + n - 1];
        uint64_t qhat = num / bn[n - 1], rhat = num % bn[n - 1];
        while (qhat >= B || qhat * bn[n - 2] > ((rhat << 32) | an[j + n - 2])) {
            qhat--;
            rhat += bn[n - 1];
            if (rhat >= B) break;
        }
        int64_t borrow = 0;
        uint64_t carry = 0;
        for (int i = 0; i < n; i++) {
            uint64_t p = qhat * bn[i] + carry;
            carry = p >> 32;
            int64_t t = (int64_t)an[i + j] - borrow - (int64_t)(uint32_t)p;
            borrow = t < 0;
            an[i + j] = (uint32_t)t;
        }
        int64_t t = (int64_t)an[j + n] - borrow - (int64_t)carry;
        an[j + n] = (uint32_t)t;
        if (t < 0) {
            qhat--;
            uint64_t c = 0;
            for (int i = 0; i < n; i++) {
                uint64_t u = (uint64_t)an[i + j] + bn[i] + c;
                an[i + j] = (uint32_t)u;
                c = u >> 32;
            }
            an[j + n] += (uint32_t)c;
        }
        q.w[j] = (uint32_t)qhat;
    }
    q.n = m + 1;
    dn_trim(q);
    for (int i = 0; i < n; i++)
        if (an[i]) return false;
    return true;
}

// ---------------------------------------------------------------------------
// Signed integers and directed rounding
// ---------------------------------------------------------------------------
struct DI {
    bool neg;
    DN m;
};
__device__ __forceinline__ void di_fix(DI& r) {
    if (r.m.n == 0) r.neg = false;
}
__device__ __noinline__ void di_i64(DI& r, int64_t v) {
    r.neg = v < 0;
    dn_u64(r.m, v < 0 ? (uint64_t)(-(v + 1)) + 1 : (uint64_t)v);
}
__device__ __noinline__ void di_copy(DI& r, const DI& a) {
    r.neg = a.neg;
    dn_copy(r.m, a.m);
}
__device__ __noinline__ void di_add(DI& r, const DI& a, const DI& b) {  // r may alias
    if (a.neg == b.neg) {
        bool ng = a.neg;
        dn_add(r.m, a.m, b.m);
        r.neg = ng;
    } else if (dn_cmp(a.m, b.m) >= 0) {
        bool ng = a.neg;
        dn_sub(r.m, a.m, b.m);
        r.neg = ng;
    } else {
        bool ng = b.neg;
        dn_sub(r.m, b.m, a.m);
        r.neg = ng;
    }
    di_fix(r);
}
__device__ __noinline__ void di_mul(DI& r, const DI& a, const DI& b) {  // no alias
    dn_mul(r.m, a.m, b.m);
    r.neg = a.neg != b.neg;
    di_fix(r);
}
__device__ __noinline__ int di_cmp(const DI& a, const DI& b) {
    if (a.neg != b.neg) return a.neg ? -1 : 1;
    int c = dn_cmp(a.m, b.m);
    return a.neg ? -c : c;
}
// floor (up = false) or ceil of x / 2^s; s <= 0 shifts left exactly. r may alias
__device__ __noinline__ void di_shift(DI& r, const DI& x, int s, bool up) {
    bool ng = x.neg;
    if (s <= 0) dn_shl(r.m, x.m, -s);
    else dn_shr(r.m, x.m, s, up != ng);  // magnitude rounds away from zero exactly when the direction says so
    r.neg = ng;
    di_fix(r);
}
__device__ __noinline__ void di_div(DI& r, const DI& x, const DN& d, bool up) {  // floor / ceil of x / d; no alias
    bool ng = x.neg;
    bool exact = dn_div(r.m, x.m, d);
    if (!exact && up != ng) {
        DN one;
        dn_u64(one, 1);
        dn_add(r.m, r.m, one);
    }
    r.neg = ng;
    di_fix(r);
}
__device__ __noinline__ void di_div10(DI& r, const DI& x, int d, bool up) {  // floor / ceil of x / 10^d; alias ok
    di_copy(r, x);
    while (d > 0) {
        int s = min(d, 9);
        uint32_t div = 1;
        for (int i = 0; i < s; i++) div *= 10;
        bool ng = r.neg;
        bool exact = dn_div_small(r.m, r.m, div, false);
        if (!exact && up != ng) {
            DN one;
            dn_u64(one, 1);
            dn_add(r.m, r.m, one);
        }
        r.neg = ng;
        di_fix(r);
        d -= s;
    }
}

// ---------------------------------------------------------------------------
// Intervals at 2^-M
// ---------------------------------------------------------------------------
struct IV {
    DI lo, hi;
};
__device__ __noinline__ void iv_zero(IV& r) {
    r.lo.neg = r.hi.neg = false;
    r.lo.m.n = r.hi.m.n = 0;
}
__device__ __noinline__ void iv_one(IV& r, int M) {
    DN one;
    dn_u64(one, 1);
    dn_shl(r.lo.m, one, M);
    dn_copy(r.hi.m, r.lo.m);
    r.lo.neg = r.hi.neg = false;
}
__device__ __noinline__ void iv_add(IV& r, const IV& a, const IV& b) {  // alias ok
    di_add(r.lo, a.lo, b.lo);
    di_add(r.hi, a.hi, b.hi);
}
__device__ __noinline__ void iv_negate(IV& r) {  // in place
    DI t;
    di_copy(t, r.lo);
    di_copy(r.lo, r.hi);
    di_copy(r.hi, t);
    r.lo.neg = !r.lo.neg;
    r.hi.neg = !r.hi.neg;
    di_fix(r.lo);
    di_fix(r.hi);
}
__device__ __noinline__ void iv_sub(IV& r, const IV& a, const IV& b) {  // r must not alias b
    IV nb;
    di_copy(nb.lo, b.hi);
    di_copy(nb.hi, b.lo);
    nb.lo.neg = !nb.lo.neg;
    nb.hi.neg = !nb.hi.neg;
    di_fix(nb.lo);
    di_fix(nb.hi);
    iv_add(r, a, nb);
}
__device__ __noinline__ void iv_mul(IV& r, const IV& a, const IV& b, int M) {  // r must not alias
    DI p, mn, mx;
    const DI* A[2] = {&a.lo, &a.hi};
    const DI* Bv[2] = {&b.lo, &b.hi};
    for (int i = 0; i < 4; i++) {
        di_mul(p, *A[i >> 1], *Bv[i & 1]);
        if (i == 0 || di_cmp(p, mn) < 0) di_copy(mn, p);
        if (i == 0 || di_cmp(p, mx) > 0) di_copy(mx, p);
        if (bad(p.m)) { mn.m.n = POISON; mx.m.n = POISON; }
    }
    di_shift(r.lo, mn, M, false);
    di_shift(r.hi, mx, M, true);
}
__device__ __noinline__ void iv_div_pos(IV& r, const IV& a, const IV& b, int M) {  // b > 0; r must not alias
    DI x, q;
    const DI* A[2] = {&a.lo, &a.hi};
    const DN* D[2] = {&b.lo.m, &b.hi.m};
    bool first = true;
    for (int i = 0; i < 2; i++) {
        x.neg = A[i]->neg;
        dn_shl(x.m, A[i]->m, M);
        for (int j = 0; j < 2; j++) {
            di_div(q, x, *D[j], false);
            if (first || di_cmp(q, r.lo) < 0 || bad(q.m)) di_copy(r.lo, q);
            di_div(q, x, *D[j], true);
            if (first || di_cmp(q, r.hi) > 0 || bad(q.m)) di_copy(r.hi, q);
            first = false;
        }
    }
}
__device__ __noinline__ void iv_div_small(IV& r, const IV& a, uint32_t d) {  // alias ok
    bool ng = a.lo.neg;
    bool ex = dn_div_small(r.lo.m, a.lo.m, d, false);
    if (!ex && ng) { DN one; dn_u64(one, 1); dn_add(r.lo.m, r.lo.m, one); }
    r.lo.neg = ng;
    di_fix(r.lo);
    ng = a.hi.neg;
    ex = dn_div_small(r.hi.m, a.hi.m, d, false);
    if (!ex && !ng) { DN one; dn_u64(one, 1); dn_add(r.hi.m, r.hi.m, one); }
    r.hi.neg = ng;
    di_fix(r.hi);
}
__device__ __noinline__ void iv_shift_down(IV& r, const IV& a, int s) {  // alias ok
    di_shift(r.lo, a.lo, s, false);
    di_shift(r.hi, a.hi, s, true);
}

// ---------------------------------------------------------------------------
// The model: decimal constants (num * 10^p, |num| < 2^63) in constant memory, filled by the host
// ---------------------------------------------------------------------------
struct KConst {
    long long num;
    int p;
};
struct KShort {
    int alpha, imin, na, a[4];
};
struct KComp {
    int nshort;
    KShort s[2];
    int eta, kmin, kadd, nC, C[6], ret_kind;
};
__constant__ KConst K[64];
__constant__ KComp COMP[3];
__constant__ int RETA[5], RETB[6];

struct Dy {  // R = m 2^e, m odd
    DN m;
    int e;
};

// coef * mult * R^i at scale 2^M, coef = num * 10^p; outward, once. r must be distinct from scratch
__device__ __noinline__ void term(IV& r, const DI& coef, int p, const Dy& R, int i, int M) {
    DI top, t2;
    di_copy(top, coef);
    if (p > 0) {
        DI ten;
        for (int k = 0; k < p; k++) { di_i64(ten, 10); di_mul(t2, top, ten); di_copy(top, t2); }
    }
    DN mp;
    dn_u64(mp, 1);
    int n = i >= 0 ? i : -i;
    for (int k = 0; k < n; k++) {
        DN t;
        dn_mul(t, mp, R.m);
        dn_copy(mp, t);
    }
    if (i >= 0) {  // top * m^i * 2^(i e + M)
        DI X;
        X.neg = top.neg;
        dn_mul(X.m, top.m, mp);
        di_fix(X);
        int s = i * R.e + M;
        di_shift(r.lo, X, -s, false);
        di_shift(r.hi, X, -s, true);
    } else {        // top * 2^(M - n e) / m^n
        int s = M - n * R.e;
        DI X;
        if (s >= 0) { X.neg = top.neg; dn_shl(X.m, top.m, s); di_fix(X); }
        else di_copy(X, top);
        di_div(r.lo, X, mp, false);
        di_div(r.hi, X, mp, true);
        if (s < 0) { di_shift(r.lo, r.lo, -s, false); di_shift(r.hi, r.hi, -s, true); }
    }
    if (p < 0) { di_div10(r.lo, r.lo, -p, false); di_div10(r.hi, r.hi, -p, true); }
}
__device__ __noinline__ void kterm(IV& r, int idx, long long mult, const Dy& R, int i, int M) {
    DI c, k, t;
    di_i64(c, K[idx].num);
    di_i64(k, mult);
    di_mul(t, c, k);
    term(r, t, K[idx].p, R, i, M);
}

// e^-y for y = a / 2^M <= 2^-8: [lo, hi] * 2^M (outward Taylor, generous remainder)
__device__ __noinline__ void exp_taylor(DN& lo, DN& hi, const DN& a, int M) {
    DN tl, th, t, one;
    dn_u64(one, 1);
    dn_shl(tl, one, M);
    dn_copy(th, tl);
    DI sl, sh, x;
    sl.neg = sh.neg = false;
    dn_copy(sl.m, tl);
    dn_copy(sh.m, tl);
    for (uint32_t i = 1; i < 4096; i++) {
        dn_mul(t, tl, a);
        dn_shr(t, t, M, false);
        dn_div_small(tl, t, i, false);
        dn_mul(t, th, a);
        dn_shr(t, t, M, true);
        dn_div_small(th, t, i, true);
        x.neg = (i & 1);
        dn_copy(x.m, (i & 1) ? th : tl);   // lower sum: subtract the larger odd term, add the smaller even term
        di_fix(x);
        di_add(sl, sl, x);
        x.neg = (i & 1);
        dn_copy(x.m, (i & 1) ? tl : th);
        di_fix(x);
        di_add(sh, sh, x);
        if (bad(th) || dn_cmp(th, one) <= 0) break;
    }
    DN rr;
    dn_shl(rr, th, 1);
    DN two;
    dn_u64(two, 2);
    dn_add(rr, rr, two);
    x.neg = true;
    dn_copy(x.m, rr);
    di_fix(x);
    di_add(sl, sl, x);
    x.neg = false;
    di_add(sh, sh, x);
    if (sl.neg) lo.n = 0;
    else dn_copy(lo, sl.m);
    dn_copy(hi, sh.m);
}
// e^-x, x in [xlo, xhi] >= 0 at scale 2^S -> r at scale 2^M
__device__ __noinline__ void exp_neg(IV& r, const DI& xlo, const DI& xhi, int S, int M) {
    r.lo.neg = r.hi.neg = false;
    if (dn_bitlen(xlo.m) > S + 12) {  // x >= 4096: e^-x < 2^-5909 < 2^-M
        r.lo.m.n = 0;
        dn_u64(r.hi.m, 1);
        if (bad(xlo.m)) r.hi.m.n = POISON;
        return;
    }
    int k = max(0, dn_bitlen(xhi.m) - S) + 8;
    int sh = M - S - k;
    DN af, ac, unused;
    if (sh >= 0) { dn_shl(af, xlo.m, sh); dn_shl(ac, xhi.m, sh); }
    else { dn_shr(af, xlo.m, -sh, false); dn_shr(ac, xhi.m, -sh, true); }
    exp_taylor(r.lo.m, unused, ac, M);
    exp_taylor(unused, r.hi.m, af, M);
    for (int i = 0; i < k; i++) {
        DN t;
        dn_mul(t, r.lo.m, r.lo.m);
        dn_shr(r.lo.m, t, M, false);
        dn_mul(t, r.hi.m, r.hi.m);
        dn_shr(r.hi.m, t, M, true);
    }
}

// sum over the model (value, or dV/dR) at scale 2^M
__device__ __noinline__ void evaluate(IV& total, const Dy& R, bool ret, bool deriv, int M) {
    const int S = M + 8;
    iv_zero(total);
    IV e256;
    bool have256 = false;
    for (int ci = 0; ci < 3; ci++) {
        const KComp& c = COMP[ci];
        for (int si = 0; si < c.nshort; si++) {
            const KShort& st = c.s[si];
            IV x, E, poly, t, u;
            kterm(x, st.alpha, 1, R, 1, S);
            exp_neg(E, x.lo, x.hi, S, M);
            iv_zero(poly);
            for (int q = 0; q < st.na; q++) {
                int i = st.imin + q;
                if (K[st.a[q]].num == 0) continue;
                if (!deriv) {
                    kterm(t, st.a[q], 1, R, i, M);
                    iv_add(poly, poly, t);
                } else {
                    if (i != 0) { kterm(t, st.a[q], i, R, i - 1, M); iv_add(poly, poly, t); }
                    DI ca, cb, cc;
                    di_i64(ca, K[st.alpha].num);
                    di_i64(cb, K[st.a[q]].num);
                    di_mul(cc, ca, cb);
                    term(t, cc, K[st.alpha].p + K[st.a[q]].p, R, i, M);
                    iv_sub(u, poly, t);
                    poly = u;
                }
            }
            iv_mul(t, E, poly, M);
            iv_add(total, total, t);
        }
        IV xS, x, E, sum, piece, t, T, tn, D, dD, g, dg, one, etaK;
        kterm(xS, c.eta, 1, R, 1, S);
        iv_shift_down(x, xS, 8);
        DI lim;
        DN one256;
        dn_u64(one256, 256);
        lim.neg = false;
        dn_shl(lim.m, one256, S);
        bool far = di_cmp(xS.lo, lim) >= 0;
        if (!far) exp_neg(E, xS.lo, xS.hi, S, M);
        if (far && !have256) {
            DI a;
            a.neg = false;
            dn_shl(a.m, one256, M);
            exp_neg(e256, a, a, M, M);
            have256 = true;
        }
        iv_one(sum, M);
        iv_one(piece, M);
        iv_one(one, M);
        kterm(etaK, c.eta, 1, R, 0, M);
        int done = 0;
        for (int tix = 0; tix < c.nC; tix++) {
            int k = c.kmin + tix, n = 2 * k + c.kadd;
            if (!far) {
                for (; done < n; done++) {
                    iv_mul(t, piece, x, M);
                    iv_div_small(piece, t, (uint32_t)(done + 1));
                    iv_add(sum, sum, piece);
                }
                iv_mul(T, E, sum, M);
                iv_mul(tn, E, piece, M);
            } else {  // [0, (n+1) e^-256 256^n / n!] and [0, e^-256 256^n / n!]
                DN b, w;
                dn_copy(b, e256.hi.m);
                for (int i = 0; i < n; i++) { dn_mul_small(w, b, 256); dn_copy(b, w); }
                for (int i = 2; i <= n; i++) dn_div_small(b, b, (uint32_t)i, true);
                iv_zero(tn);
                dn_copy(tn.hi.m, b);
                iv_zero(T);
                dn_mul_small(T.hi.m, b, (uint32_t)(n + 1));
            }
            iv_mul(dD, tn, etaK, M);
            bool kmin = tix == 0;
            if (c.ret_kind == 1 && kmin && ret) {
                const int G = M + 64;
                IV N, Dn, dN, dDn, w, w2, num, den;
                iv_one(N, G);
                iv_one(Dn, G);
                iv_zero(dN);
                iv_zero(dDn);
                for (int mm = 0; mm < 5; mm++) {
                    kterm(w, RETA[mm], 1, R, mm + 1, G);
                    iv_add(N, N, w);
                    kterm(w, RETA[mm], mm + 1, R, mm, G);
                    iv_add(dN, dN, w);
                }
                for (int mm = 0; mm < 6; mm++) {
                    kterm(w, RETB[mm], 1, R, mm + 1, G);
                    iv_add(Dn, Dn, w);
                    kterm(w, RETB[mm], mm + 1, R, mm, G);
                    iv_add(dDn, dDn, w);
                }
                iv_div_pos(w, N, Dn, G);
                iv_shift_down(g, w, G - M);
                iv_mul(w, dN, Dn, G);
                iv_mul(w2, N, dDn, G);
                iv_sub(num, w, w2);
                iv_mul(den, Dn, Dn, G);
                iv_div_pos(w, num, den, G);
                iv_shift_down(dg, w, G - M);
                iv_sub(D, g, T);
                iv_add(dD, dD, dg);
            } else if (c.ret_kind == 2 && kmin && ret) {
                D = T;
                iv_negate(D);
            } else {
                iv_sub(D, one, T);
            }
            IV w, w2;
            if (!deriv) {
                kterm(w, c.C[tix], 1, R, -2 * k, M);
                iv_mul(w2, D, w, M);
                iv_sub(w, total, w2);
                total = w;
            } else {
                kterm(w, c.C[tix], 1, R, -2 * k, M);
                iv_mul(w2, dD, w, M);
                iv_sub(w, total, w2);
                total = w;
#if INJECT != 204  // defect 204: the +2k C D / R^(2k+1) term dropped
                kterm(w, c.C[tix], 2 * k, R, -2 * k - 1, M);
                iv_mul(w2, D, w, M);
                iv_add(total, total, w2);
#endif
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Rounding once, domain, one query
// ---------------------------------------------------------------------------
enum { A_OK, A_DOMAIN, A_HALT, A_INVALID, A_RANGE, A_PREC, A_WIDTH };
struct DQuery {
    int deriv, ret, fx, W, F;
    uint64_t raw;
};
struct DAns {
    int status, M;
    uint64_t raw;
};

// nearest-even binary64 of x / 2^M; returns false on overflow
__device__ __noinline__ bool round_b64(const DI& x, int M, uint64_t* out) {
    if (x.m.n == 0) { *out = 0; return true; }
    int L = dn_bitlen(x.m);
    int E = L - 1 - M;                  // 2^E <= |v| < 2^(E+1)
    int eu = max(E - 52, -1074);        // exponent of the last kept bit
    int drop = eu + M;                  // bits of m below that position
    uint64_t q;
    if (drop <= 0) {
        DN t;
        dn_shl(t, x.m, -drop);
        q = (uint64_t)t.w[0] | (t.n > 1 ? (uint64_t)t.w[1] << 32 : 0);
    } else {
        DN t;
        dn_shr(t, x.m, drop, false);
        q = (uint64_t)t.w[0] * (t.n > 0) | (t.n > 1 ? (uint64_t)t.w[1] << 32 : 0);
        bool half = (x.m.w[(drop - 1) >> 5] >> ((drop - 1) & 31)) & 1;
        bool sticky = !dn_low_zero(x.m, drop - 1);
#if INJECT == 201
        half = false;  // defect: truncation instead of nearest
#endif
        if (half && (sticky || (q & 1))) q++;
    }
    if (q == (1ull << 53)) { q = 1ull << 52; eu++; }
    uint64_t s = x.neg ? 1ull << 63 : 0;
    if (q >= (1ull << 52)) {
        int field = eu + 1075;
        if (field >= 0x7FF) return false;
        *out = s | ((uint64_t)field << 52) | (q - (1ull << 52));
    } else {
        *out = s | q;
    }
    return true;
}
// nearest-even FX(W, F) of x / 2^M; returns false when out of range
__device__ __noinline__ bool round_fx(const DI& x, int M, int W, int F, uint64_t* out) {
    DI q;
    int s = M - F;
    dn_shr(q.m, x.m, s, false);
    bool half = s > 0 && ((x.m.n > ((s - 1) >> 5)) && ((x.m.w[(s - 1) >> 5] >> ((s - 1) & 31)) & 1));
    bool sticky = s > 1 && !dn_low_zero(x.m, s - 1);
    // |x| = q + f, f in [0, 1); nearest-even of the magnitude equals that of the signed value (symmetric)
    bool odd = q.m.n && (q.m.w[0] & 1);
    if (half && (sticky || odd)) { DN one; dn_u64(one, 1); dn_add(q.m, q.m, one); }
    q.neg = x.neg;
    di_fix(q);
    int L = dn_bitlen(q.m);
    bool ok = L <= W - 1 || (q.neg && L == W && dn_low_zero(q.m, W - 1));
    if (!ok || W > 64) return false;
    uint64_t mag = q.m.n ? ((uint64_t)q.m.w[0] | (q.m.n > 1 ? (uint64_t)q.m.w[1] << 32 : 0)) : 0;
    *out = q.neg ? 0 - mag : mag;
    return true;
}

__device__ __noinline__ void answer(const DQuery& Q, DAns* A, int lane) {
    A->M = 0;
    A->raw = 0;
    Dy R;
    if (Q.fx) {
        long long v = (long long)Q.raw;
        if (v <= 0) { A->status = A_DOMAIN; return; }
        dn_u64(R.m, (uint64_t)v);
        R.e = -Q.F;
    } else {
        uint64_t b = Q.raw;
        int field = (int)((b >> 52) & 0x7FF);
        if (field == 0x7FF) { A->status = A_INVALID; return; }
        if ((b >> 63) || (b << 1) == 0) { A->status = A_DOMAIN; return; }
        uint64_t frac = b & ((1ull << 52) - 1);
        dn_u64(R.m, field ? frac | (1ull << 52) : frac);
        R.e = field ? field - 1075 : -1074;
    }
    while (!(R.m.w[0] & 1)) { dn_shr(R.m, R.m, 1, false); R.e++; }
    // R < 1.2 / 0.529177210903  <=>  m 2^e 529177210903 < 1200000000000
    {
        DN l, r, t, c;
        dn_u64(c, 529177210903ull);
        dn_mul(l, R.m, c);
        dn_u64(r, 1200000000000ull);
        if (R.e >= 0) { dn_shl(t, l, R.e); dn_copy(l, t); }
        else { dn_shl(t, r, -R.e); dn_copy(r, t); }
        if (dn_cmp(l, r) < 0) { A->status = A_DOMAIN; return; }
    }
    int L = dn_bitlen(R.m);
    if (L + R.e > 21 || (L + R.e == 21 && !(R.m.n == 1 && R.m.w[0] == 1))) { A->status = A_RANGE; return; }
    int M = M0;
#ifdef AR2_FORCE_M
    M = AR2_FORCE_M;  // measurement build only: every query at this precision
#endif
    for (int attempt = 0; attempt < NATIVE_AR2_MAX_ATTEMPTS; attempt++, M *= 2) {
        IV v;
        int Mx = M;
#if INJECT == 205
        if (lane >= 32) Mx = 64;  // defect: threads past the first warp at a fixed low precision
#endif
        evaluate(v, R, Q.ret != 0, Q.deriv != 0, Mx);
        if (Q.deriv) iv_negate(v);
        if (bad(v.lo.m) || bad(v.hi.m)) { A->status = A_WIDTH; return; }
        uint64_t a = 0, b = 0;
        bool oa, ob;
        if (Q.fx) { oa = round_fx(v.lo, Mx, Q.W, Q.F, &a); ob = round_fx(v.hi, Mx, Q.W, Q.F, &b); }
        else { oa = round_b64(v.lo, Mx, &a); ob = round_b64(v.hi, Mx, &b); }
#if INJECT == 202
        ob = oa; b = a;  // defect: no refinement
#endif
        if (oa == ob && a == b) {
            A->status = oa ? A_OK : A_HALT;
            A->raw = a;
            A->M = Mx;
            return;
        }
    }
    A->status = A_PREC;
}

__global__ void eval_kernel(int base, int count, const DQuery* q, DAns* out) {
    int stride = gridDim.x * blockDim.x;
    for (int local = blockIdx.x * blockDim.x + threadIdx.x; local < count; local += stride)
        answer(q[base + local], &out[base + local], threadIdx.x);
}

// ---------------------------------------------------------------------------
// Host
// ---------------------------------------------------------------------------
#define CK(x)                                                                                            \
    do {                                                                                                 \
        cudaError_t err = (x);                                                                           \
        if (err != cudaSuccess) {                                                                        \
            fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(err), __FILE__, __LINE__);    \
            exit(4);                                                                                     \
        }                                                                                                \
    } while (0)

static KConst kconst(const char* s) {  // "d.ddde+x" -> num * 10^p exactly (host, separate from ar2::dec)
    long long num = 0;
    int frac = 0, exp10 = 0;
    bool neg = false, point = false;
    const char* c = s;
    if (*c == '-' || *c == '+') neg = *c++ == '-';
    for (; *c && *c != 'e' && *c != 'E'; c++) {
        if (*c == '.') { point = true; continue; }
        num = num * 10 + (*c - '0');
        if (point) frac++;
    }
    if (*c) exp10 = atoi(c + 1);
    return KConst{neg ? -num : num, exp10 - frac};
}

int main(int argc, char** argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: ar2_b2 <block_size> <grid_blocks> <launch_chunk> <queries.txt> <answers.txt>\n");
        return 2;
    }
    const int B = std::max(1, atoi(argv[1]));
    const int want_grid = atoi(argv[2]), want_chunk = atoi(argv[3]);
    std::vector<ar2::Query> qs = ar2::read_queries(argv[4]);
    // model constants into constant memory (the same decimals as S2_ar2_pot.f90)
    std::vector<KConst> k;
    auto add = [&k](const char* s) { k.push_back(kconst(s)); return (int)k.size() - 1; };
    KComp comps[3];
    const auto& model = ar2::model();
    for (int ci = 0; ci < 3; ci++) {
        const ar2::Component& c = model[ci];
        KComp& d = comps[ci];
        d.nshort = (int)c.shorts.size();
        for (int si = 0; si < d.nshort; si++) {
            d.s[si].alpha = add(c.shorts[si].alpha);
            d.s[si].imin = c.shorts[si].imin;
            d.s[si].na = (int)c.shorts[si].a.size();
            for (int q = 0; q < d.s[si].na; q++) d.s[si].a[q] = add(c.shorts[si].a[q]);
        }
        d.eta = add(c.eta);
        d.kmin = c.kmin;
        d.kadd = c.kadd;
        d.nC = (int)c.C.size();
        for (int q = 0; q < d.nC; q++) d.C[q] = add(c.C[q]);
        d.ret_kind = c.ret_kind;
    }
    int ra[5], rb[6];
    for (int i = 0; i < 5; i++) ra[i] = add(ar2::RET_A[i]);
    for (int i = 0; i < 6; i++) rb[i] = add(ar2::RET_B[i]);
    CK(cudaMemcpyToSymbol(K, k.data(), k.size() * sizeof(KConst)));
    CK(cudaMemcpyToSymbol(COMP, comps, sizeof comps));
    CK(cudaMemcpyToSymbol(RETA, ra, sizeof ra));
    CK(cudaMemcpyToSymbol(RETB, rb, sizeof rb));

    std::vector<DQuery> dq;
    for (const ar2::Query& q : qs) {
        DQuery d{q.qty == 'F', q.ret, q.p.fx, q.p.W, q.p.F, 0};
        d.raw = q.p.fx ? (uint64_t)strtoll(q.raw.c_str(), nullptr, 10) : strtoull(q.raw.c_str(), nullptr, 16);
        if (q.p.fx && q.p.W > 64) { fprintf(stderr, "B2 implements FX with W <= 64 only\n"); return 5; }
        dq.push_back(d);
    }
    const int n = (int)dq.size();
    CK(cudaDeviceSetLimit(cudaLimitStackSize, 60 * 1024));
    DQuery* g_q = nullptr;
    DAns* g_a = nullptr;
    CK(cudaMalloc(&g_q, std::max(1, n) * sizeof(DQuery)));
    CK(cudaMalloc(&g_a, std::max(1, n) * sizeof(DAns)));
    if (n) CK(cudaMemcpy(g_q, dq.data(), n * sizeof(DQuery), cudaMemcpyHostToDevice));
    CK(cudaMemset(g_a, 0xFF, std::max(1, n) * sizeof(DAns)));  // unanswered queries read back as garbage status
    const int chunk = want_chunk > 0 ? want_chunk : std::max(1, n);
    for (int base = 0; base < n; base += chunk) {
        int count = std::min(chunk, n - base);
        int grid = want_grid > 0 ? want_grid : (count + B - 1) / B;
        eval_kernel<<<grid, B>>>(base, count, g_q, g_a);
        CK(cudaGetLastError());
        CK(cudaDeviceSynchronize());
    }
#ifdef AR2_TRACK_WIDTH
    int maxl = 0;
    CK(cudaMemcpyFromSymbol(&maxl, g_max_limbs, sizeof maxl));
    fprintf(stderr, "max_limbs %d\n", maxl);
#endif
    std::vector<DAns> ans(n);
    if (n) CK(cudaMemcpy(ans.data(), g_a, n * sizeof(DAns), cudaMemcpyDeviceToHost));
    std::vector<std::string> out;
    char buf[80];
    for (int i = 0; i < n; i++) {
        const DAns& a = ans[i];
        switch (a.status) {
            case A_OK:
                if (dq[i].fx) snprintf(buf, sizeof buf, "ok %lld %d", (long long)a.raw, a.M);
                else snprintf(buf, sizeof buf, "ok %016llx %d", (unsigned long long)a.raw, a.M);
                break;
            case A_DOMAIN: snprintf(buf, sizeof buf, "domain physics_domain_exceeded"); break;
            case A_HALT: snprintf(buf, sizeof buf, "halt overflow"); break;
            case A_INVALID: snprintf(buf, sizeof buf, "refuse invalid_input"); break;
            case A_RANGE: snprintf(buf, sizeof buf, "refuse beyond_native_range"); break;
            case A_PREC: snprintf(buf, sizeof buf, "refuse device_precision_cap"); break;
            case A_WIDTH: snprintf(buf, sizeof buf, "refuse device_width"); break;
            default: fprintf(stderr, "query %d was never answered\n", i); return 8;
        }
        out.push_back(buf);
    }
    ar2::write_answers(argv[5], out);
    return 0;
}
