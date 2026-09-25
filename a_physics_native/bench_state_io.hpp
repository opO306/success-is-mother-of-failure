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
constexpr uint64_t K_DRIFT = DT * DRIFT_A;                    // p * K / B = p * dt / m in raw FX(.,48) units

struct Rng {
    uint64_t z = 0x9E3779B97F4A7C15ull;
    uint64_t next() { z ^= z << 13; z ^= z >> 7; z ^= z << 17; return z; }
    int64_t range(int64_t lim) { return (int64_t)(next() % (2 * (uint64_t)lim + 1)) - lim; }
};

// positions within +-1000 bohr (raw 2^48 units), momenta within +-50 a.u., J within +-0.01 a.u.
template <int N>
static void make_pairs(std::vector<Pair<N>>& ps, std::vector<int64_t>& Js, size_t n) {
    Rng g;
    ps.resize(n);
    Js.resize(3 * n);
    const int64_t R = 1000ll << 48, P = 50ll << 48, J = (1ll << 48) / 100;
    for (size_t i = 0; i < n; i++) {
        for (int k = 0; k < 3; k++) {
            ps[i].ri[k] = from_i64<N>(g.range(R));
            ps[i].rj[k] = from_i64<N>(g.range(R));
            ps[i].pi[k] = g.range(P);
            ps[i].pj[k] = g.range(P);
            Js[3 * i + k] = g.range(J);
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
