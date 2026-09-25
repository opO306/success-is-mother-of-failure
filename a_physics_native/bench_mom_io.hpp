// Host-side helpers for the momentum-representation benchmark (bench_mom.hpp): deterministic inputs (the same draws
// as a_physics_native/bench_state.py expected_mom), check-line format, kind names. Benchmark only.
#pragma once
#include "bench_mom.hpp"
#include "bench_state_io.hpp"

namespace bench {

// the momentum grids: base value on 2^-48 plus S extra fraction bits taken from a 64-bit draw
template <class M>
struct Gen;
template <int L, int F>
struct Gen<MFX<L, F>> {
    static constexpr int S = F - 48;
    static W<L> fine(int64_t base, uint64_t x) {       // base 2^S + (x mod 2^S), exact
        W<L> b = from_i64<L>(base), sh;
        for (int i = 0; i < L; i++) sh.w[i] = 0;
        for (int i = 0; i < L; i++) {                   // sh = b << S
            int w = S >> 5, bitsh = S & 31, dst = i + w;
            if (dst < L) sh.w[dst] |= bitsh ? b.w[i] << bitsh : b.w[i];
            if (bitsh && dst + 1 < L) sh.w[dst + 1] |= b.w[i] >> (32 - bitsh);
        }
        uint64_t ext = S == 0 ? 0 : S >= 64 ? x : (x & ((1ull << S) - 1));
        W<L> e;
        for (int i = 0; i < L; i++) e.w[i] = i == 0 ? (uint32_t)ext : i == 1 ? (uint32_t)(ext >> 32) : 0u;
        return add(sh, e);
    }
    static MFX<L, F> mom(int64_t base, uint64_t x, bool tie) { return MFX<L, F>{fine(base, tie ? 0 : x)}; }
    static W<L> J(int64_t base, uint64_t x) { return fine(base, x); }
    static std::string hex(const MFX<L, F>& m) { return bench::hex(m.p); }
};
constexpr uint64_t HALF_COARSE = 1ull << 62;           // carry residual bound, in 2^-111 units
inline int64_t range_of(uint64_t x, uint64_t lim) { return (int64_t)(x % (2 * lim + 1)) - (int64_t)lim; }
template <>
struct Gen<MCarry> {
    static MCarry mom(int64_t base, uint64_t x, bool tie) { return MCarry{base, tie ? 0 : range_of(x, HALF_COARSE)}; }
    static W<4> J(int64_t base, uint64_t x) {           // base 2^63 + range(x, 2^62)
        uint64_t lo = (uint64_t)base, hi = base < 0 ? ~0ull : 0ull;
        uint64_t slo = lo << 63, shi = (hi << 63) | (lo >> 1);
        W<4> sh;
        sh.w[0] = (uint32_t)slo; sh.w[1] = (uint32_t)(slo >> 32); sh.w[2] = (uint32_t)shi; sh.w[3] = (uint32_t)(shi >> 32);
        return add(sh, from_i64<4>(range_of(x, HALF_COARSE)));
    }
    static std::string hex(const MCarry& m) {
        char b[40];
        snprintf(b, sizeof b, "%016llx:%016llx", (unsigned long long)m.c, (unsigned long long)m.r);
        return b;
    }
};

template <class M>
static void make_mpairs(std::vector<MPair<M>>& ps, std::vector<typename MJ<M>::T>& Js, size_t n) {
    Rng g;
    ps.resize(n);
    Js.resize(3 * n);
    const int64_t RR = 1000ll << 48, P = 50ll << 48, J = (1ll << 48) / 100;
    for (size_t i = 0; i < n; i++) {
        for (int k = 0; k < 3; k++) {
            ps[i].pos.ri[k] = from_i64<3>(g.range(RR));
            ps[i].pos.rj[k] = from_i64<3>(g.range(RR));
            int64_t bi = g.range(P), bj = g.range(P), bJ = g.range(J);
            uint64_t xi = g.next(), xj = g.next(), xJ = g.next();
            bool tie_i = i % 8 == 0 && k == 0, tie_j = i % 8 == 0 && k == 1;
            if (tie_i) bi = (i % 16 == 0 ? 1 : -1) * TIE_P;
            if (tie_j) bj = TIE_P;
            ps[i].pi[k] = Gen<M>::mom(bi, xi, tie_i);
            ps[i].pj[k] = Gen<M>::mom(bj, xj, tie_j);
            Js[3 * i + k] = Gen<M>::J(bJ, xJ);
        }
    }
}

template <class M>
static std::string mcheck_line(const MPair<M>& s, const Out<3>& o, bool ok) {
    std::string l = ok ? "ok" : "ovf";
    for (int k = 0; k < 3; k++) l += " " + hex(s.pos.ri[k]);
    for (int k = 0; k < 3; k++) l += " " + hex(s.pos.rj[k]);
    for (int k = 0; k < 3; k++) l += " " + Gen<M>::hex(s.pi[k]);
    for (int k = 0; k < 3; k++) l += " " + Gen<M>::hex(s.pj[k]);
    for (int k = 0; k < 3; k++) l += " " + hex(o.dr[k]);
    l += " " + hex(o.R2);
    return l;
}

// kind names shared with Python
using MFX64_48 = MFX<2, 48>;
using MFX80_64 = MFX<3, 64>;       // stored in 3 limbs (96 bits)
using MFX96_80 = MFX<3, 80>;
using MFX128_112 = MFX<4, 112>;
#define BENCH_MOM_KINDS(X) X("fx64_48", MFX64_48) X("fx80_64", MFX80_64) X("fx96_80", MFX96_80) \
    X("fx128_112", MFX128_112) X("carry", MCarry)

}  // namespace bench
