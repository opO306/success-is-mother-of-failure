// GPU_FORCE_FEASIBILITY_V1 (G0): E2 scalar G(R^2) interval on the GPU (protocol.json 'gpu_design').
//
// One thread evaluates one R^2 interval end-to-end by interpreting the straight-line program traced from the frozen
// rewrite_pilot_a3.rwforce.RwForce.__call__ (rw:R1+R2) at precision p. Every interval operation replicates mpmath 1.3.0
// (pure-python backend) libmpi / libmpf / libelefun exactly:
//   mpi_add / mpi_sub / mpi_mul (with its sign-case branches) / mpi_div / mpi_neg / mpi_sqrt / mpi_exp,
//   mpf_add (incl. the far-exponent perturbation), mpf_mul, mpf_div (extra bits + sticky), mpf_sqrt (isqrt / sqrtrem),
//   mpf_exp (wp = p + 14, ln2 reduction with floor divmod, exp_basecase), normalize with round_floor / round_ceiling.
// Constants (the lifted plan constants, ln2_fixed(wp + mag), r = int(wp ** 0.5)) are uploaded by the host.
//
// Statuses: 0 OK, 1 DOMAIN_UNPROVEN, 2 REFUSED_DEVICE_WIDTH (poison: never truncated, never wrapped),
//           3 REFUSED_DEVICE_PRECISION (unsupported exp branch / argument, or a non-finite interval result).
// No block or grid size may change a bit: grid-stride loop, thread and block ids only select the sample.
//
// Provenance: the DN magnitude primitives below (struct DN ... dn_div) are copied from a_physics_native/ar2_b2.cu
// lines 44-256 (sha256_lf a2393150c26b22b4ae6d8f392fa404fda36df31552d4d39530ef7dfe297ed1f5); changes: the width
// limit is the runtime d_wl (<= DL) instead of the constant DL, and the fault hooks 3, 4, 8 (tests only). Everything
// else is new.
#include <cuda_runtime.h>
#include <stdint.h>
#include <chrono>

#define DL 16       // workspace limbs (512 bits)
#define ML 6        // mantissa limbs (192 bits): p <= 192
#define POISON (DL + 1)
#define NREG 16
#define MAXCODE 512
#define MAXCONST 256
#define MAG_LO 2
#define NMAG 23     // ln2 table for mag 2 .. 24
#define WORDS_MP 11
#define WORDS_MPI 22
#define WORDS_OUT 48
#define FLOOR 0
#define CEIL 1

#ifdef _WIN32
#define G0_API extern "C" __declspec(dllexport)
#else
#define G0_API extern "C"
#endif

__device__ int d_wl;     // work-limb limit (<= DL)
__device__ int d_fault;  // 0 in every evidence run

// ---------------------------------------------------------------------------
// Device magnitudes (copied from ar2_b2.cu, see header)
// ---------------------------------------------------------------------------
struct DN {
    int n;  // limbs in use; POISON = overflowed
    uint32_t w[DL];
};
__device__ __forceinline__ bool bad(const DN& a) { return a.n == POISON; }
__device__ __noinline__ void dn_trim(DN& r) {
    if (bad(r)) return;
    while (r.n > 0 && r.w[r.n - 1] == 0) r.n--;
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
__device__ __noinline__ int dn_cmp(const DN& a, const DN& b) {
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
        if (d_fault == 3) c = 0;  // fault 3: carry dropped
    }
    if (c) {
        if (n >= d_wl) {
            if (d_fault == 8) { r.n = n; dn_trim(r); return; }  // fault 8: overflow ignored
            r.n = POISON;
            return;
        }
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
    if (dn_bitlen(a) + dn_bitlen(b) > d_wl * 32 && d_fault != 8) { r.n = POISON; return; }
    int n = min(a.n + b.n, d_wl);
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
    if (d_fault == 4 && n > 1) r.w[n - 1] = 0;  // fault 4: high limb dropped
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
        if (r.n >= d_wl) {
            if (d_fault == 8) { dn_trim(r); return; }
            r.n = POISON;
            return;
        }
        r.w[r.n++] = (uint32_t)c;
    }
    dn_trim(r);
}
__device__ __noinline__ void dn_shl(DN& r, const DN& a, int s) {  // r may alias
    if (bad(a)) { r.n = POISON; return; }
    if (!a.n) { r.n = 0; return; }
    int wq = s >> 5, b = s & 31;
    int n = a.n + wq + 1;
    if (n > d_wl) {
        if (dn_bitlen(a) + s > d_wl * 32 && d_fault != 8) { r.n = POISON; return; }
        n = d_wl;
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
// New: magnitude helpers
// ---------------------------------------------------------------------------
__device__ __noinline__ int dn_ctz(const DN& a) {  // a != 0
    int i = 0;
    while (i < a.n && a.w[i] == 0) i++;
    return i * 32 + __ffs(a.w[i]) - 1;
}
__device__ __noinline__ bool dn_is_one(const DN& a) { return a.n == 1 && a.w[0] == 1; }
// q = floor(a / b), r = a - q b (q, r must not alias a or b)
__device__ __noinline__ void dn_divmod(DN& q, DN& r, const DN& a, const DN& b) {
    dn_div(q, a, b);
    DN t;
    dn_mul(t, q, b);
    if (bad(t) || bad(q)) { q.n = POISON; r.n = POISON; return; }
    dn_sub(r, a, t);
}
// floor(sqrt(a)) with remainder a - s^2 (bit-by-bit; s, rem must not alias a)
__device__ __noinline__ void dn_isqrt(DN& s, DN& rem, const DN& a) {
    if (bad(a)) { s.n = POISON; rem.n = POISON; return; }
    s.n = 0;
    dn_copy(rem, a);
    if (!a.n) return;
    int top = (dn_bitlen(a) - 1) & ~1;  // highest even bit position <= msb
    DN bit, t;
    dn_u64(bit, 1);
    dn_shl(bit, bit, top);
    while (bit.n) {
        dn_add(t, s, bit);              // t = s + bit
        if (dn_cmp(rem, t) >= 0) {
            dn_sub(rem, rem, t);
            dn_shr(s, s, 1, false);
            dn_add(s, s, bit);
        } else {
            dn_shr(s, s, 1, false);
        }
        dn_shr(bit, bit, 2, false);
    }
}

// signed integer = (neg, magnitude); zero is never negative
struct SN {
    bool neg;
    DN m;
};
__device__ __forceinline__ void sn_fix(SN& x) { if (!x.m.n) x.neg = false; }
__device__ __noinline__ void sn_add(SN& r, const SN& a, const SN& b) {  // r may alias
    if (a.neg == b.neg) {
        dn_add(r.m, a.m, b.m);
        r.neg = a.neg;
    } else if (dn_cmp(a.m, b.m) >= 0) {
        dn_sub(r.m, a.m, b.m);
        r.neg = a.neg;
    } else {
        DN t;
        dn_sub(t, b.m, a.m);
        dn_copy(r.m, t);
        r.neg = b.neg;
    }
    sn_fix(r);
}
// Python a >> s (floor) for a signed value
__device__ __noinline__ void sn_shr_floor(SN& r, const SN& a, int s) {
    dn_shr(r.m, a.m, s, a.neg);
    r.neg = a.neg;
    sn_fix(r);
}

// ---------------------------------------------------------------------------
// mpf: (sign, odd mantissa, exponent, bitcount) as in mpmath; zero: n == 0
// ---------------------------------------------------------------------------
struct MP {
    int sign;
    int n;
    int bc;
    long long exp;
    uint32_t m[ML];
};
struct MPI {
    MP a, b;
};
struct Ctx {
    int prec;
    int flags;  // 1 width, 2 precision / non-finite
};
__device__ __forceinline__ void mp_zero(MP& r) { r.sign = 0; r.n = 0; r.bc = 0; r.exp = 0; }
__device__ __forceinline__ int mp_sgn(const MP& x) { return x.n ? (x.sign ? -1 : 1) : 0; }
__device__ __noinline__ void mp_man(DN& d, const MP& x) {
    d.n = x.n;
    for (int i = 0; i < x.n; i++) d.w[i] = x.m[i];
}
// mpmath normalize(sign, man, exp, bc, prec, rnd) with rnd in {round_floor, round_ceiling}
__device__ __noinline__ void normalize(MP& r, int sign, const DN& man, long long exp, Ctx& c, int rnd) {
    if (bad(man)) { c.flags |= 1; mp_zero(r); return; }
    int bc = dn_bitlen(man);
    if (!bc) { mp_zero(r); return; }
    DN m;
    dn_copy(m, man);
    int n = bc - c.prec;
    if (n > 0) {
        bool down = (rnd == FLOOR) ? (sign == 0) : (sign == 1);  // shifts_down[rnd][sign]
        dn_shr(m, m, n, !down);
        exp += n;
    }
    if (bad(m)) { c.flags |= 1; mp_zero(r); return; }
    int tz = dn_ctz(m);
    if (tz) {
        dn_shr(m, m, tz, false);
        exp += tz;
    }
    if (m.n > ML) { c.flags |= 1; mp_zero(r); return; }
    r.sign = sign;
    r.n = m.n;
    r.bc = dn_bitlen(m);
    r.exp = exp;
    for (int i = 0; i < m.n; i++) r.m[i] = m.w[i];
}
// mpf_add(s, t, prec, rnd, _sub) - literal replication incl. the far-exponent perturbation
__device__ __noinline__ void mpf_add(MP& r, const MP& s, const MP& t, Ctx& c, int rnd, int sub) {
    int tsign = t.sign ^ sub;
    if (s.n && t.n) {
        DN sm, tm, man;
        mp_man(sm, s);
        mp_man(tm, t);
        long long offset = s.exp - t.exp;
        if (offset > 100 || offset < -100) {
            const MP& big = offset > 0 ? s : t;
            const MP& small = offset > 0 ? t : s;
            int bsign = offset > 0 ? s.sign : tsign, ssign = offset > 0 ? tsign : s.sign;
            long long delta = (long long)big.bc + big.exp - small.bc - small.exp;
            if (delta > c.prec + 4) {
                int off = c.prec + 4;
                DN bm, one;
                mp_man(bm, big);
                dn_shl(bm, bm, off);
                dn_u64(one, 1);
                if (bsign == ssign) dn_add(bm, bm, one);
                else dn_sub(bm, bm, one);
                normalize(r, bsign, bm, big.exp - off, c, rnd);
                return;
            }
        }
        long long e;
        SN a, b, sum;
        if (offset >= 0) {
            dn_shl(a.m, sm, (int)offset);
            dn_copy(b.m, tm);
            e = t.exp;
        } else {
            dn_copy(a.m, sm);
            dn_shl(b.m, tm, (int)-offset);
            e = s.exp;
        }
        a.neg = s.sign;
        b.neg = tsign;
        sn_fix(a);
        sn_fix(b);
        sn_add(sum, a, b);
        if (bad(sum.m)) { c.flags |= 1; mp_zero(r); return; }
        normalize(r, sum.neg ? 1 : 0, sum.m, e, c, rnd);
        return;
    }
    DN m;
    if (!s.n) {
        if (t.n) { mp_man(m, t); normalize(r, tsign, m, t.exp, c, rnd); }
        else mp_zero(r);
        return;
    }
    mp_man(m, s);
    normalize(r, s.sign, m, s.exp, c, rnd);
}
__device__ __noinline__ void mpf_mul(MP& r, const MP& s, const MP& t, Ctx& c, int rnd) {
    if (!s.n || !t.n) { mp_zero(r); return; }
    DN sm, tm, p;
    mp_man(sm, s);
    mp_man(tm, t);
    dn_mul(p, sm, tm);
    normalize(r, s.sign ^ t.sign, p, s.exp + t.exp, c, rnd);
}
// exact product as (sign, magnitude, exponent) for mpi_mul's general case
struct XP {
    int sign;
    DN m;
    long long exp;
};
__device__ __noinline__ void xp_mul(XP& r, const MP& s, const MP& t) {
    DN sm, tm;
    mp_man(sm, s);
    mp_man(tm, t);
    if (!s.n || !t.n) { r.sign = 0; r.m.n = 0; r.exp = 0; return; }
    dn_mul(r.m, sm, tm);
    r.sign = s.sign ^ t.sign;
    r.exp = s.exp + t.exp;
}
__device__ __noinline__ int xp_cmp(const XP& x, const XP& y) {  // exact value comparison
    int sx = x.m.n ? (x.sign ? -1 : 1) : 0, sy = y.m.n ? (y.sign ? -1 : 1) : 0;
    if (sx != sy) return sx < sy ? -1 : 1;
    if (!sx) return 0;
    long long tx = dn_bitlen(x.m) + x.exp, ty = dn_bitlen(y.m) + y.exp;
    int mag;
    if (tx != ty) {
        mag = tx < ty ? -1 : 1;
    } else {
        DN a, b;
        if (x.exp >= y.exp) { dn_shl(a, x.m, (int)(x.exp - y.exp)); dn_copy(b, y.m); }
        else { dn_copy(a, x.m); dn_shl(b, y.m, (int)(y.exp - x.exp)); }
        mag = dn_cmp(a, b);
    }
    return sx > 0 ? mag : -mag;
}
__device__ __noinline__ void mpf_div(MP& r, const MP& s, const MP& t, Ctx& c, int rnd) {
    if (!t.n) { c.flags |= 2; mp_zero(r); return; }
    if (!s.n) { mp_zero(r); return; }
    int sign = s.sign ^ t.sign;
    DN sm, tm;
    mp_man(sm, s);
    mp_man(tm, t);
    if (dn_is_one(tm)) { normalize(r, sign, sm, s.exp - t.exp, c, rnd); return; }
    int extra = c.prec - s.bc + t.bc + 5;
    if (extra < 5) extra = 5;
    DN num, q, rem;
    dn_shl(num, sm, extra);
    dn_divmod(q, rem, num, tm);
    if (bad(q)) { c.flags |= 1; mp_zero(r); return; }
    if (rem.n) {
        DN one;
        dn_shl(q, q, 1);
        dn_u64(one, 1);
        dn_add(q, q, one);
        extra += 1;
    }
    normalize(r, sign, q, s.exp - t.exp - extra, c, rnd);
}
__device__ __noinline__ void mpf_sqrt(MP& r, const MP& s, Ctx& c, int rnd) {
    if (s.sign && s.n) { c.flags |= 2; mp_zero(r); return; }  // ComplexResult in mpmath
    if (!s.n) { mp_zero(r); return; }
    DN man;
    mp_man(man, s);
    long long exp = s.exp;
    int bc = s.bc;
    if (exp & 1) {
        exp -= 1;
        dn_shl(man, man, 1);
        bc += 1;
    } else if (dn_is_one(man)) {
        normalize(r, 0, man, exp / 2, c, rnd);
        return;
    }
    int shift = 2 * c.prec - bc + 4;
    if (shift < 4) shift = 4;
    shift += shift & 1;
    DN x, root, rem;
    dn_shl(x, man, shift);
    dn_isqrt(root, rem, x);
    if (rnd == CEIL && !(d_fault == 6)) {  // fault 6: the floor root also for the upper end
        if (rem.n) {
            DN one;
            dn_shl(root, root, 1);
            dn_u64(one, 1);
            dn_add(root, root, one);
            shift += 2;
        }
    }
    normalize(r, 0, root, (exp - shift) / 2, c, rnd);  // exp - shift is even
}
__device__ __noinline__ void mpf_neg(MP& r, const MP& s, Ctx& c, int rnd) {
    if (!s.n) { mp_zero(r); return; }
    DN m;
    mp_man(m, s);
    normalize(r, 1 - s.sign, m, s.exp, c, rnd);
}

// ---------------------------------------------------------------------------
// mpf_exp (libelefun) - literal replication for prec <= 600
// ---------------------------------------------------------------------------
__constant__ int c_prec, c_wp, c_r;
__constant__ uint32_t c_ln2[NMAG * (DL + 1)];  // [n, limbs...] for mag = MAG_LO + k

// exp_basecase(x, prec) with prec = wp; x signed fixed point
__device__ __noinline__ void exp_basecase(DN& out, const SN& x, int prec, int r, Ctx& c) {
    prec += r;
    DN s0, s1, a, x2, t, one;
    dn_u64(one, 1);
    dn_shl(s0, one, prec);
    dn_copy(s1, s0);
    dn_mul(t, x.m, x.m);
    dn_shr(x2, t, prec, false);
    dn_copy(a, x2);
    uint32_t k = 2;
    while (a.n && !bad(a)) {
        dn_div_small(a, a, k, false); dn_add(s0, s0, a); k++;
        dn_div_small(a, a, k, false); dn_add(s1, s1, a); k++;
        dn_mul(t, a, x2);
        dn_shr(a, t, prec, false);
    }
    SN s1x, s0s, s;
    dn_mul(s1x.m, s1, x.m);
    s1x.neg = x.neg;
    sn_fix(s1x);
    sn_shr_floor(s1x, s1x, prec);       // (s1 * x) >> prec, floor
    dn_copy(s0s.m, s0);
    s0s.neg = false;
    sn_add(s, s0s, s1x);
    if (s.neg) { c.flags |= 2; out.n = 0; return; }  // cannot happen for the replicated ranges; refused if it does
    DN sq;
    for (int i = 0; i < r; i++) {
        dn_mul(sq, s.m, s.m);
        dn_shr(s.m, sq, prec, false);
    }
    dn_shr(out, s.m, r, false);
}
__device__ __noinline__ void mpf_exp(MP& res, const MP& x, Ctx& c, int rnd) {
    if (!x.n) {  // exp(0) = 1 exactly
        res.sign = 0; res.n = 1; res.bc = 1; res.exp = 0; res.m[0] = 1;
        return;
    }
    int prec = c.prec;
    int wp = prec + 14, r = c_r;
    if (d_fault == 5) { wp = prec; }  // fault 5: no guard bits, still reported OK
    long long mag = (long long)x.bc + x.exp;
    if (prec > 600 || mag < -wp) { c.flags |= 2; mp_zero(res); return; }  // unimplemented mpmath branches
    SN t;
    long long n = 0;
    DN man;
    mp_man(man, x);
    if (mag > 1) {
        int k = (int)mag - MAG_LO;
        if (k >= NMAG) { c.flags |= 2; mp_zero(res); return; }
        int wpmod = wp + (int)mag;
        long long offset = x.exp + wpmod;
        if (offset >= 0) {
            dn_shl(t.m, man, (int)offset);
            t.neg = x.sign;
        } else {
            SN mm;
            dn_copy(mm.m, man);
            mm.neg = x.sign;
            sn_shr_floor(t, mm, (int)-offset);
        }
        sn_fix(t);
        DN lg2;
        const uint32_t* L = c_ln2 + k * (DL + 1);
        lg2.n = (int)L[0];
        for (int i = 0; i < lg2.n; i++) lg2.w[i] = L[1 + i];
        if (d_fault == 5) {  // the table is for wp = p + 14: rescale the constant to the faulty wp
            dn_shr(lg2, lg2, 14, false);
        }
        DN q, rm;
        dn_divmod(q, rm, t.m, lg2);  // magnitudes
        if (bad(q) || q.n > 1) { c.flags |= bad(q) ? 1 : 2; mp_zero(res); return; }
        long long qv = q.n ? (long long)q.w[0] : 0;
        if (t.neg) {  // Python floor divmod of a negative value
            if (rm.n) {
                qv = -qv - 1;
                dn_sub(rm, lg2, rm);
            } else {
                qv = -qv;
            }
        }
        n = qv;
        SN tt;
        dn_copy(tt.m, rm);
        tt.neg = false;
        dn_shr(t.m, tt.m, (int)mag, false);  // t >>= mag (t >= 0)
        t.neg = false;
    } else {
        long long offset = x.exp + wp;
        if (offset >= 0) {
            dn_shl(t.m, man, (int)offset);
            t.neg = x.sign;
        } else {
            SN mm;
            dn_copy(mm.m, man);
            mm.neg = x.sign;
            sn_shr_floor(t, mm, (int)-offset);
        }
        sn_fix(t);
    }
    DN m;
    exp_basecase(m, t, wp, r, c);
    if (c.flags) { mp_zero(res); return; }
    normalize(res, 0, m, n - wp, c, rnd);
}

// ---------------------------------------------------------------------------
// mpi (libmpi) - literal replication
// ---------------------------------------------------------------------------
__device__ __noinline__ void mpi_add(MPI& r, const MPI& s, const MPI& t, Ctx& c) {
    MP a, b;
    mpf_add(a, s.a, t.a, c, FLOOR, 0);
    mpf_add(b, s.b, t.b, c, d_fault == 2 ? FLOOR : CEIL, 0);  // fault 2: upper end rounded inward
    r.a = a;
    r.b = b;
}
__device__ __noinline__ void mpi_sub(MPI& r, const MPI& s, const MPI& t, Ctx& c) {
    MP a, b;
    mpf_add(a, s.a, t.b, c, FLOOR, 1);
    mpf_add(b, s.b, t.a, c, CEIL, 1);
    r.a = a;
    r.b = b;
}
__device__ __noinline__ void mpi_neg(MPI& r, const MPI& s, Ctx& c) {
    MP a, b;
    mpf_neg(a, s.b, c, FLOOR);
    mpf_neg(b, s.a, c, CEIL);
    r.a = a;
    r.b = b;
}
__device__ __noinline__ void mpi_mul(MPI& r, const MPI& s, const MPI& t, Ctx& c) {
    int sas = mp_sgn(s.a), sbs = mp_sgn(s.b), tas = mp_sgn(t.a), tbs = mp_sgn(t.b);
    MP a, b;
    int lo = d_fault == 1 ? CEIL : FLOOR;  // fault 1: lower end rounded inward
    if (sas == 0 && sbs == 0) { mp_zero(r.a); mp_zero(r.b); return; }
    if (tas == 0 && tbs == 0) { mp_zero(r.a); mp_zero(r.b); return; }
    if (sas >= 0) {
        if (tas >= 0) { mpf_mul(a, s.a, t.a, c, lo); mpf_mul(b, s.b, t.b, c, CEIL); }
        else if (tbs <= 0) { mpf_mul(a, s.b, t.a, c, lo); mpf_mul(b, s.a, t.b, c, CEIL); }
        else { mpf_mul(a, s.b, t.a, c, lo); mpf_mul(b, s.b, t.b, c, CEIL); }
    } else if (sbs <= 0) {
        if (tas >= 0) { mpf_mul(a, s.a, t.b, c, lo); mpf_mul(b, s.b, t.a, c, CEIL); }
        else if (tbs <= 0) { mpf_mul(a, s.b, t.b, c, lo); mpf_mul(b, s.a, t.a, c, CEIL); }
        else { mpf_mul(a, s.a, t.b, c, lo); mpf_mul(b, s.a, t.a, c, CEIL); }
    } else {  // general case: exact cross products, min / max, then round
        XP p[4];
        xp_mul(p[0], s.a, t.a);
        xp_mul(p[1], s.a, t.b);
        xp_mul(p[2], s.b, t.a);
        xp_mul(p[3], s.b, t.b);
        int imin = 0, imax = 0;
        for (int i = 1; i < 4; i++) {
            if (xp_cmp(p[i], p[imin]) < 0) imin = i;
            if (xp_cmp(p[i], p[imax]) > 0) imax = i;
        }
        normalize(a, p[imin].m.n ? p[imin].sign : 0, p[imin].m, p[imin].exp, c, lo);
        normalize(b, p[imax].m.n ? p[imax].sign : 0, p[imax].m, p[imax].exp, c, CEIL);
    }
    r.a = a;
    r.b = b;
}
__device__ __noinline__ void mpi_div(MPI& r, const MPI& s0, const MPI& t0, Ctx& c) {
    MPI s = s0, t = t0;
    int sas = mp_sgn(s.a), sbs = mp_sgn(s.b), tas = mp_sgn(t.a), tbs = mp_sgn(t.b);
    if (sas == 0 && sbs == 0) {
        if ((tas < 0 && tbs > 0) || tas == 0 || tbs == 0) { c.flags |= 2; return; }  // (-inf, inf)
        mp_zero(r.a); mp_zero(r.b);
        return;
    }
    if (tas < 0 && tbs > 0) { c.flags |= 2; return; }
    if (tas < 0) {  // mpi_div(mpi_neg(s), mpi_neg(t))
        MPI ns, nt;
        mpi_neg(ns, s, c);
        mpi_neg(nt, t, c);
        s = ns;
        t = nt;
        sas = mp_sgn(s.a); sbs = mp_sgn(s.b); tas = mp_sgn(t.a); tbs = mp_sgn(t.b);
    }
    if (tas == 0) { c.flags |= 2; return; }  // an infinite end
    MP a, b;
    if (sas >= 0) { mpf_div(a, s.a, t.b, c, FLOOR); mpf_div(b, s.b, t.a, c, CEIL); }
    else if (sbs <= 0) { mpf_div(a, s.a, t.a, c, FLOOR); mpf_div(b, s.b, t.b, c, CEIL); }
    else { mpf_div(a, s.a, t.a, c, FLOOR); mpf_div(b, s.b, t.a, c, CEIL); }
    r.a = a;
    r.b = b;
}
__device__ __noinline__ void mpi_sqrt(MPI& r, const MPI& s, Ctx& c) {
    MP a, b;
    mpf_sqrt(a, s.a, c, FLOOR);
    mpf_sqrt(b, s.b, c, CEIL);
    r.a = a;
    r.b = b;
}
__device__ __noinline__ void mpi_exp(MPI& r, const MPI& s, Ctx& c) {
    MP a, b;
    mpf_exp(a, s.a, c, FLOOR);
    mpf_exp(b, s.b, c, (d_fault == 10 && blockDim.x == 64) ? FLOOR : CEIL);  // fault 10: layout-dependent branch
    r.a = a;
    r.b = b;
}

// ---------------------------------------------------------------------------
// Program interpreter
// ---------------------------------------------------------------------------
__constant__ int c_code[MAXCODE * 4];
__constant__ int c_ncode;
__constant__ uint32_t c_consts[MAXCONST * WORDS_MPI];

__device__ __noinline__ void load_mp(MP& x, const uint32_t* w) {
    x.sign = (int)w[0];
    x.n = (int)w[1];
    x.bc = (int)w[2];
    x.exp = (long long)(((uint64_t)w[4] << 32) | w[3]);
    for (int i = 0; i < ML; i++) x.m[i] = i < x.n ? w[5 + i] : 0;
}
__device__ __noinline__ void store_mp(uint32_t* w, const MP& x) {
    w[0] = (uint32_t)x.sign;
    w[1] = (uint32_t)x.n;
    w[2] = (uint32_t)x.bc;
    w[3] = (uint32_t)((uint64_t)x.exp & 0xffffffffu);
    w[4] = (uint32_t)((uint64_t)x.exp >> 32);
    for (int i = 0; i < ML; i++) w[5 + i] = i < x.n ? x.m[i] : 0;
}
__device__ __noinline__ void get_val(MPI& v, const MPI* regs, int x) {
    if (x >= 0) { v = regs[x]; return; }
    const uint32_t* w = c_consts + (-1 - x) * WORDS_MPI;
    load_mp(v.a, w);
    load_mp(v.b, w + WORDS_MP);
}

__global__ void g0_kernel(int n, const uint32_t* in, uint32_t* out) {
    int stride = gridDim.x * blockDim.x;
    for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n; i += stride) {
        MPI regs[NREG];
        const uint32_t* iw = in + (size_t)i * WORDS_MPI;
        load_mp(regs[0].a, iw);
        load_mp(regs[0].b, iw + WORDS_MP);
        Ctx c;
        c.prec = c_prec;
        c.flags = 0;
        int status = 0, mask = 0;
        MPI res;
        mp_zero(res.a);
        mp_zero(res.b);
        for (int k = 0; k < c_ncode && !status; k++) {
            int code = c_code[4 * k], dst = c_code[4 * k + 1], a = c_code[4 * k + 2], b = c_code[4 * k + 3];
            MPI va, vb, r;
            get_val(va, regs, a);
            switch (code) {
            case 0: get_val(vb, regs, b); mpi_add(r, va, vb, c); break;
            case 1: get_val(vb, regs, b); mpi_sub(r, va, vb, c); break;
            case 2: get_val(vb, regs, b); mpi_mul(r, va, vb, c); break;
            case 3: get_val(vb, regs, b); mpi_div(r, va, vb, c); break;
            case 4: mpi_neg(r, va, c); break;
            case 5: mpi_sqrt(r, va, c); break;
            case 6: mpi_exp(r, va, c); break;
            case 7:  // REQPOS: lower end > 0
                if (d_fault == 7 && b == 1) break;  // fault 7: denominator obligation removed
                if (mp_sgn(va.a) > 0) mask |= 1 << b;
                else status = 1;
                break;
            case 8: res = va; break;
            }
            if (c.flags) status = (c.flags & 1) ? 2 : 3;
            if (!status && dst >= 0) regs[dst] = r;
        }
        uint32_t* ow = out + (size_t)i * WORDS_OUT;
        ow[0] = (uint32_t)status;
        ow[1] = (uint32_t)i;
        ow[2] = (uint32_t)mask;
        ow[3] = 0;
        if (status == 0) {
            store_mp(ow + 4, res.a);
            store_mp(ow + 4 + WORDS_MP, res.b);
        } else {
            for (int j = 0; j < WORDS_MPI; j++) ow[4 + j] = 0;
        }
        for (int j = 0; j < WORDS_MPI; j++) ow[4 + WORDS_MPI + j] = iw[j];  // input echo
    }
}

// ---------------------------------------------------------------------------
// Host API (ctypes)
// ---------------------------------------------------------------------------
static uint32_t* g_in = nullptr;
static uint32_t* g_out = nullptr;
static int g_cap = 0;

static double ms_since(std::chrono::steady_clock::time_point t0) {
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
}

G0_API int g0_init(int device, double* ms) {
    auto t0 = std::chrono::steady_clock::now();
    cudaError_t e = cudaSetDevice(device);
    if (e == cudaSuccess) e = cudaFree(0);  // creates the context
    *ms = ms_since(t0);
    return (int)e;
}

G0_API int g0_device_name(char* buf, int len) {
    cudaDeviceProp p;
    cudaError_t e = cudaGetDeviceProperties(&p, 0);
    if (e != cudaSuccess) return (int)e;
    int i = 0;
    for (; i < len - 1 && p.name[i]; i++) buf[i] = p.name[i];
    buf[i] = 0;
    return 0;
}

G0_API int g0_alloc(int cap, double* ms) {
    auto t0 = std::chrono::steady_clock::now();
    if (g_in) cudaFree(g_in);
    if (g_out) cudaFree(g_out);
    g_in = nullptr;
    g_out = nullptr;
    cudaError_t e = cudaMalloc(&g_in, (size_t)cap * WORDS_MPI * 4);
    if (e == cudaSuccess) e = cudaMalloc(&g_out, (size_t)cap * WORDS_OUT * 4);
    g_cap = e == cudaSuccess ? cap : 0;
    *ms = ms_since(t0);
    return (int)e;
}

// code: ncode x 4 ints; consts: nconst x 22 words; ln2: NMAG x (DL + 1) words
G0_API int g0_upload(int prec, int wp, int r, int ncode, const int* code, int nconst, const uint32_t* consts,
                     const uint32_t* ln2, double* ms) {
    if (ncode > MAXCODE || nconst > MAXCONST) return -2;
    auto t0 = std::chrono::steady_clock::now();
    cudaError_t e = cudaMemcpyToSymbol(c_prec, &prec, sizeof(int));
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(c_wp, &wp, sizeof(int));
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(c_r, &r, sizeof(int));
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(c_ncode, &ncode, sizeof(int));
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(c_code, code, (size_t)ncode * 4 * sizeof(int));
    if (e == cudaSuccess && nconst) e = cudaMemcpyToSymbol(c_consts, consts, (size_t)nconst * WORDS_MPI * 4);
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(c_ln2, ln2, (size_t)NMAG * (DL + 1) * 4);
    if (e == cudaSuccess) e = cudaDeviceSynchronize();
    *ms = ms_since(t0);
    return (int)e;
}

// times: [h2d_ms, kernel_ms, d2h_ms]
G0_API int g0_eval(int n, const uint32_t* in, uint32_t* out, int block, int grid, int fault, int wl, float* times) {
    if (n > g_cap) return -3;
    if (wl < 1 || wl > DL) return -4;
    if (grid <= 0) grid = (n + block - 1) / block;
    cudaError_t e = cudaMemcpyToSymbol(d_fault, &fault, sizeof(int));
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(d_wl, &wl, sizeof(int));
    if (e != cudaSuccess) return (int)e;
    cudaEvent_t ev[4];
    for (int i = 0; i < 4; i++) cudaEventCreate(&ev[i]);
    cudaEventRecord(ev[0]);
    e = cudaMemcpy(g_in, in, (size_t)n * WORDS_MPI * 4, cudaMemcpyHostToDevice);
    cudaEventRecord(ev[1]);
    if (e == cudaSuccess && n > 0) {
        g0_kernel<<<grid, block>>>(n, g_in, g_out);
        e = cudaGetLastError();
    }
    cudaEventRecord(ev[2]);
    if (e == cudaSuccess) e = cudaMemcpy(out, g_out, (size_t)n * WORDS_OUT * 4, cudaMemcpyDeviceToHost);
    cudaEventRecord(ev[3]);
    cudaEventSynchronize(ev[3]);
    if (e == cudaSuccess) e = cudaGetLastError();
    for (int i = 0; i < 3; i++) cudaEventElapsedTime(&times[i], ev[i], ev[i + 1]);
    for (int i = 0; i < 4; i++) cudaEventDestroy(ev[i]);
    return (int)e;
}

G0_API void g0_free() {
    if (g_in) cudaFree(g_in);
    if (g_out) cudaFree(g_out);
    g_in = g_out = nullptr;
    g_cap = 0;
}
