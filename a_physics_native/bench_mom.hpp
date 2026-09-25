// Benchmark-only momentum kernels for the C1-B1 momentum-precision comparison (designer 15th ed.). NOT a world
// executor. Position FX(96,48) (3 limbs) with drift v2; the momentum representation varies:
//   FX(64,48) FX(80,64) FX(96,80) FX(128,112)  -- two's complement limbs, fraction F bits
//   CARRY                                       -- coarse int64 on 2^-48 (what the drift moves with) + residual int64
//                                                  on 2^-111 (|r| <= 2^62); each kick lands on the fine grid and is
//                                                  split again, round half even (odd-symmetric)
// Operations (per pair, 3 components): drift r <- r + round_half_even(p dt / m) on the 2^-48 position grid (p on
// its own grid: displacement = p K / (B 2^(F-48)), K = dt A), kick p <- p +- J (J on the momentum's fine grid),
// dr and R^2 as in bench_state.hpp. Every operation is exact and checked bit for bit against Python
// (a_physics_native/bench_state.py, expected_mom).
#pragma once
#include "bench_state.hpp"

namespace bench {

template <int L>
HD W<L + 2> mul_u64(const W<L>& m, uint64_t k) {  // non-negative m times k
    W<L + 2> out;
    for (int i = 0; i < L + 2; i++) out.w[i] = 0;
    const uint64_t k0 = k & 0xFFFFFFFFull, k1 = k >> 32;
    for (int part = 0; part < 2; part++) {
        uint64_t b = part ? k1 : k0, c = 0;
        int i = 0;
        for (; i < L; i++) {
            uint64_t t = (uint64_t)m.w[i] * b + out.w[i + part] + c;
            out.w[i + part] = (uint32_t)t;
            c = t >> 32;
        }
        for (int j = i + part; j < L + 2 && c; j++) {
            uint64_t t = (uint64_t)out.w[j] + c;
            out.w[j] = (uint32_t)t;
            c = t >> 32;
        }
    }
    return out;
}

template <int L>
HD uint64_t divmod_u64(W<L>& a, uint64_t d) {  // a <- a / d (non-negative), returns the remainder
    uint64_t rem = 0;
    for (int i = L - 1; i >= 0; i--) {
        uint64_t r2, q = divlu(rem >> 32, (rem << 32) | a.w[i], d, &r2);
        a.w[i] = (uint32_t)q;
        rem = r2;
    }
    return rem;
}

template <int L>
HD bool bit(const W<L>& a, int i) { return (a.w[i >> 5] >> (i & 31)) & 1u; }
template <int L>
HD bool any_below(const W<L>& a, int n) {  // any of bits [0, n) set
    for (int i = 0; i < (n >> 5); i++)
        if (a.w[i]) return true;
    return (n & 31) && (a.w[n >> 5] & ((1u << (n & 31)) - 1u));
}
template <int L>
HD uint64_t bits64(const W<L>& a, int s) {  // bits [s, s + 64) as an unsigned integer
    uint64_t v = 0;
    for (int i = 63; i >= 0; i--) {
        int j = s + i;
        v = (v << 1) | (j < 32 * L ? (uint64_t)bit(a, j) : 0u);
    }
    return v;
}

// round_half_even(p K / (B 2^s)) for p on a 2^-(48+s) grid, as a raw 2^-48 displacement (fits int64 by contract)
template <int L>
HD int64_t disp_raw(const W<L>& p, int s, uint64_t K) {
    bool ng = negative(p);
    W<L> m = ng ? neg(p) : p;
    W<L + 2> q = mul_u64<L>(m, K);
    uint64_t rem = divmod_u64<L + 2>(q, DRIFT_B);
    uint64_t fl = bits64<L + 2>(q, s);
    bool up;
    if (s == 0) {
        up = 2 * rem > DRIFT_B || (2 * rem == DRIFT_B && (fl & 1));
    } else {
        bool top = bit<L + 2>(q, s - 1), rest = any_below<L + 2>(q, s - 1) || rem;
        up = top && (rest || (fl & 1));
    }
    int64_t d = (int64_t)(fl + (up ? 1 : 0));
    return ng ? -d : d;
}

template <int L, int F>
struct MFX {  // momentum FX(32 L, F)
    W<L> p;
    static constexpr int S = F - 48;
    HD int64_t disp(uint64_t K) const { return disp_raw<L>(p, S, K); }
    HD bool kick(const W<L>& J) {
        W<L> s = add(p, J);
        bool ovf = add_overflows(p, J, s);
        p = s;
        return !ovf;
    }
};

struct MCarry {  // coarse int64 at 2^-48 + residual int64 at 2^-111; J is a 128-bit fine value
    int64_t c, r;
    HD int64_t disp(uint64_t K) const { return disp_raw<2>(from_i64<2>(c), 0, K); }
    HD bool kick(const W<4>& J) {
        // total = c 2^63 + r + J (exact, 128-bit two's complement), then c' = round_half_even(total / 2^63),
        // r' = total - c' 2^63 (|r'| <= 2^62, so its low 64 bits are exact)
        uint64_t lo = (uint64_t)c, hi = c < 0 ? ~0ull : 0ull;
        uint64_t slo = lo << 63, shi = (hi << 63) | (lo >> 1);
        W<4> sh;
        sh.w[0] = (uint32_t)slo; sh.w[1] = (uint32_t)(slo >> 32); sh.w[2] = (uint32_t)shi; sh.w[3] = (uint32_t)(shi >> 32);
        W<4> tot = add(add(sh, from_i64<4>(r)), J);
        bool ng = negative(tot);
        W<4> m = ng ? neg(tot) : tot;
        uint64_t fl = bits64<4>(m, 63);
        bool top = bit<4>(m, 62), rest = any_below<4>(m, 62);
        uint64_t q = fl + ((top && (rest || (fl & 1))) ? 1 : 0);
        bool ovf = q > 0x7FFFFFFFFFFFFFFFull;
        int64_t cn = ng ? -(int64_t)q : (int64_t)q;
        uint64_t tlo = (uint64_t)tot.w[0] | ((uint64_t)tot.w[1] << 32);
        c = cn;
        r = (int64_t)(tlo - ((uint64_t)cn << 63));
        return !ovf;
    }
};

template <class M>
struct MJ;
template <int L, int F>
struct MJ<MFX<L, F>> { using T = W<L>; };
template <>
struct MJ<MCarry> { using T = W<4>; };

template <class M>
struct MPair {
    Pair<3> pos;       // positions FX(96,48); the int64 momentum fields of Pair are unused here
    M pi[3], pj[3];
};

template <class M>
HD bool mop_drift(MPair<M>& s, uint64_t K) {
    bool ok = true;
    for (int k = 0; k < 3; k++) {
        W<3> a = from_i64<3>(s.pi[k].disp(K)), b = from_i64<3>(s.pj[k].disp(K));
        W<3> x = add(s.pos.ri[k], a), y = add(s.pos.rj[k], b);
        ok &= !add_overflows(s.pos.ri[k], a, x) && !add_overflows(s.pos.rj[k], b, y);
        s.pos.ri[k] = x;
        s.pos.rj[k] = y;
    }
    return ok;
}

template <class M>
HD bool mop_kick(MPair<M>& s, const typename MJ<M>::T* J) {
    bool ok = true;
    for (int k = 0; k < 3; k++) {
        ok &= s.pj[k].kick(J[k]);
        ok &= s.pi[k].kick(neg(J[k]));
    }
    return ok;
}

}  // namespace bench
