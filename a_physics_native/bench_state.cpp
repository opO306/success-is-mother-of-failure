// CPU (single thread) benchmark of C1-B1 state operations by position width (designer 13th ed. item 10).
// Usage: bench_state check <rule v1|v2|exact> <limbs> <npairs> <out.txt>
//        bench_state time  <rule> <limbs> <npairs> <iters>   -> ns per pair for drift, dr, R2, kick, bundle
//        bench_state e2e   <rule> <limbs> <npairs>           -> us per pair: bundle + one C1-A F(R) evaluation (B0)
// limbs 2|3|4 for v1 / v2 (FX(64|96|128,48)), 5 for exact (160-bit positions in units 2^-48 / B bohr)
#include "ar2_core.hpp"
#include "bench_state_io.hpp"

static Int accumulate(const std::vector<Int>& xs) {
    Int s;
    for (const Int& x : xs) s = iadd(s, x);
    return s;
}

using namespace bench;

template <int R, int N>
static int check(size_t n, const char* out) {
    std::vector<Pair<N>> ps;
    std::vector<int64_t> Js;
    make_pairs<R, N>(ps, Js, n);
    std::string text;
    for (size_t i = 0; i < n; i++) {
        Out<N> o;
        bool ok = op_drift<R>(ps[i], K_DRIFT);
        ok &= op_kick(ps[i], &Js[3 * i]);
        op_dr(ps[i], o);
        op_R2(o);
        text += check_line(ps[i], o, ok) + "\n";
    }
    std::ofstream(out) << text;
    return 0;
}

template <int R, int N>
static int timing(size_t n, int iters) {
    std::vector<Pair<N>> ps;
    std::vector<int64_t> Js;
    make_pairs<R, N>(ps, Js, n);
    std::vector<Out<N>> os(n);
    volatile uint32_t sink = 0;
    auto run = [&](int which) {
        double t0 = now_s();
        uint32_t acc = 0;
        for (int it = 0; it < iters; it++)
            for (size_t i = 0; i < n; i++) {
                if (which == 0 || which == 4) acc += op_drift<R>(ps[i], K_DRIFT);
                if (which == 1 || which == 4) op_dr(ps[i], os[i]);
                if (which == 2 || which == 4) { if (which == 2) op_dr(ps[i], os[i]); op_R2(os[i]); }
                if (which == 3 || which == 4) acc += op_kick(ps[i], &Js[3 * i]);
                acc += os[i].R2.w[0] ^ os[i].dr[0].w[0];
            }
        sink = sink + acc;
        return (now_s() - t0) / ((double)n * iters) * 1e9;
    };
    const char* names[] = {"drift", "dr", "dr+R2", "kick", "bundle"};
    for (int w = 0; w < 5; w++) printf("%s %.2f\n", names[w], run(w));
    return 0;
}

template <int R, int N>
static int e2e(size_t n) {
    std::vector<Pair<N>> ps;
    std::vector<int64_t> Js;
    make_pairs<R, N>(ps, Js, n);
    // bring the pairs to C1-B1 distances (5..20 bohr) so the F evaluation sees realistic R
    Rng g;
    for (auto& p : ps)
        for (int k = 0; k < 3; k++) p.rj[k] = add(p.ri[k], to_units<R>(from_i64<N>(g.range(6ll << 48))));
    ar2::Cache cache;
    ar2::Profile b64{false, 64, 0};
    double t0 = now_s();
    size_t done = 0;
    for (size_t i = 0; i < n; i++) {
        Out<N> o;
        op_drift<R>(ps[i], K_DRIFT);
        op_dr(ps[i], o);
        op_R2(o);
        double Rb = std::sqrt(to_double(o.R2)) / UNITS_PER_BOHR[R];  // timing-proxy input
        if (Rb < 2.3) continue;
        char buf[32];
        snprintf(buf, sizeof buf, "%016llx", (unsigned long long)bits_of(Rb));
        std::string a = ar2::answer('F', true, b64, buf, cache);
        op_kick(ps[i], &Js[3 * i]);
        done++;
    }
    double dt = now_s() - t0;
    printf("e2e_us %.2f pairs %zu\n", dt / done * 1e6, done);
    return 0;
}

int main(int argc, char** argv) {
    if (argc < 5) return 2;
    std::string mode = argv[1], rule = argv[2];
    int L = atoi(argv[3]);
    size_t n = (size_t)atoll(argv[4]);
    auto go = [&](auto r, auto l) -> int {
        constexpr int R = decltype(r)::value, N = decltype(l)::value;
        if (mode == "check") return check<R, N>(n, argv[5]);
        if (mode == "time") return timing<R, N>(n, atoi(argv[5]));
        if (mode == "e2e") return e2e<R, N>(n);
        return 2;
    };
    using std::integral_constant;
    if (rule == "exact" && L == 5) return go(integral_constant<int, EXACT>(), integral_constant<int, 5>());
    auto by_limbs = [&](auto r) -> int {
        if (L == 2) return go(r, integral_constant<int, 2>());
        if (L == 3) return go(r, integral_constant<int, 3>());
        if (L == 4) return go(r, integral_constant<int, 4>());
        return 2;
    };
    if (rule == "v1") return by_limbs(integral_constant<int, V1>());
    if (rule == "v2") return by_limbs(integral_constant<int, V2>());
    return 2;
}
