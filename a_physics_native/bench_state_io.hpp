// Host-side helpers shared by bench_state.cpp (CPU) and bench_state.cu (CUDA): deterministic pair generation,
// the check-mode text format (hex limbs), and the op list. Benchmark only.
#pragma once
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "bench_state.hpp"

namespace bench {

constexpr uint64_t DT = 40;                                   // a.u.
constexpr uint64_t K_DRIFT = DT * DRIFT_A;
constexpr int64_t TIE_P = 4995297890462500ll;                 // |p| raw giving an exact half-unit drift at dt = 40                    // p * K / B = p * dt / m in raw FX(.,48) units

struct Rng {
    uint64_t z = 0x9E3779B97F4A7C15ull;
    uint64_t next() { z ^= z << 13; z ^= z >> 7; z ^= z << 17; return z; }
    int64_t range(int64_t lim) { return (int64_t)(next() % (2 * (uint64_t)lim + 1)) - lim; }
};

// positions within +-1000 bohr (raw 2^48 units), momenta within +-50 a.u., J within +-0.01 a.u.
template <int R, int N>
static void make_pairs(std::vector<Pair<N>>& ps, std::vector<int64_t>& Js, size_t n) {
    Rng g;
    ps.resize(n);
    Js.resize(3 * n);
    const int64_t RR = 1000ll << 48, P = 50ll << 48, J = (1ll << 48) / 100;
    for (size_t i = 0; i < n; i++) {
        for (int k = 0; k < 3; k++) {
            ps[i].ri[k] = to_units<R>(from_i64<N>(g.range(RR)));
            ps[i].rj[k] = to_units<R>(from_i64<N>(g.range(RR)));
            ps[i].pi[k] = g.range(P);
            ps[i].pj[k] = g.range(P);
            Js[3 * i + k] = g.range(J);
        }
        if (i % 8 == 0) {                            // exact drift ties: p dt / m is exactly half a raw unit
            ps[i].pi[0] = (i % 16 == 0 ? 1 : -1) * TIE_P;
            ps[i].pj[1] = TIE_P;
        }
    }
}

template <int N>
static std::string hex(const W<N>& a) {
    std::string s;
    char b[16];
    for (int i = N - 1; i >= 0; i--) {
        snprintf(b, sizeof b, "%08x", a.w[i]);
        s += b;
    }
    return s;
}

constexpr double UNITS_PER_BOHR[3] = {281474976710656.0, 281474976710656.0,
                                     281474976710656.0 * 399623831237000000.0};

// one line per pair after: drift (both atoms), kick +-J, dr, R2
template <int N>
static std::string check_line(const Pair<N>& s, const Out<N>& o, bool ok) {
    std::string l = ok ? "ok" : "ovf";
    for (int k = 0; k < 3; k++) l += " " + hex(s.ri[k]);
    for (int k = 0; k < 3; k++) l += " " + hex(s.rj[k]);
    char b[24];
    for (int k = 0; k < 3; k++) { snprintf(b, sizeof b, " %016llx", (unsigned long long)s.pi[k]); l += b; }
    for (int k = 0; k < 3; k++) { snprintf(b, sizeof b, " %016llx", (unsigned long long)s.pj[k]); l += b; }
    for (int k = 0; k < 3; k++) l += " " + hex(o.dr[k]);
    l += " " + hex(o.R2);
    return l;
}

static double now_s() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

}  // namespace bench
