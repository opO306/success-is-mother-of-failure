// B0: serial native evaluator of the C1-A Ar-Ar V(R) and F(R) (ar2_core.hpp). No threads.
// Usage: ar2_b0 <queries.txt> <answers.txt>   |   ar2_b0 selftest
#include "ar2_core.hpp"

#include <chrono>

static Int accumulate(const std::vector<Int>& xs) {  // required by anvm_core; unused here
    Int s;
    for (const Int& x : xs) s = iadd(s, x);
    return s;
}

// Knuth division against anvm_core's bitwise division on deterministic pseudo-random operands
static int selftest() {
    uint64_t z = 0x9E3779B97F4A7C15ull;
    auto next = [&]() { z ^= z << 13; z ^= z >> 7; z ^= z << 17; return (uint32_t)z; };
    for (int t = 0; t < 3000; t++) {
        Mag a(1 + next() % 40), b(1 + next() % 20);
        for (auto& w : a) w = next();
        for (auto& w : b) w = next();
        if (t % 3 == 0) b.back() = 1 + (next() & 3);        // small top limb: large normalisation shift
        if (t % 5 == 0) for (auto& w : b) w = 0xFFFFFFFFu;   // qhat correction paths
        trim(a); trim(b);
        if (b.empty()) continue;
        Mag q1, r1, q2, r2;
        divmod(a, b, q1, r1);
        ar2::divmod_knuth(a, b, q2, r2);
        if (cmp(q1, q2) || cmp(r1, r2)) { fprintf(stderr, "divmod mismatch at %d\n", t); return 1; }
    }
    printf("selftest ok\n");
    return 0;
}

// a fair plain binary64 V and F for timing: constants parsed once, every operation rounded, platform exp
struct PlainModel {
    struct S { double al; int imin; std::vector<double> a; };
    struct C { std::vector<S> s; double eta; int kmin, kadd, ret; std::vector<double> c; };
    std::vector<C> comps;
    std::vector<double> A, B;
    PlainModel() {
        for (const ar2::Component& c : ar2::model()) {
            C d{{}, strtod(c.eta, nullptr), c.kmin, c.kadd, c.ret_kind, {}};
            for (const ar2::ShortTerm& st : c.shorts) {
                S x{strtod(st.alpha, nullptr), st.imin, {}};
                for (const char* a : st.a) x.a.push_back(strtod(a, nullptr));
                d.s.push_back(x);
            }
            for (const char* k : c.C) d.c.push_back(strtod(k, nullptr));
            comps.push_back(d);
        }
        for (const char* a : ar2::RET_A) A.push_back(strtod(a, nullptr));
        for (const char* b : ar2::RET_B) B.push_back(strtod(b, nullptr));
    }
    void eval(double r, double& v, double& f) const {
        v = 0;
        double dv = 0, ri = 1 / r;
        for (const C& c : comps) {
            for (const S& st : c.s) {
                double e = exp(-st.al * r), P = 0, dP = 0, rp = st.imin < 0 ? ri : 1;
                for (size_t t = 0; t < st.a.size(); t++) {
                    int i = st.imin + (int)t;
                    P += st.a[t] * rp;
                    dP += i * st.a[t] * rp * ri;
                    rp *= r;
                }
                v += e * P;
                dv += e * (dP - st.al * P);
            }
            double x = c.eta * r, ex = exp(-x), s = 1, piece = 1;
            int done = 0;
            double r2k = 1;
            for (int k = 0; k < c.kmin; k++) r2k *= r * r;
            for (size_t t = 0; t < c.c.size(); t++, r2k *= r * r) {
                int k = c.kmin + (int)t, n = 2 * k + c.kadd;
                for (; done < n; done++) { piece *= x / (done + 1); s += piece; }
                double T = ex * s, D = 1 - T, dD = c.eta * ex * piece;
                if (c.ret == 1 && t == 0) {
                    double N = 1, Dn = 1, dN = 0, dDn = 0, rp = 1;
                    for (size_t m = 0; m < B.size(); m++) {
                        if (m < A.size()) { dN += (m + 1) * A[m] * rp; N += A[m] * rp * r; }
                        dDn += (m + 1) * B[m] * rp; Dn += B[m] * rp * r;
                        rp *= r;
                    }
                    D = N / Dn - T;
                    dD += (dN * Dn - N * dDn) / (Dn * Dn);
                } else if (c.ret == 2 && t == 0) {
                    D = -T;
                }
                v -= c.c[t] * D / r2k;
                dv -= c.c[t] * (dD / r2k - 2 * k * D / (r2k * r));
            }
        }
        f = -dv;
    }
};

// in-process timing, no file I/O: n binary64 distances spread over [lo, hi] bohr, V and F (retardation on);
// the contract path against a plain binary64 evaluation (every operation rounded, platform exp)
static int bench(int n, double lo, double hi) {
    std::vector<std::string> raws;
    for (int i = 0; i < n; i++) {
        char buf[32];
        snprintf(buf, sizeof buf, "%016llx", (unsigned long long)bits_of(lo + (hi - lo) * (i + 0.5) / n));
        raws.push_back(buf);
    }
    ar2::Cache cache;
    ar2::Profile p{false, 64, 0};
    std::vector<std::string> exact;
    auto t0 = std::chrono::steady_clock::now();
    for (const std::string& r : raws)
        for (char q : {'V', 'F'}) exact.push_back(ar2::answer(q, true, p, r, cache));
    auto t1 = std::chrono::steady_clock::now();
    std::vector<std::string> plain;
    volatile double sink = 0;
    for (const std::string& r : raws) {
        Term t = decode(strtoull(r.c_str(), nullptr, 16));
        ar2::Dyadic R{t.m, t.e};
        for (bool d : {false, true}) plain.push_back(ar2::plain_binary64(R, true, d));
    }
    auto t2 = std::chrono::steady_clock::now();
    PlainModel pm;
    std::vector<double> fast;
    auto t3 = std::chrono::steady_clock::now();
    for (int rep = 0; rep < 20; rep++) {
        fast.clear();
        for (const std::string& r : raws) {
            double v, f;
            pm.eval(dbl(strtoull(r.c_str(), nullptr, 16)), v, f);
            fast.push_back(v);
            fast.push_back(f);
        }
    }
    auto t4 = std::chrono::steady_clock::now();
    int differ_fast = 0;
    for (size_t i = 0; i < exact.size(); i++) {
        char buf[32];
        snprintf(buf, sizeof buf, "%016llx", (unsigned long long)bits_of(fast[i]));
        if (exact[i].substr(3, 16) != buf) differ_fast++;
    }
    printf("fair plain binary64 (constants pre-parsed): %.3f us/query, differs from the contract on %d of %zu\n",
           std::chrono::duration<double, std::micro>(t4 - t3).count() / (20.0 * fast.size()), differ_fast, fast.size());
    int differ = 0;
    for (size_t i = 0; i < exact.size(); i++)
        if (exact[i].substr(3, 16) != plain[i]) differ++;
    double us_exact = std::chrono::duration<double, std::micro>(t1 - t0).count() / exact.size();
    double us_plain = std::chrono::duration<double, std::micro>(t2 - t1).count() / plain.size();
    printf("exact %.2f us/query, plain binary64 %.3f us/query, plain differs from the contract on %d of %zu\n",
           us_exact, us_plain, differ, exact.size());
    (void)sink;
    return 0;
}

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "selftest") return selftest();
    if (argc == 5 && std::string(argv[1]) == "bench") return bench(atoi(argv[2]), atof(argv[3]), atof(argv[4]));
    if (argc != 3) {
        fprintf(stderr, "usage: ar2_b0 <queries.txt> <answers.txt>\n");
        return 2;
    }
    std::vector<ar2::Query> qs = ar2::read_queries(argv[1]);
    std::vector<std::string> ans;
    ar2::Cache cache;
    for (const ar2::Query& q : qs) ans.push_back(ar2::answer(q.qty, q.ret, q.p, q.raw, cache));
    ar2::write_answers(argv[2], ans);
    return 0;
}
