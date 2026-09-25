// Benchmark-only state kernels for the C1-B1 number-representation decision (designer 13th ed. item 10).
// NOT a world executor and not B0: it measures what a position width costs. Every operation is still exact
// (and checked bit for bit against Python by a_physics_native/bench_state.py), otherwise its timing would mean
// nothing.
//
// position = FX(32 NL, 48)  -- NL 32-bit limbs, two's complement (NL = 2, 3, 4: FX(64,48), FX(96,48), FX(128,48))
// momentum = FX(64, 48)     -- int64
// The SAME generic limb code serves every width (so the widths are compared under one implementation strategy;
// a hand-tuned native-int64 path for FX(64,48) could be faster -- not measured).
//
// Operations (per pair of atoms i, j; 3 components):
//   drift : r <- r + round_half_even(p * dt / m)  (contract c1b1-two-atom-v2: the DISPLACEMENT is rounded, then
//           added exactly; dt / m = dt * A / B exactly, A = 5485799090441, B = 399623831237000000 -- NIST 40Ar /
//           CODATA 2022 m_e; the exact quotient never pre-rounded)
//   dr    : Delta r = r_j - r_i, exact (one limb wider)
//   R2    : Delta x^2 + Delta y^2 + Delta z^2, exact (2 NL + 3 limbs)
//   kick  : p_j <- p_j + J, p_i <- p_i - J  (int64, overflow flagged)
#pragma once
#include <cstdint>

#ifdef __CUDACC__
#define HD __host__ __device__ __forceinline__
#else
#define HD inline
#endif

namespace bench {

constexpr uint64_t DRIFT_A = 5485799090441ull;          // numerator of 1/m (m in electron masses)
constexpr uint64_t DRIFT_B = 399623831237000000ull;     // denominator

template <int N>
struct W {  // two's complement, little-endian 32-bit limbs
    uint32_t w[N];
};

template <int N>
HD W<N> from_i64(int64_t v) {
    W<N> r;
    uint64_t u = (uint64_t)v;
    for (int i = 0; i < N; i++) {
        r.w[i] = i == 0 ? (uint32_t)u : i == 1 ? (uint32_t)(u >> 32) : (v < 0 ? 0xFFFFFFFFu : 0u);
    }
    return r;
}
template <int N>
HD bool negative(const W<N>& a) { return a.w[N - 1] >> 31; }
template <int N>
HD W<N> add(const W<N>& a, const W<N>& b) {
    W<N> r;
    uint64_t c = 0;
    for (int i = 0; i < N; i++) {
        uint64_t t = (uint64_t)a.w[i] + b.w[i] + c;
        r.w[i] = (uint32_t)t;
        c = t >> 32;
    }
    return r;
}
template <int N>
HD bool add_overflows(const W<N>& a, const W<N>& b, const W<N>& s) {
    return negative(a) == negative(b) && negative(s) != negative(a);
}
template <int M, int N>
HD W<M> widen(const W<N>& a) {  // sign extension, M >= N
    W<M> r;
    uint32_t ext = negative(a) ? 0xFFFFFFFFu : 0u;
    for (int i = 0; i < M; i++) r.w[i] = i < N ? a.w[i] : ext;
    return r;
}
template <int N>
HD W<N> neg(const W<N>& a) {
    W<N> r;
    uint64_t c = 1;
    for (int i = 0; i < N; i++) {
        uint64_t t = (uint64_t)(~a.w[i]) + c;
        r.w[i] = (uint32_t)t;
        c = t >> 32;
    }
    return r;
}
template <int N>
HD W<N> sub(const W<N>& a, const W<N>& b) { return add(a, neg(b)); }
template <int N>
HD W<2 * N> square(const W<N>& a) {  // exact a^2 (non-negative)
    W<N> m = negative(a) ? neg(a) : a;
    W<2 * N> r;
    for (int i = 0; i < 2 * N; i++) r.w[i] = 0;
    for (int i = 0; i < N; i++) {
        uint64_t c = 0;
        for (int j = 0; j < N; j++) {
            uint64_t t = (uint64_t)m.w[i] * m.w[j] + r.w[i + j] + c;
            r.w[i + j] = (uint32_t)t;
            c = t >> 32;
        }
        r.w[i + N] = (uint32_t)c;
    }
    return r;
}

// unsigned 128 / 64 (Hacker's Delight divlu, 32-bit digits), q must fit 64 bits (hi < d)
HD uint64_t divlu(uint64_t hi, uint64_t lo, uint64_t d, uint64_t* rem) {
    const uint64_t b = 1ull << 32;
    int s = 0;
    for (uint64_t t = d; !(t & 0x8000000000000000ull); t <<= 1) s++;
    d <<= s;
    uint64_t vn1 = d >> 32, vn0 = d & 0xFFFFFFFFull;
    uint64_t un32 = s ? (hi << s) | (lo >> (64 - s)) : hi;
    uint64_t un10 = lo << s;
    uint64_t un1 = un10 >> 32, un0 = un10 & 0xFFFFFFFFull;
    uint64_t q1 = un32 / vn1, rhat = un32 - q1 * vn1;
    while (q1 >= b || q1 * vn0 > b * rhat + un1) {
        q1--;
        rhat += vn1;
        if (rhat >= b) break;
    }
    uint64_t un21 = un32 * b + un1 - q1 * d;
    uint64_t q0 = un21 / vn1;
    rhat = un21 - q0 * vn1;
    while (q0 >= b || q0 * vn0 > b * rhat + un0) {
        q0--;
        rhat += vn1;
        if (rhat >= b) break;
    }
    *rem = (un21 * b + un0 - q0 * d) >> s;
    return q1 * b + q0;
}
HD void mul64(uint64_t a, uint64_t b, uint64_t* hi, uint64_t* lo) {
    uint64_t a0 = a & 0xFFFFFFFFull, a1 = a >> 32, b0 = b & 0xFFFFFFFFull, b1 = b >> 32;
    uint64_t p00 = a0 * b0, p01 = a0 * b1, p10 = a1 * b0, p11 = a1 * b1;
    uint64_t mid = (p00 >> 32) + (p01 & 0xFFFFFFFFull) + (p10 & 0xFFFFFFFFull);
    *lo = (mid << 32) | (p00 & 0xFFFFFFFFull);
    *hi = p11 + (p01 >> 32) + (p10 >> 32) + (mid >> 32);
}

// r <- r + round_half_even(p * K / B), K = dt * A; returns false on overflow of the position range
template <int N>
HD bool drift(W<N>& r, int64_t p, uint64_t K) {
    bool neg_p = p < 0;
    uint64_t mag = neg_p ? (uint64_t)(-(p + 1)) + 1 : (uint64_t)p;
    uint64_t hi, lo, rem;
    mul64(mag, K, &hi, &lo);
    uint64_t t = divlu(hi, lo, DRIFT_B, &rem);   // |p| K = t B + rem
    // exact displacement sign * (t + rem / B); floor it first
    int64_t fl = neg_p ? -(int64_t)t - (rem ? 1 : 0) : (int64_t)t;
    uint64_t frac_num = neg_p ? (rem ? DRIFT_B - rem : 0) : rem;   // (value - floor) * B
    // round half even ON THE DISPLACEMENT: > 1/2 up; == 1/2 up iff its floor is odd (never the parity of r)
    if (2 * frac_num > DRIFT_B || (2 * frac_num == DRIFT_B && (fl & 1))) fl += 1;
    W<N> inc = from_i64<N>(fl);
    W<N> s = add(r, inc);
    bool ovf = add_overflows(r, inc, s);
    r = s;
    return !ovf;
}

HD bool kick(int64_t& p, int64_t J) {
    int64_t s = (int64_t)((uint64_t)p + (uint64_t)J);
    bool ovf = ((p ^ s) & (J ^ s)) < 0;
    p = s;
    return !ovf;
}

template <int N>
HD double to_double(const W<N>& a) {  // approximate (timing-proxy input only)
    W<N> m = negative(a) ? neg(a) : a;
    double v = 0;
    for (int i = N - 1; i >= 0; i--) v = v * 4294967296.0 + m.w[i];
    return negative(a) ? -v : v;
}

template <int N>
struct Pair {
    W<N> ri[3], rj[3];
    int64_t pi[3], pj[3];
};

template <int N>
struct Out {
    W<N + 1> dr[3];
    W<2 * N + 3> R2;
};

template <int N>
HD bool op_drift(Pair<N>& s, uint64_t K) {
    bool ok = true;
    for (int k = 0; k < 3; k++) {
        ok &= drift(s.ri[k], s.pi[k], K);
        ok &= drift(s.rj[k], s.pj[k], K);
    }
    return ok;
}
template <int N>
HD void op_dr(const Pair<N>& s, Out<N>& o) {
    for (int k = 0; k < 3; k++) o.dr[k] = sub(widen<N + 1>(s.rj[k]), widen<N + 1>(s.ri[k]));
}
template <int N>
HD void op_R2(Out<N>& o) {
    W<2 * N + 3> acc;
    for (int i = 0; i < 2 * N + 3; i++) acc.w[i] = 0;
    for (int k = 0; k < 3; k++) acc = add(acc, widen<2 * N + 3>(square(o.dr[k])));
    o.R2 = acc;
}
template <int N>
HD bool op_kick(Pair<N>& s, const int64_t* J) {
    bool ok = true;
    for (int k = 0; k < 3; k++) {
        ok &= kick(s.pj[k], J[k]);
        ok &= kick(s.pi[k], -J[k]);
    }
    return ok;
}

}  // namespace bench
