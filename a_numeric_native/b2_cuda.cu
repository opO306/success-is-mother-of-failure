// B2: CUDA executor of A-Numeric VM 0.1 programs.
// docs/current/A_NUMERIC_EXECUTION_STACK_V1.md section 4 (E9: neither the block
// size nor the grid / launch layout may change any result). Programs are sent in
// launches of C programs; each launch has G blocks and block b runs programs
// b, b + G, b + 2G, ... of that launch (grid-stride). Thread 0 interprets the
// program; for SUM and DOT every thread of the block takes a strided share of
// the terms and accumulates it EXACTLY into a 4480-bit two's-complement integer,
// thread 0 adds the exact partials and rounds ONCE. Integer addition is
// associative, so the block size cannot change the value.
//
// Device arithmetic is written separately from anvm_core.hpp (which is host-only):
//   * binary64 ADD SUB MUL DIV SQRT: __dadd_rn __dsub_rn __dmul_rn __ddiv_rn __dsqrt_rn
//     (correctly rounded, never contracted), a non-finite result halts;
//   * FX(W, F), W <= 64: exact 128-bit integer arithmetic.
// CONST literals are materialised on the HOST by anvm_core (shared with B0/B1 --
// disclosed in the design doc); a CONST that halts still halts at its own pc.
// Usage: b2 <block_size> [<grid_blocks> <launch_chunk>] <programs.txt> <results.txt>   (0 = default)
#include <cuda_runtime.h>

#include "anvm_core.hpp"

static Int accumulate(const std::vector<Int>& xs) {  // host side, used only by CONST
    Int s;
    for (const Int& x : xs) s = iadd(s, x);
    return s;
}

// Width contract (A_NUMERIC_EXECUTION_STACK_V1.md 4.2). The VM's SUM/DOT are exact for ANY number of
// terms; this fixed-width accumulator is exact only up to NATIVE_MAX_REDUCTION_TERMS, and longer
// reductions are refused before anything runs.
//   binary64 DOT term: m_a m_b 2^(e_a + e_b), m < 2^53, e in [-1074, 971]. In units of 2^-2148:
//     shift = e_a + e_b + 2148 in [0, 4090], m_a m_b < 2^106  =>  |term| < 2^4196 (DOT_TERM_BITS).
//   N terms: |sum| < N 2^4196 <= 2^(4196 + ceil(log2 N)); two's complement needs one more bit.
//   binary64 SUM terms (< 2^2098 in units of 2^-1074) and FX(W <= 64) products (<= 2^126) need less.
//   CMP margin: |a - b| <= 2 MAX < 2^2099 in units of 2^-1074.
#if INJECT == 211
#define LIMBS 131   // defect: 4192 bits -- one worst-case DOT term no longer fits
#else
#define LIMBS 140   // 4480 bits
#endif
#define MLIMBS 68   // 2176 bits
#define DOT_TERM_BITS 4196
#define NATIVE_MAX_REDUCTION_TERMS 65536
#define LOG2_MAX_REDUCTION_TERMS 16
#if INJECT != 211
static_assert(DOT_TERM_BITS + LOG2_MAX_REDUCTION_TERMS + 1 <= LIMBS * 32, "accumulator too narrow for the contract");
static_assert((4090 + 128) / 32 + 1 < LIMBS, "shifted term must stay inside the accumulator");
#endif
static_assert(2099 <= MLIMBS * 32, "CMP margin buffer too narrow");
static_assert((1 << LOG2_MAX_REDUCTION_TERMS) >= NATIVE_MAX_REDUCTION_TERMS, "log2 bound");

enum { OP_LOADK, OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_NEG, OP_ABS, OP_SQRT, OP_CMP, OP_SUM, OP_DOT, OP_EXP };
enum { H_NONE, H_OVERFLOW, H_DIVZERO, H_SQRTNEG };

struct DInstr {
    int op, dst, arg0, nargs;
};
struct DProgram {
    int fx, W, F, instr0, ninstr, reg0, br0;
};
struct DBranch {
    int pc, result, exp, pad;
    uint32_t m[MLIMBS];
};
struct DImm {
    uint64_t v;
    int halt, pad;
};

// ---------------------------------------------------------------------------
// Exact two's-complement accumulator
// ---------------------------------------------------------------------------
__device__ __noinline__ void acc_clear(uint32_t* a) {
    #pragma unroll 1
    for (int i = 0; i < LIMBS; i++) a[i] = 0;
}
// a += (-1)^neg * (hi:lo) * 2^shift
__device__ __noinline__ void acc_add_shifted(uint32_t* a, uint64_t lo, uint64_t hi, int shift, bool neg) {
    uint32_t o[5] = {(uint32_t)lo, (uint32_t)(lo >> 32), (uint32_t)hi, (uint32_t)(hi >> 32), 0};
    int w = shift >> 5, b = shift & 31;
    uint32_t s[5];
    for (int i = 0; i < 5; i++) s[i] = (o[i] << b) | (b && i ? o[i - 1] >> (32 - b) : 0);
    if (!neg) {
        uint64_t c = 0;
        #pragma unroll 1
        for (int i = w; i < LIMBS; i++) {
            uint64_t t = (uint64_t)a[i] + (i - w < 5 ? s[i - w] : 0) + c;
            a[i] = (uint32_t)t;
            c = t >> 32;
            if (i - w >= 4 && c == 0) break;
        }
    } else {
        int64_t br = 0;
        #pragma unroll 1
        for (int i = w; i < LIMBS; i++) {
            int64_t t = (int64_t)a[i] - (i - w < 5 ? (int64_t)s[i - w] : 0) - br;
            br = t < 0;
            a[i] = (uint32_t)(t + (br ? ((int64_t)1 << 32) : 0));
            if (i - w >= 4 && br == 0) break;
        }
    }
}
__device__ __noinline__ void acc_add(uint32_t* a, const uint32_t* b) {
    uint64_t c = 0;
    #pragma unroll 1
    for (int i = 0; i < LIMBS; i++) {
        uint64_t t = (uint64_t)a[i] + b[i] + c;
        a[i] = (uint32_t)t;
        c = t >> 32;
    }
}
__device__ bool acc_negative(const uint32_t* a) { return a[LIMBS - 1] >> 31; }
__device__ __noinline__ void acc_negate(uint32_t* a) {
    uint64_t c = 1;
    #pragma unroll 1
    for (int i = 0; i < LIMBS; i++) {
        uint64_t t = (uint64_t)(~a[i]) + c;
        a[i] = (uint32_t)t;
        c = t >> 32;
    }
}
__device__ bool acc_bit(const uint32_t* a, int i) { return (a[i >> 5] >> (i & 31)) & 1; }
__device__ __noinline__ int acc_bitlen(const uint32_t* a) {
    #pragma unroll 1
    for (int i = LIMBS - 1; i >= 0; i--)
        if (a[i]) return i * 32 + 32 - __clz(a[i]);
    return 0;
}
__device__ __noinline__ uint64_t acc_bits(const uint32_t* a, int s, int n) {  // n <= 64 bits from position s
    uint64_t v = 0;
    #pragma unroll 1
    for (int i = n - 1; i >= 0; i--) v = (v << 1) | (s + i < LIMBS * 32 && acc_bit(a, s + i));
    return v;
}
__device__ __noinline__ bool acc_any_below(const uint32_t* a, int s) {
    #pragma unroll 1
    for (int i = 0; i < s; i++)
        if (acc_bit(a, i)) return true;
    return false;
}
__device__ __noinline__ bool acc_is_zero(const uint32_t* a) {
    #pragma unroll 1
    for (int i = 0; i < LIMBS; i++)
        if (a[i]) return false;
    return true;
}
// arithmetic shift right by F (0 < F < 64)
__device__ __noinline__ void acc_sar(const uint32_t* a, int F, uint32_t* q) {
    uint32_t fill = acc_negative(a) ? 0xFFFFFFFFu : 0;
    int w = F >> 5, b = F & 31;
    #pragma unroll 1
    for (int i = 0; i < LIMBS; i++) {
        uint32_t lo = i + w < LIMBS ? a[i + w] : fill, hi = i + w + 1 < LIMBS ? a[i + w + 1] : fill;
        q[i] = b ? (lo >> b) | (hi << (32 - b)) : lo;
    }
}
// value within [-2^(W-1), 2^(W-1) - 1]?
__device__ __noinline__ bool acc_fits(const uint32_t* a, int W) {
#if INJECT == 205
    return true;  // defect: FX range check skipped
#endif
    bool sign = acc_negative(a);
    #pragma unroll 1
    for (int i = W - 1; i < LIMBS * 32; i++) {
        if ((i & 31) == 0 && i >= 64) {
            #pragma unroll 1
            for (int j = i >> 5; j < LIMBS; j++)
                if (a[j] != (sign ? 0xFFFFFFFFu : 0)) return false;
            return true;
        }
        if (acc_bit(a, i) != sign) return false;
    }
    return true;
}

// round sign * mag * 2^base (mag > 0) to binary64, nearest-even
__device__ __noinline__ int round_b64(const uint32_t* mag, int base, int sign, uint64_t* out) {
    int k = acc_bitlen(mag) - 1;
    int e = max(k + base - 52, -1074);
    int s = e - base;
    uint64_t q = acc_bits(mag, s, 54);
    bool rb = s > 0 && acc_bit(mag, s - 1);
    bool sticky = s > 1 && acc_any_below(mag, s - 1);
#if INJECT == 204
    if (rb) q++;  // defect: ties away from zero
#else
    if (rb && (sticky || (q & 1))) q++;
#endif
    if (q == 1ull << 53) { q = 1ull << 52; e++; }
    uint64_t sg = (uint64_t)sign << 63;
    if (q >= 1ull << 52) {
        int field = e + 1075;
        if (field >= 0x7FF) return H_OVERFLOW;
        *out = sg | ((uint64_t)field << 52) | (q - (1ull << 52));
    } else {
        *out = sg | q;
    }
    return H_NONE;
}

__device__ __noinline__ void b64_decode(uint64_t b, int* sign, uint64_t* m, int* e) {
    int field = (int)((b >> 52) & 0x7FF);
    uint64_t frac = b & ((1ull << 52) - 1);
    *sign = (int)(b >> 63);
    *m = field ? frac | (1ull << 52) : frac;
    *e = field ? field - 1075 : -1074;
}
__device__ __noinline__ int hw(double r, uint64_t* out) {
    if (!isfinite(r)) return H_OVERFLOW;
    *out = (uint64_t)__double_as_longlong(r);
    return H_NONE;
}

// ---------------------------------------------------------------------------
// 128-bit integers for FX(W <= 64)
// ---------------------------------------------------------------------------
struct I128 {
    uint64_t lo;
    int64_t hi;
};
__device__ I128 i128(int64_t x) { return I128{(uint64_t)x, x < 0 ? -1 : 0}; }
__device__ __noinline__ I128 add128(I128 a, I128 b) {
    uint64_t lo = a.lo + b.lo;
    return I128{lo, a.hi + b.hi + (lo < a.lo)};
}
__device__ __noinline__ I128 neg128(I128 a) {
    uint64_t lo = ~a.lo + 1;
    return I128{lo, ~a.hi + (lo == 0)};
}
__device__ __noinline__ I128 sub128(I128 a, I128 b) { return add128(a, neg128(b)); }
__device__ __noinline__ bool fits128(I128 x, int W) {
#if INJECT == 205
    return true;
#endif
    int64_t v = (int64_t)x.lo;
    if (x.hi != (v < 0 ? -1 : 0)) return false;
    if (W == 64) return true;
    return v >= -(1ll << (W - 1)) && v <= (1ll << (W - 1)) - 1;
}
__device__ __noinline__ I128 mul64(int64_t a, int64_t b) {
    uint64_t ua = a < 0 ? 0 - (uint64_t)a : (uint64_t)a, ub = b < 0 ? 0 - (uint64_t)b : (uint64_t)b;
    I128 r{ua * ub, (int64_t)__umul64hi(ua, ub)};
    return (a < 0) != (b < 0) ? neg128(r) : r;
}
// x / 2^F nearest-even, floor-based (exact for negative x), 0 <= F < 64
__device__ __noinline__ I128 round_shift128(I128 x, int F) {
    if (F == 0) return x;
    I128 q{(x.lo >> F) | ((uint64_t)x.hi << (64 - F)), x.hi >> F};
    uint64_t rem = x.lo & ((1ull << F) - 1), half = 1ull << (F - 1);
    if (rem > half || (rem == half && (q.lo & 1))) q = add128(q, i128(1));
    return q;
}
__device__ __noinline__ int fx_out(I128 v, int W, uint64_t* out) {
    if (!fits128(v, W)) return H_OVERFLOW;
    *out = v.lo;
    return H_NONE;
}
__device__ __noinline__ int fx_div(int64_t a, int64_t b, int W, int F, uint64_t* out) {
    if (b == 0) return H_DIVZERO;
    I128 num = i128(a);
    if (F) num = I128{num.lo << F, (int64_t)(((uint64_t)num.hi << F) | (num.lo >> (64 - F)))};
    bool nneg = num.hi < 0;
    if (nneg) num = neg128(num);
    uint64_t d = b < 0 ? 0 - (uint64_t)b : (uint64_t)b;
    uint64_t qh = 0, ql = 0, r = 0, nh = (uint64_t)num.hi, nl = num.lo;
    #pragma unroll 1
    for (int i = 127; i >= 0; i--) {  // r < d <= 2^63, so r * 2 + 1 fits
        uint64_t bitv = i >= 64 ? (nh >> (i - 64)) & 1 : (nl >> i) & 1;
        r = (r << 1) | bitv;
        if (r >= d) {
            r -= d;
            if (i >= 64) qh |= 1ull << (i - 64);
            else ql |= 1ull << i;
        }
    }
    uint64_t other = d - r;  // compare 2r with d without overflow
    if (r > other || (r == other && (ql & 1))) {
        ql++;
        if (ql == 0) qh++;
    }
    if (qh >> 63) return H_OVERFLOW;
    I128 q{ql, (int64_t)qh};
    return fx_out((a < 0) != (b < 0) ? neg128(q) : q, W, out);
}
__device__ __noinline__ int fx_sqrt(int64_t a, int W, int F, uint64_t* out) {
    if (a < 0) return H_SQRTNEG;
    uint64_t nh = F ? ((uint64_t)a >> (64 - F)) : 0, nl = (uint64_t)a << F;  // n = a * 2^F < 2^127
    uint64_t rh = 0, rl = 0, bh = 1ull << 62, bl = 0;                        // bit = 2^126
    auto ge = [](uint64_t xh, uint64_t xl, uint64_t yh, uint64_t yl) { return xh > yh || (xh == yh && xl >= yl); };
    while (!(bh == 0 && bl == 0) && !ge(nh, nl, bh, bl)) {  // bit >>= 2 while bit > n
        bl = (bl >> 2) | (bh << 62);
        bh >>= 2;
    }
    while (!(bh == 0 && bl == 0)) {
        uint64_t th = rh + bh, tl = rl + bl;
        if (tl < rl) th++;
        if (ge(nh, nl, th, tl)) {
            uint64_t ol = nl;
            nl -= tl;
            nh -= th + (nl > ol);
            rl = (rl >> 1) | (rh << 63);  // res = (res >> 1) + bit
            rh >>= 1;
            uint64_t o = rl;
            rl += bl;
            rh += bh + (rl < o);
        } else {
            rl = (rl >> 1) | (rh << 63);
            rh >>= 1;
        }
        bl = (bl >> 2) | (bh << 62);
        bh >>= 2;
    }
    // now r = floor(sqrt(n)) (fits 64 bits) and n holds n - r^2
    uint64_t r = rl;
#if INJECT != 207  // defect 207: floor root, never rounds up
    if (nh || nl > r) r++;
#endif
    return fx_out(I128{r, 0}, W, out);
}


// ---------------------------------------------------------------------------
// EXP = deterministic_exp_v1 on the device: the exact e^x rounded once. Written
// separately from the VM and from anvm_core.hpp. Enclosure [lo, hi] / 2^M from an
// outward-rounded Taylor sum of y = x / 2^k and k squarings; M grows until both
// ends round alike. Fixed width, so a declared cap: NATIVE_EXP_MAX_ATTEMPTS
// (extra precision 64, 128, 256, 512 bits); beyond it the batch is refused
// (exit 7), never answered.
// ---------------------------------------------------------------------------
#define BNL 176                     // 5632 bits: (M + 1025) * 2 with M <= 1150 + 36 + 512
#define NATIVE_EXP_MAX_ATTEMPTS 4
#define EXP_SCRATCH_BNS 10
struct BN {
    int n;
    uint32_t w[BNL];
};
__device__ __noinline__ void bn_set(BN& r, uint64_t v) {
    r.n = 0;
    while (v) { r.w[r.n++] = (uint32_t)v; v >>= 32; }
}
__device__ __noinline__ void bn_copy(BN& r, const BN& a) {
    r.n = a.n;
    #pragma unroll 1
    for (int i = 0; i < a.n; i++) r.w[i] = a.w[i];
}
__device__ __noinline__ void bn_trim(BN& r) {
    while (r.n && r.w[r.n - 1] == 0) r.n--;
}
__device__ __noinline__ int bn_cmp(const BN& a, const BN& b) {
    if (a.n != b.n) return a.n < b.n ? -1 : 1;
    #pragma unroll 1
    for (int i = a.n - 1; i >= 0; i--)
        if (a.w[i] != b.w[i]) return a.w[i] < b.w[i] ? -1 : 1;
    return 0;
}
__device__ __noinline__ int bn_bitlen(const BN& a) { return a.n ? (a.n - 1) * 32 + 32 - __clz(a.w[a.n - 1]) : 0; }
__device__ __noinline__ bool bn_bit(const BN& a, int i) { return i >= 0 && (i >> 5) < a.n && ((a.w[i >> 5] >> (i & 31)) & 1); }
__device__ __noinline__ bool bn_any_below(const BN& a, int s) {
    #pragma unroll 1
    for (int i = 0; i < s && (i >> 5) < a.n; i++)
        if (bn_bit(a, i)) return true;
    return false;
}
__device__ __noinline__ void bn_add(BN& r, const BN& a, const BN& b) {  // r may alias a
    int n = a.n > b.n ? a.n : b.n;
    uint64_t c = 0;
    #pragma unroll 1
    for (int i = 0; i < n; i++) {
        uint64_t t = (uint64_t)(i < a.n ? a.w[i] : 0) + (i < b.n ? b.w[i] : 0) + c;
        r.w[i] = (uint32_t)t;
        c = t >> 32;
    }
    r.n = n;
    if (c) r.w[r.n++] = (uint32_t)c;
}
__device__ __noinline__ void bn_add_small(BN& r, uint32_t v) {
    BN t;
    bn_set(t, v);
    bn_add(r, r, t);
}
__device__ __noinline__ void bn_sub(BN& r, const BN& a, const BN& b) {  // a >= b; r may alias a
    int64_t br = 0;
    #pragma unroll 1
    for (int i = 0; i < a.n; i++) {
        int64_t t = (int64_t)a.w[i] - (i < b.n ? (int64_t)b.w[i] : 0) - br;
        br = t < 0;
        r.w[i] = (uint32_t)(t + (br ? ((int64_t)1 << 32) : 0));
    }
    r.n = a.n;
    bn_trim(r);
}
__device__ __noinline__ void bn_mul(BN& r, const BN& a, const BN& b) {  // r must not alias
    r.n = a.n + b.n;
    #pragma unroll 1
    for (int i = 0; i < r.n; i++) r.w[i] = 0;
    #pragma unroll 1
    for (int i = 0; i < a.n; i++) {
        uint64_t c = 0;
        #pragma unroll 1
        for (int j = 0; j < b.n; j++) {
            uint64_t t = (uint64_t)a.w[i] * b.w[j] + r.w[i + j] + c;
            r.w[i + j] = (uint32_t)t;
            c = t >> 32;
        }
        r.w[i + b.n] = (uint32_t)c;
    }
    bn_trim(r);
}
__device__ __noinline__ void bn_shl(BN& r, const BN& a, int s) {  // r must not alias
    int w = s >> 5, b = s & 31;
    #pragma unroll 1
    for (int i = 0; i < a.n + w + 1; i++) r.w[i] = 0;
    #pragma unroll 1
    for (int i = 0; i < a.n; i++) {
        r.w[i + w] |= a.w[i] << b;
        if (b) r.w[i + w + 1] |= a.w[i] >> (32 - b);
    }
    r.n = a.n ? a.n + w + 1 : 0;
    bn_trim(r);
}
// r = floor(a / 2^s) (ceil if up); r may alias a
__device__ __noinline__ void bn_shr(BN& r, const BN& a, int s, bool up) {
    bool inexact = up && bn_any_below(a, s);
    int w = s >> 5, b = s & 31;
    int n = a.n - w;
    if (n <= 0) {
        r.n = 0;
    } else {
        #pragma unroll 1
        for (int i = 0; i < n; i++)
            r.w[i] = (a.w[i + w] >> b) | (b && i + w + 1 < a.n ? a.w[i + w + 1] << (32 - b) : 0);
        r.n = n;
        bn_trim(r);
    }
    if (inexact) bn_add_small(r, 1);
}
// r = floor(a / d) (ceil if up); r may alias a
__device__ __noinline__ void bn_div_small(BN& r, const BN& a, uint32_t d, bool up) {
    uint64_t rem = 0;
    int n = a.n;
    #pragma unroll 1
    for (int i = n - 1; i >= 0; i--) {
        uint64_t cur = (rem << 32) | a.w[i];
        r.w[i] = (uint32_t)(cur / d);
        rem = cur % d;
    }
    r.n = n;
    bn_trim(r);
    if (up && rem) bn_add_small(r, 1);
}
__device__ __noinline__ uint64_t bn_bits(const BN& a, int s, int n) {
    uint64_t v = 0;
    #pragma unroll 1
    for (int i = n - 1; i >= 0; i--) v = (v << 1) | (bn_bit(a, s + i) ? 1 : 0);
    return v;
}

// [lo, hi] containing e^x * 2^M, x = (-1)^neg * X / 2^S, with |x| / 2^k <= 2^-8. T: 8 scratch numbers.
__device__ __noinline__ void exp_enclose(bool neg, const BN& X, int S, int M, int k, BN* T, BN& lo, BN& hi) {
    BN &a = T[0], &t_lo = T[1], &t_hi = T[2], &s_lo = T[3], &s_hi = T[4], &prod = T[5], &r = T[6];
    bn_shl(a, X, M - S - k);                       // exact: M - S - k >= 0 by the choice of M
    bn_set(r, 1);
    bn_shl(t_lo, r, M);
    bn_copy(t_hi, t_lo);
    bn_copy(s_lo, t_lo);
    bn_copy(s_hi, t_lo);
    #pragma unroll 1
    for (uint32_t i = 1;; i++) {
        bn_mul(prod, t_lo, a);
        bn_shr(prod, prod, M, false);
        bn_div_small(t_lo, prod, i, false);
        bn_mul(prod, t_hi, a);
        bn_shr(prod, prod, M, true);
        bn_div_small(t_hi, prod, i, true);
        if (neg && (i & 1)) {
            bn_sub(s_lo, s_lo, t_hi);
            bn_sub(s_hi, s_hi, t_lo);
        } else {
            bn_add(s_lo, s_lo, t_lo);
            bn_add(s_hi, s_hi, t_hi);
        }
        if (t_hi.n == 0 || (t_hi.n == 1 && t_hi.w[0] <= 1)) break;
    }
    bn_add(r, t_hi, t_hi);                        // remainder <= t_hi (|y| <= 2^-8); margin 2 t_hi + 2
    bn_add_small(r, 2);
    bn_sub(lo, s_lo, r);                          // s_lo > r always: e^y > 0.99 at scale 2^M
    bn_add(hi, s_hi, r);
    #pragma unroll 1
    for (int j = 0; j < k; j++) {
        bn_mul(prod, lo, lo);
        bn_shr(lo, prod, M, false);
        bn_mul(prod, hi, hi);
        bn_shr(hi, prod, M, true);
    }
}
// v / 2^M rounded to binary64 (nearest-even); H_OVERFLOW if it leaves the finite range
__device__ __noinline__ int exp_round_b64(const BN& v, int M, uint64_t* out) {
    if (v.n == 0) { *out = 0; return H_NONE; }
    int k = bn_bitlen(v) - 1;
    int e = max(k - M - 52, -1074);
    int s = e + M;                                 // > 0 since M > 1074
    uint64_t q = bn_bits(v, s, 54);
    bool rb = bn_bit(v, s - 1), sticky = bn_any_below(v, s - 1);
    if (rb && (sticky || (q & 1))) q++;
    if (q == 1ull << 53) { q = 1ull << 52; e++; }
    if (q >= 1ull << 52) {
        int field = e + 1075;
        if (field >= 0x7FF) return H_OVERFLOW;
        *out = ((uint64_t)field << 52) | (q - (1ull << 52));
    } else {
        *out = q;
    }
    return H_NONE;
}
// v / 2^M rounded to the FX(W, F) grid (nearest-even)
__device__ __noinline__ int exp_round_fx(const BN& v, int M, int W, int F, uint64_t* out) {
    int s = M - F;
    int bl = bn_bitlen(v);
    if (bl - s > W) return H_OVERFLOW;             // quotient >= 2^(W-1) certainly
    uint64_t q = bn_bits(v, s, 64);
    bool rb = bn_bit(v, s - 1), sticky = bn_any_below(v, s - 1);
    if (rb && (sticky || (q & 1))) q++;
    if (q > (W == 64 ? 0x7FFFFFFFFFFFFFFFull : (1ull << (W - 1)) - 1)) return H_OVERFLOW;
    *out = q;
    return H_NONE;
}
// returns a halt code, or -1 if the precision cap was reached (the batch will be refused)
__device__ __noinline__ int exp_eval(bool fx, int W, int F, uint64_t xr, BN* T, uint64_t* out) {
#if INJECT == 212
    if (!fx) return hw(exp(__longlong_as_double((long long)xr)), out);  // defect: CUDA's exp
#endif
    BN &X = T[7], &lo = T[8], &hi = T[9];
    bool neg;
    int S;
    if (fx) {
        int64_t v = (int64_t)xr;
        if (v == 0) {
            if (F >= W - 1) return H_OVERFLOW;         // 1 is not representable
            *out = 1ull << F;
            return H_NONE;
        }
        neg = v < 0;
        uint64_t mag = neg ? 0 - (uint64_t)v : (uint64_t)v;
        if (!neg && (mag >> F) >= (uint64_t)W) return H_OVERFLOW;          // e^W > 2^W
        if (neg && (mag >> F) >= (uint64_t)F + 2) { *out = 0; return H_NONE; }  // e^-(F+2) < 2^-(F+2)
        bn_set(X, mag);
        S = F;
    } else {
        if ((xr & ~(1ull << 63)) == 0) { *out = 0x3FF0000000000000ull; return H_NONE; }
        double xd = __longlong_as_double((long long)xr);
        if (xd >= 710.0) return H_OVERFLOW;           // e^710 > 2^1024
        if (xd <= -746.0) { *out = 0; return H_NONE; }  // e^-746 < 2^-1076
        int sg, e;
        uint64_t m;
        b64_decode(xr, &sg, &m, &e);                   // |x| < 746: e < 0
        neg = sg;
        bn_set(X, m);
        S = -e;
    }
    int k = max(0, bn_bitlen(X) - S) + 8;
    int base = fx ? F + 16 : 1150;
    #pragma unroll 1
    for (int attempt = 0, extra = 64; attempt < NATIVE_EXP_MAX_ATTEMPTS; attempt++, extra *= 2) {
        int M = base + 2 * k + extra;
#if INJECT == 213
        M = S + k + 8;                               // defect: ~8 bits beyond the input's scale, no refinement
#endif
        exp_enclose(neg, X, S, M, k, T, lo, hi);
        uint64_t a = 0, b = 0;
        int ha = fx ? exp_round_fx(lo, M, W, F, &a) : exp_round_b64(lo, M, &a);
        int hb = fx ? exp_round_fx(hi, M, W, F, &b) : exp_round_b64(hi, M, &b);
#if INJECT == 213
        hb = ha; b = a;
#endif
#if INJECT == 214
        b = a + 1;                                    // defect: never agrees (exercises the refusal)
#endif
        if (ha == hb && a == b) {
            *out = a;
            return ha;
        }
    }
    return -1;
}

// ---------------------------------------------------------------------------
// The kernel: one program per block
// ---------------------------------------------------------------------------
__device__ __noinline__ void run_one(int pid, const DProgram* progs, const DInstr* instrs, const int* args,
                                     const DImm* imm, uint64_t* regs, uint8_t* defined, DBranch* branches, int* nbranch,
                                     int* halt_pc, int* halt_reason, uint32_t* scratch, int& halted,
                                     BN* exp_scratch, int* exp_exhausted) {
    const DProgram P = progs[pid];
    uint64_t* R = regs + P.reg0;
    uint8_t* Def = defined + P.reg0;
    const int tid = threadIdx.x, B = blockDim.x;
    uint32_t* part = scratch + ((size_t)blockIdx.x * B + tid) * LIMBS;
    uint32_t* parts = scratch + (size_t)blockIdx.x * B * LIMBS;
    if (tid == 0) { halted = 0; nbranch[pid] = 0; halt_pc[pid] = -1; halt_reason[pid] = H_NONE; }
    __syncthreads();
    for (int pc = 0; pc < P.ninstr; pc++) {
        const DInstr I = instrs[P.instr0 + pc];
        const int* A = args + I.arg0;
        if (I.op == OP_SUM || I.op == OP_DOT) {
            int k = I.op == OP_SUM ? I.nargs : I.nargs / 2;
            acc_clear(part);
            bool mine_all_neg_zero = true;
#if INJECT == 201
            double fpart = 0.0;  // defect: each thread sums its share in hardware floats
            bool started = false;
#endif
            int start = tid;
#if INJECT == 210
            if (blockIdx.x == 1) start++;  // defect: the result depends on which block runs the program
#endif
            for (int i = start; i < k; i += B) {
                if (P.fx) {
                    int64_t x = (int64_t)R[A[i]];
                    if (I.op == OP_SUM) {
                        acc_add_shifted(part, x < 0 ? 0 - (uint64_t)x : (uint64_t)x, 0, 0, x < 0);
                    } else {
                        I128 p = mul64(x, (int64_t)R[A[k + i]]);
                        bool n = p.hi < 0;
                        if (n) p = neg128(p);
                        acc_add_shifted(part, p.lo, (uint64_t)p.hi, 0, n);
                    }
                    continue;
                }
                int sa, sb = 0, ea, eb = 0;
                uint64_t ma, mb = 1;
                b64_decode(R[A[i]], &sa, &ma, &ea);
                if (I.op == OP_DOT) b64_decode(R[A[k + i]], &sb, &mb, &eb);
                int sg = sa ^ sb;
                uint64_t lo = ma * mb, hi = __umul64hi(ma, mb);
#if INJECT == 206
                hi = 0;  // defect: high word of the 106-bit product dropped
#endif
                if (!(sg == 1 && lo == 0 && hi == 0)) mine_all_neg_zero = false;
                acc_add_shifted(part, lo, hi, I.op == OP_SUM ? ea + 1074 : ea + eb + 2148, sg);
#if INJECT == 201
                if (I.op == OP_SUM) {
                    double v = __longlong_as_double((long long)R[A[i]]);
                    fpart = started ? __dadd_rn(fpart, v) : v;
                    started = true;
                }
#endif
            }
#if INJECT == 201
            if (!P.fx && I.op == OP_SUM) {
                ((double*)part)[0] = fpart;
                part[2] = started;
            }
#endif
            int all_neg_zero = __syncthreads_and(mine_all_neg_zero);
            if (tid == 0) {
                uint32_t tot[LIMBS];
                acc_clear(tot);
#if INJECT == 202
                int nb = B < 32 ? B : 32;  // defect: combines only one warp's partials
#else
                int nb = B;
#endif
                #pragma unroll 1
                for (int t = 0; t < nb; t++) acc_add(tot, parts + (size_t)t * LIMBS);
                uint64_t out = 0;
                int h = H_NONE;
                if (P.fx) {
                    if (I.op == OP_DOT && P.F) {
                        uint32_t q[LIMBS];
                        acc_sar(tot, P.F, q);
                        if (acc_bit(tot, P.F - 1) && (acc_any_below(tot, P.F - 1) || (q[0] & 1)))
                            acc_add_shifted(q, 1, 0, 0, false);
                        #pragma unroll 1
                        for (int i = 0; i < LIMBS; i++) tot[i] = q[i];
                    }
                    if (acc_fits(tot, P.W)) out = (uint64_t)tot[0] | ((uint64_t)tot[1] << 32);
                    else h = H_OVERFLOW;
                } else if (acc_is_zero(tot)) {
                    out = all_neg_zero ? 1ull << 63 : 0;
                } else {
                    int sign = acc_negative(tot);
                    if (sign) acc_negate(tot);
                    h = round_b64(tot, I.op == OP_SUM ? -1074 : -2148, sign, &out);
                }
#if INJECT == 201
                if (!P.fx && I.op == OP_SUM) {
                    double f = 0.0;
                    bool first = true;
                    for (int t = 0; t < B; t++) {
                        const uint32_t* pt = parts + (size_t)t * LIMBS;
                        if (!pt[2]) continue;
                        double v = ((const double*)pt)[0];
                        f = first ? v : __dadd_rn(f, v);
                        first = false;
                    }
                    h = hw(f, &out);
                }
#endif
                if (h) { halted = 1; halt_pc[pid] = pc; halt_reason[pid] = h; }
                else { R[I.dst] = out; Def[I.dst] = 1; }
            }
        } else if (tid == 0) {
            uint64_t out = 0;
            int h = H_NONE;
            if (I.op == OP_LOADK) {
                h = imm[I.arg0].halt;
                out = imm[I.arg0].v;
            } else if (I.op == OP_CMP) {
                DBranch& br = branches[P.br0 + nbranch[pid]];
                nbranch[pid]++;
                br.pc = pc;
                uint64_t a = R[A[0]], b = R[A[1]];
                #pragma unroll 1
                for (int i = 0; i < MLIMBS; i++) br.m[i] = 0;
                if (P.fx) {
                    int64_t x = (int64_t)a, y = (int64_t)b;
                    br.result = (x > y) - (x < y);
                    I128 d = sub128(i128(x), i128(y));
                    if (d.hi < 0) d = neg128(d);
                    br.m[0] = (uint32_t)d.lo; br.m[1] = (uint32_t)(d.lo >> 32);
                    br.m[2] = (uint32_t)d.hi; br.m[3] = (uint32_t)((uint64_t)d.hi >> 32);
                    br.exp = -P.F;
                } else {
                    double x = __longlong_as_double((long long)a), y = __longlong_as_double((long long)b);
                    br.result = (x > y) - (x < y);
                    uint32_t d[LIMBS];
                    acc_clear(d);
                    int s, e;
                    uint64_t m;
                    b64_decode(a, &s, &m, &e);
                    acc_add_shifted(d, m, 0, e + 1074, s);
                    b64_decode(b, &s, &m, &e);
                    acc_add_shifted(d, m, 0, e + 1074, !s);
                    if (acc_negative(d)) acc_negate(d);
                    #pragma unroll 1
                    for (int i = 0; i < MLIMBS; i++) br.m[i] = d[i];
                    br.exp = -1074;
                }
            } else if (P.fx) {
                int64_t x = (int64_t)R[A[0]];
                int64_t y = I.nargs > 1 ? (int64_t)R[A[1]] : 0;
                switch (I.op) {
                    case OP_ADD: h = fx_out(add128(i128(x), i128(y)), P.W, &out); break;
                    case OP_SUB: h = fx_out(sub128(i128(x), i128(y)), P.W, &out); break;
                    case OP_MUL: h = fx_out(round_shift128(mul64(x, y), P.F), P.W, &out); break;
                    case OP_DIV: h = fx_div(x, y, P.W, P.F, &out); break;
                    case OP_NEG: h = fx_out(neg128(i128(x)), P.W, &out); break;
                    case OP_ABS: h = fx_out(x < 0 ? neg128(i128(x)) : i128(x), P.W, &out); break;
                    case OP_SQRT: h = fx_sqrt(x, P.W, P.F, &out); break;
                    case OP_EXP:
                        h = exp_eval(true, P.W, P.F, (uint64_t)x, exp_scratch + (size_t)blockIdx.x * EXP_SCRATCH_BNS, &out);
                        if (h < 0) { *exp_exhausted = 1; h = H_OVERFLOW; }
                        break;
                }
            } else {
                uint64_t a = R[A[0]], b = I.nargs > 1 ? R[A[1]] : 0;
                double x = __longlong_as_double((long long)a), y = __longlong_as_double((long long)b);
                switch (I.op) {
#if INJECT == 203
                    case OP_ADD: h = hw(__dadd_rz(x, y), &out); break;  // defect: round toward zero
#else
                    case OP_ADD: h = hw(__dadd_rn(x, y), &out); break;
#endif
                    case OP_SUB: h = hw(__dsub_rn(x, y), &out); break;
                    case OP_MUL: h = hw(__dmul_rn(x, y), &out); break;
                    case OP_DIV:
                        if ((b & ~(1ull << 63)) == 0) h = H_DIVZERO;
                        else h = hw(__ddiv_rn(x, y), &out);
                        break;
                    case OP_NEG: out = a ^ (1ull << 63); break;
                    case OP_ABS: out = a & ~(1ull << 63); break;
                    case OP_SQRT:
                        if ((a >> 63) && (a & ~(1ull << 63))) h = H_SQRTNEG;
                        else h = hw(__dsqrt_rn(x), &out);
                        break;
                    case OP_EXP:
                        h = exp_eval(false, 0, 0, a, exp_scratch + (size_t)blockIdx.x * EXP_SCRATCH_BNS, &out);
                        if (h < 0) { *exp_exhausted = 1; h = H_OVERFLOW; }
                        break;
                }
            }
            if (I.op != OP_CMP) {
                if (h) { halted = 1; halt_pc[pid] = pc; halt_reason[pid] = h; }
                else { R[I.dst] = out; Def[I.dst] = 1; }
            }
        }
        __syncthreads();
        if (halted) break;
    }
}

__global__ void run_programs(int base, int count, const DProgram* progs, const DInstr* instrs, const int* args,
                             const DImm* imm, uint64_t* regs, uint8_t* defined, DBranch* branches, int* nbranch,
                             int* halt_pc, int* halt_reason, uint32_t* scratch, BN* exp_scratch,
                             int* exp_exhausted) {
    __shared__ int halted;
#if INJECT == 208
    // defect: one program per block assumed -- programs past gridDim.x in a launch are never run
    if ((int)blockIdx.x < count)
        run_one(base + blockIdx.x, progs, instrs, args, imm, regs, defined, branches, nbranch, halt_pc, halt_reason,
                scratch, halted, exp_scratch, exp_exhausted);
#else
    for (int local = blockIdx.x; local < count; local += gridDim.x) {  // uniform for the whole block
        run_one(base + local, progs, instrs, args, imm, regs, defined, branches, nbranch, halt_pc, halt_reason,
                scratch, halted, exp_scratch, exp_exhausted);
        __syncthreads();
    }
#endif
}

// ---------------------------------------------------------------------------
// Host
// ---------------------------------------------------------------------------
#define CK(x)                                                                              \
    do {                                                                                   \
        cudaError_t err = (x);                                                             \
        if (err != cudaSuccess) {                                                          \
            fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(err), __FILE__, __LINE__); \
            exit(4);                                                                       \
        }                                                                                  \
    } while (0)

template <class T>
static T* upload(const std::vector<T>& v) {
    T* d = nullptr;
    CK(cudaMalloc(&d, std::max<size_t>(1, v.size()) * sizeof(T)));
    if (!v.empty()) CK(cudaMemcpy(d, v.data(), v.size() * sizeof(T), cudaMemcpyHostToDevice));
    return d;
}

int main(int argc, char** argv) {
    if ((argc != 4 && argc != 6) || atoi(argv[1]) < 1 || atoi(argv[1]) > 1024) {
        fprintf(stderr, "usage: b2 <block_size 1..1024> [<grid_blocks> <launch_chunk>] <programs.txt> <results.txt>\n");
        return 2;
    }
    const int B = atoi(argv[1]);
    const int want_grid = argc == 6 ? atoi(argv[2]) : 0, want_chunk = argc == 6 ? atoi(argv[3]) : 0;
    const char* in_path = argv[argc - 2];
    const char* out_path = argv[argc - 1];
    std::vector<Program> progs = parse_programs(in_path);
    // refuse, before anything runs, every reduction the accumulator is not proven to hold
    for (size_t pi = 0; pi < progs.size(); pi++)
        for (size_t pc = 0; pc < progs[pi].prog.size(); pc++) {
            const Instr& in = progs[pi].prog[pc];
            if ((in.op == "SUM" || in.op == "DOT") && atoll(in.args[0].c_str()) > NATIVE_MAX_REDUCTION_TERMS) {
                fprintf(stderr, "REJECTED native_reduction_too_long: program %zu pc %zu has %s terms > %d\n", pi, pc,
                        in.args[0].c_str(), NATIVE_MAX_REDUCTION_TERMS);
                return 6;
            }
        }
    static const std::map<std::string, int> OPS = {{"ADD", OP_ADD}, {"SUB", OP_SUB}, {"MUL", OP_MUL}, {"DIV", OP_DIV},
                                                   {"NEG", OP_NEG}, {"ABS", OP_ABS}, {"SQRT", OP_SQRT}, {"CMP", OP_CMP},
                                                   {"SUM", OP_SUM}, {"DOT", OP_DOT}, {"EXP", OP_EXP}};
    std::vector<DProgram> dp;
    std::vector<DInstr> di;
    std::vector<int> da;
    std::vector<DImm> dimm;
    std::vector<uint64_t> regs;
    std::vector<uint8_t> def;
    std::vector<std::map<std::string, int>> slots(progs.size());
    int nbr_total = 0;
    for (size_t pi = 0; pi < progs.size(); pi++) {
        const Program& P = progs[pi];
        if (P.fx && P.p.W > 64) {
            fprintf(stderr, "B2 implements FX with W <= 64 only\n");
            return 5;
        }
        std::map<std::string, int>& S = slots[pi];
        auto slot = [&S](const std::string& n) {
            auto it = S.find(n);
            if (it != S.end()) return it->second;
            int k = (int)S.size();
            S[n] = k;
            return k;
        };
        DProgram d{P.fx, P.p.W, P.p.F, (int)di.size(), (int)P.prog.size(), (int)regs.size(), nbr_total};
        std::vector<std::pair<int, uint64_t>> init;
        for (auto& kv : P.inputs)
            init.push_back({slot(kv.first), P.fx ? (uint64_t)strtoll(kv.second.c_str(), nullptr, 10)
                                                 : strtoull(kv.second.c_str(), nullptr, 16)});
        for (const Instr& in : P.prog) {
            DInstr x{0, -1, (int)da.size(), 0};
            if (in.op == "CONST") {
                x.op = OP_LOADK;
                x.arg0 = (int)dimm.size();
                DImm k{0, H_NONE, 0};
                try {
                    Int num = parse_int(in.args[0]), den = parse_int(in.args[1]);
                    if (P.fx) {
                        Int v = fx_check(P.p, div_round(mk(num.neg, shl(num.m, P.p.F)), den));
                        uint64_t mag = to_u64(v.m);
                        k.v = v.neg ? 0 - mag : mag;
                    } else {
                        k.v = b64_const(num, den);
                    }
                } catch (const Halt&) {
                    k.halt = H_OVERFLOW;
                }
                dimm.push_back(k);
            } else {
                x.op = OPS.at(in.op);
                std::vector<std::string> names;
                if (in.op == "SUM" || in.op == "DOT") names.assign(in.args.begin() + 1, in.args.end());
                else names = in.args;
                for (const std::string& n : names) da.push_back(slot(n));
                x.nargs = (int)names.size();
                if (in.op == "CMP") nbr_total++;
            }
            if (in.op != "CMP") x.dst = slot(in.dst);
            di.push_back(x);
        }
        regs.resize(regs.size() + S.size(), 0);
        def.resize(def.size() + S.size(), 0);
        for (auto& kv : init) {
            regs[d.reg0 + kv.first] = kv.second;
            def[d.reg0 + kv.first] = 1;
        }
        dp.push_back(d);
    }
    const int n = (int)dp.size();
    CK(cudaDeviceSetLimit(cudaLimitStackSize, 8192));
    DProgram* g_prog = upload(dp);
    DInstr* g_instr = upload(di);
    int* g_args = upload(da);
    DImm* g_imm = upload(dimm);
    uint64_t* g_regs = upload(regs);
    uint8_t* g_def = upload(def);
    DBranch* g_br = nullptr;
    CK(cudaMalloc(&g_br, std::max(1, nbr_total) * sizeof(DBranch)));
    int *g_nbr, *g_hpc, *g_hr;
    CK(cudaMalloc(&g_nbr, std::max(1, n) * sizeof(int)));
    CK(cudaMalloc(&g_hpc, std::max(1, n) * sizeof(int)));
    CK(cudaMalloc(&g_hr, std::max(1, n) * sizeof(int)));
    // a program that is never run must read back as "no registers written, no halt" (never garbage)
    CK(cudaMemset(g_nbr, 0, std::max(1, n) * sizeof(int)));
    CK(cudaMemset(g_hpc, 0xFF, std::max(1, n) * sizeof(int)));
    CK(cudaMemset(g_hr, 0, std::max(1, n) * sizeof(int)));
    const size_t per_block = (size_t)B * LIMBS * sizeof(uint32_t);
    const int max_blocks = (int)std::max<size_t>(1, ((size_t)256 << 20) / per_block);  // scratch <= 256 MB
    const int chunk = want_chunk > 0 ? want_chunk : std::max(1, std::min(n, max_blocks));
    const int grid = std::min({want_grid > 0 ? want_grid : chunk, chunk, max_blocks});
    uint32_t* g_scratch = nullptr;
    CK(cudaMalloc(&g_scratch, (size_t)grid * per_block));
    BN* g_exp_scratch = nullptr;
    CK(cudaMalloc(&g_exp_scratch, (size_t)grid * EXP_SCRATCH_BNS * sizeof(BN)));
    int* g_exhausted = nullptr;
    CK(cudaMalloc(&g_exhausted, sizeof(int)));
    CK(cudaMemset(g_exhausted, 0, sizeof(int)));
#if INJECT == 209
    for (int base = 0; base + chunk <= n; base += chunk) {  // defect: a last partial launch is skipped
#else
    for (int base = 0; base < n; base += chunk) {
#endif
        int count = std::min(chunk, n - base);
        run_programs<<<std::min(grid, count), B>>>(base, count, g_prog, g_instr, g_args, g_imm, g_regs, g_def, g_br,
                                                  g_nbr, g_hpc, g_hr, g_scratch, g_exp_scratch,
                                                  g_exhausted);
        CK(cudaGetLastError());
        CK(cudaDeviceSynchronize());
    }
    int exhausted = 0;
    CK(cudaMemcpy(&exhausted, g_exhausted, sizeof(int), cudaMemcpyDeviceToHost));
    if (exhausted) {
        fprintf(stderr, "REJECTED native_exp_precision_exhausted: EXP not resolved within %d attempts\n",
                NATIVE_EXP_MAX_ATTEMPTS);
        return 7;
    }
    std::vector<DBranch> br(nbr_total);
    std::vector<int> nbr(n), hpc(n), hr(n);
    CK(cudaMemcpy(regs.data(), g_regs, regs.size() * sizeof(uint64_t), cudaMemcpyDeviceToHost));
    CK(cudaMemcpy(def.data(), g_def, def.size(), cudaMemcpyDeviceToHost));
    if (nbr_total) CK(cudaMemcpy(br.data(), g_br, nbr_total * sizeof(DBranch), cudaMemcpyDeviceToHost));
    if (n) {
        CK(cudaMemcpy(nbr.data(), g_nbr, n * sizeof(int), cudaMemcpyDeviceToHost));
        CK(cudaMemcpy(hpc.data(), g_hpc, n * sizeof(int), cudaMemcpyDeviceToHost));
        CK(cudaMemcpy(hr.data(), g_hr, n * sizeof(int), cudaMemcpyDeviceToHost));
    }
    static const char* REASON[] = {"-", "overflow", "division_by_zero", "sqrt_of_negative"};
    std::string out;
    char buf[64];
    for (int pi = 0; pi < n; pi++) {
        out += "R\n";
        for (auto& kv : slots[pi]) {
            int s = dp[pi].reg0 + kv.second;
            if (!def[s]) continue;
            if (dp[pi].fx) snprintf(buf, sizeof buf, "%lld", (long long)regs[s]);
            else snprintf(buf, sizeof buf, "%016llx", (unsigned long long)regs[s]);
            out += "G " + kv.first + " " + buf + "\n";
        }
        for (int b = 0; b < nbr[pi]; b++) {
            const DBranch& x = br[dp[pi].br0 + b];
            Mag m(x.m, x.m + MLIMBS);
            trim(m);
            out += "B " + std::to_string(x.pc) + " " + std::to_string(x.result) + " " + to_hex(m) + " " +
                   std::to_string(x.exp) + "\n";
        }
        if (hpc[pi] >= 0) out += "H " + std::to_string(hpc[pi]) + " " + REASON[hr[pi]] + "\n";
        else out += "H -\n";
        out += "E\n";
    }
    write_file(out_path, out);
    return 0;
}
