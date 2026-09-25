// CPU (single thread) benchmark of C1-B1 state operations by position width (designer 13th ed. item 10).
// Usage: bench_state check <limbs 2|3|4> <npairs> <out.txt>
//        bench_state time  <limbs> <npairs> <iters>          -> ns per pair for drift, dr, R2, kick, bundle
//        bench_state e2e   <limbs> <npairs>                  -> us per pair: bundle + one C1-A F(R) evaluation (B0)
#include "ar2_core.hpp"
#include "bench_state_io.hpp"

static Int accumulate(const std::vector<Int>& xs) {
    Int s;
    for (const Int& x : xs) s = iadd(s, x);
    return s;
}

using namespace bench;

template <int N>
static int check(size_t n, const char* out) {
    std::vector<Pair<N>> ps;
    std::vector<int64_t> Js;
    make_pairs<N>(ps, Js, n);
    std::string text;
    for (size_t i = 0; i < n; i++) {
        Out<N> o;
        bool ok = op_drift(ps[i], K_DRIFT);
        ok &= op_kick(ps[i], &Js[3 * i]);
        op_dr(ps[i], o);
        op_R2(o);
        text += check_line(ps[i], o, ok) + "\n";
    }
    std::ofstream(out) << text;
    return 0;
}

template <int N>
static int timing(size_t n, int iters) {
    std::vector<Pair<N>> ps;
    std::vector<int64_t> Js;
    make_pairs<N>(ps, Js, n);
    std::vector<Out<N>> os(n);
    volatile uint32_t sink = 0;
    auto run = [&](int which) {
        double t0 = now_s();
        uint32_t acc = 0;
        for (int it = 0; it < iters; it++)
            for (size_t i = 0; i < n; i++) {
                if (which == 0 || which == 4) acc += op_drift(ps[i], K_DRIFT);
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

template <int N>
static int e2e(size_t n) {
    std::vector<Pair<N>> ps;
    std::vector<int64_t> Js;
    make_pairs<N>(ps, Js, n);
    // bring the pairs to C1-B1 distances (5..20 bohr) so the F evaluation sees realistic R
    Rng g;
    for (auto& p : ps)
        for (int k = 0; k < 3; k++) p.rj[k] = add(p.ri[k], from_i64<N>(g.range(6ll << 48)));
    ar2::Cache cache;
    ar2::Profile b64{false, 64, 0};
    double t0 = now_s();
    size_t done = 0;
    for (size_t i = 0; i < n; i++) {
        Out<N> o;
        op_drift(ps[i], K_DRIFT);
        op_dr(ps[i], o);
        op_R2(o);
        double R = std::sqrt(to_double(o.R2)) / 281474976710656.0;   // 2^48: timing-proxy input
        if (R < 2.3) continue;
        char buf[32];
        snprintf(buf, sizeof buf, "%016llx", (unsigned long long)bits_of(R));
        std::string a = ar2::answer('F', true, b64, buf, cache);
        op_kick(ps[i], &Js[3 * i]);
        done++;
    }
    double dt = now_s() - t0;
    printf("e2e_us %.2f pairs %zu\n", dt / done * 1e6, done);
    return 0;
}

int main(int argc, char** argv) {
    if (argc < 4) return 2;
    std::string mode = argv[1];
    int L = atoi(argv[2]);
    size_t n = (size_t)atoll(argv[3]);
    auto dispatch = [&](auto tag) -> int {
        constexpr int N = decltype(tag)::value;
        if (mode == "check") return check<N>(n, argv[4]);
        if (mode == "time") return timing<N>(n, atoi(argv[4]));
        if (mode == "e2e") return e2e<N>(n);
        return 2;
    };
    if (L == 2) return dispatch(std::integral_constant<int, 2>());
    if (L == 3) return dispatch(std::integral_constant<int, 3>());
    if (L == 4) return dispatch(std::integral_constant<int, 4>());
    return 2;
}
