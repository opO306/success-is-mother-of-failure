// C1-A native evaluator core: the Lang-Przybytek-Lesiuk 2024 Ar-Ar potential V(R) and radial force
// F(R) = -dV/dR, each the EXACT model value rounded once (contract c1a-ar2-lang2024-v1).
//
// docs/current/A_MICRO_V6_ARAR_POTENTIAL_SURVEY_V1.md 11 (designer 9th ed.). Judged against the Python
// reference evaluator (a_reference/ar2_lang2024.py) and its Git fixture; never calls it. Written separately:
//   * fixed-point INTERVAL arithmetic at 2^-M on the arbitrary-precision integers of anvm_core.hpp,
//     every operation rounded outward (floor for the lower end, ceil for the upper), so the true value is
//     always inside [lo, hi];
//   * e^-x from anvm_core's verified Taylor-and-squaring enclosure (itself judged against the VM);
//   * the derivative is analytic (f_n' = e^-x x^n / n!, g' = (N'D - N D') / D^2);
//   * shortcuts that only tighten or bound, never replace, the value: e^-x < 2^-M taken as [0, 2^-M] for
//     x >= 4096 (valid while M <= 5909); for x >= 256 the Tang-Toennies tail e^-x sum_{i<=n} x^i/i! is
//     enclosed by [0, (n+1) e^-256 256^n / n!] (x >= n: the sum is at most (n+1) x^n/n!, and e^-x x^n falls).
// Precision M = 96, 192, ..., 3072; if both ends still round differently the input is REFUSED ("undecided"),
// never guessed. Domain: R < 1.2 A / a0 (a0 = 0.529177210903 A, this contract's source-versioned CODATA 2018
// value) -> physics_domain_exceeded. Capability limit: R > 2^20 bohr -> refused (not physics).
//
// Query line:  <V|F> <retardation 0|1> <B64|FX:W:F> <raw R>
// Answer line: ok <raw> <M> | domain physics_domain_exceeded | halt overflow | refuse <reason>
// INJECT=n compiles a deliberate defect (fault injection, tests only).
#pragma once
#include "anvm_core.hpp"

#include <array>
#include <thread>

namespace ar2 {

static const int M_START = 96;
#ifndef AR2_M_CAP
#define AR2_M_CAP 3072
#endif
static const int M_CAP = AR2_M_CAP;  // tests lower it to show refusal instead of guessing
static const int R_MAX_LOG2 = 20;  // R <= 2^20 bohr

// ---------------------------------------------------------------------------
// Knuth algorithm D (32-bit limbs): q = floor(a / b), r = a mod b. anvm_core's divmod is bitwise.
// ---------------------------------------------------------------------------
static void divmod_knuth(const Mag& a, const Mag& b, Mag& q, Mag& r) {
    if (cmp(a, b) < 0) { q.clear(); r = a; return; }
    size_t n = b.size(), m = a.size() - n;
    if (n == 1) {
        q.assign(a.size(), 0);
        uint64_t rem = 0;
        for (size_t i = a.size(); i-- > 0;) {
            uint64_t cur = (rem << 32) | a[i];
            q[i] = (uint32_t)(cur / b[0]);
            rem = cur % b[0];
        }
        trim(q);
        r = from_u64(rem);
        return;
    }
    int s = 0;
    for (uint32_t t = b.back(); !(t & 0x80000000u); t <<= 1) s++;
    Mag bn(n), an(a.size() + 1);
    for (size_t i = n - 1; i > 0; i--) bn[i] = (b[i] << s) | (s ? (uint32_t)((uint64_t)b[i - 1] >> (32 - s)) : 0);
    bn[0] = b[0] << s;
    an[a.size()] = s ? (uint32_t)((uint64_t)a.back() >> (32 - s)) : 0;
    for (size_t i = a.size() - 1; i > 0; i--) an[i] = (a[i] << s) | (s ? (uint32_t)((uint64_t)a[i - 1] >> (32 - s)) : 0);
    an[0] = a[0] << s;
    q.assign(m + 1, 0);
    const uint64_t B = 1ull << 32;
    for (size_t j = m + 1; j-- > 0;) {
        uint64_t num = ((uint64_t)an[j + n] << 32) | an[j + n - 1];
        uint64_t qhat = num / bn[n - 1], rhat = num % bn[n - 1];
        while (qhat >= B || qhat * bn[n - 2] > ((rhat << 32) | an[j + n - 2])) {
            qhat--;
            rhat += bn[n - 1];
            if (rhat >= B) break;
        }
        int64_t borrow = 0;
        uint64_t carry = 0;
        for (size_t i = 0; i < n; i++) {
            uint64_t p = qhat * bn[i] + carry;
            carry = p >> 32;
            int64_t t = (int64_t)an[i + j] - borrow - (int64_t)(uint32_t)p;
            borrow = t < 0;
            an[i + j] = (uint32_t)t;
        }
        int64_t t = (int64_t)an[j + n] - borrow - (int64_t)carry;
        an[j + n] = (uint32_t)t;
        if (t < 0) {  // added back: qhat was one too large
            qhat--;
            uint64_t c = 0;
            for (size_t i = 0; i < n; i++) {
                uint64_t u = (uint64_t)an[i + j] + bn[i] + c;
                an[i + j] = (uint32_t)u;
                c = u >> 32;
            }
            an[j + n] += (uint32_t)c;
        }
        q[j] = (uint32_t)qhat;
    }
    trim(q);
    r.assign(n, 0);
    for (size_t i = 0; i < n; i++) r[i] = (an[i] >> s) | (s ? (uint32_t)((uint64_t)an[i + 1] << (32 - s)) : 0);
    trim(r);
}

// ---------------------------------------------------------------------------
// Signed floor / ceil helpers on Int (sign + magnitude)
// ---------------------------------------------------------------------------
static Int ceil_shift_neg_aware(const Int& x, int n, bool up) {  // floor (up=false) or ceil of x / 2^n
    if (n <= 0) return mk(x.neg, shl(x.m, -n));
    bool exact = is_zero(low_bits(x.m, n));
    Mag q = shr(x.m, n);
    // |x| / 2^n = q + frac; floor(x) = q (x >= 0) or -(q + [frac > 0]) (x < 0)
    if (!exact && (up != x.neg)) q = add(q, ONE);
    return mk(x.neg, q);
}
static Int floor_shr(const Int& x, int n) { return ceil_shift_neg_aware(x, n, false); }
static Int ceil_shr(const Int& x, int n) { return ceil_shift_neg_aware(x, n, true); }
static Int div_dir(const Int& x, const Mag& d, bool up) {  // floor / ceil of x / d, d > 0
    Mag q, r;
    divmod_knuth(x.m, d, q, r);
    if (!is_zero(r) && (up != x.neg)) q = add(q, ONE);
    return mk(x.neg, q);
}
static Int div10_dir(const Int& x, int d, bool up) {  // floor / ceil of x / 10^d by nested small divisions
    Int y = x;
    while (d > 0) {
        int s = std::min(d, 9);
        uint32_t div = 1;
        for (int i = 0; i < s; i++) div *= 10;
        bool exact;
        Mag q = div_small(y.m, div, &exact);
        if (!exact && (up != y.neg)) q = add(q, ONE);
        y = mk(y.neg, q);
        d -= s;
    }
    return y;
}

// ---------------------------------------------------------------------------
// Exact decimal constants: value = num * 10^p
// ---------------------------------------------------------------------------
struct Dec {
    Int num;
    int p;
};
static Dec dec(const char* s) {
    std::string t(s), digits;
    int exp10 = 0, frac = 0;
    bool neg = false, point = false;
    size_t i = 0;
    if (t[i] == '-' || t[i] == '+') neg = t[i++] == '-';
    for (; i < t.size() && t[i] != 'e' && t[i] != 'E'; i++) {
        if (t[i] == '.') { point = true; continue; }
        digits += t[i];
        if (point) frac++;
    }
    if (i < t.size()) exp10 = atoi(t.c_str() + i + 1);
    return Dec{mk(neg, from_dec(digits)), exp10 - frac};
}
static Mag pow10(int d) {
    Mag r = ONE;
    for (int i = 0; i < d; i++) r = mul(r, from_u64(10));
    return r;
}

// ---------------------------------------------------------------------------
// Intervals at scale 2^M: the real value lies in [lo, hi] / 2^M
// ---------------------------------------------------------------------------
struct IV {
    Int lo, hi;
};
static IV iv_exact(const Int& x) { return IV{x, x}; }
static IV iv_add(const IV& a, const IV& b) { return IV{iadd(a.lo, b.lo), iadd(a.hi, b.hi)}; }
static IV iv_neg(const IV& a) { return IV{ineg(a.hi), ineg(a.lo)}; }
static IV iv_sub(const IV& a, const IV& b) { return iv_add(a, iv_neg(b)); }
static IV iv_mul(const IV& a, const IV& b, int M) {
#if INJECT == 7
    // defect: only lo*lo and hi*hi (wrong when an interval is negative)
    return IV{floor_shr(imul(a.lo, b.lo), M), ceil_shr(imul(a.hi, b.hi), M)};
#endif
    Int p[4] = {imul(a.lo, b.lo), imul(a.lo, b.hi), imul(a.hi, b.lo), imul(a.hi, b.hi)};
    Int mn = p[0], mx = p[0];
    for (int i = 1; i < 4; i++) {
        if (icmp(p[i], mn) < 0) mn = p[i];
        if (icmp(p[i], mx) > 0) mx = p[i];
    }
    return IV{floor_shr(mn, M), ceil_shr(mx, M)};
}
static IV iv_div_pos(const IV& a, const IV& b, int M) {  // b > 0
    Int n[2] = {mk(a.lo.neg, shl(a.lo.m, M)), mk(a.hi.neg, shl(a.hi.m, M))};
    Int lo, hi;
    bool first = true;
    for (const Int& x : n)
        for (const Int* d : {&b.lo, &b.hi}) {
            Int l = div_dir(x, d->m, false), h = div_dir(x, d->m, true);
            if (first || icmp(l, lo) < 0) lo = l;
            if (first || icmp(h, hi) > 0) hi = h;
            first = false;
        }
    return IV{lo, hi};
}
static IV iv_div_small(const IV& a, uint32_t d) {  // a / d, d > 0
    bool ex;
    Mag ql = div_small(a.lo.m, d, &ex);
    if (!ex && a.lo.neg) ql = add(ql, ONE);
    Mag qh = div_small(a.hi.m, d, &ex);
    if (!ex && !a.hi.neg) qh = add(qh, ONE);
    return IV{mk(a.lo.neg, ql), mk(a.hi.neg, qh)};
}
static IV iv_shift_down(const IV& a, int s) { return IV{floor_shr(a.lo, s), ceil_shr(a.hi, s)}; }

// exact rational x = X * 10^p * 2^s (X integer) enclosed at scale 2^M
static IV enclose_scaled(const Int& X, int p, int s, int M) {
    if (p >= 0) {
        Int y = imul(X, mk(false, pow10(p)));
        return IV{floor_shr(y, -(s + M)), ceil_shr(y, -(s + M))};
    }
    // floor(X 2^(s+M) / 10^-p): shift first when s + M >= 0 (exact), else nested floors (valid for d > 0)
    Int lo = s + M >= 0 ? mk(X.neg, shl(X.m, s + M)) : floor_shr(X, -(s + M));
    Int hi = s + M >= 0 ? lo : ceil_shr(X, -(s + M));
    return IV{div10_dir(lo, -p, false), div10_dir(hi, -p, true)};
}

// ---------------------------------------------------------------------------
// e^-x for x in [xlo, xhi] >= 0 (given at scale 2^S), result at scale 2^M
// ---------------------------------------------------------------------------
static IV exp_neg(const Int& xlo, const Int& xhi, int S, int M) {
    if (bitlen(xlo.m) > S + 12) return IV{Int(), mk(false, ONE)};  // x >= 4096: e^-x < 2^-5909 <= 2^-M
    int k = std::max(0, bitlen(xhi.m) - S) + 8;
    int shift = M - S - k;
    Mag a_floor = shift >= 0 ? shl(xlo.m, shift) : shr(xlo.m, -shift);
    Mag a_ceil = shift >= 0 ? shl(xhi.m, shift) : shr_ceil(xhi.m, -shift);
    Mag lo, hi, unused;
    exp_taylor(a_ceil, true, M, lo, unused);   // the larger argument gives the lower end
    exp_taylor(a_floor, true, M, unused, hi);
    for (int i = 0; i < k; i++) {
        lo = shr(mul(lo, lo), M);
        hi = shr_ceil(mul(hi, hi), M);
    }
    return IV{mk(false, lo), mk(false, hi)};
}

// ---------------------------------------------------------------------------
// The model (parameters: the exact decimals of S2_ar2_pot.f90, typed separately from the reference)
// ---------------------------------------------------------------------------
struct ShortTerm {
    const char* alpha;
    int imin;
    std::vector<const char*> a;
};
struct Component {
    std::vector<ShortTerm> shorts;
    const char* eta;
    int kmin, kadd;
    std::vector<const char*> C;
    int ret_kind;  // 0: none, 1: BO C6 -> g + f - 1, 2: REL C4 -> f - 1
};
static const std::vector<Component>& model() {
    static const std::vector<Component> m = {
        {{{"6.92639712", -1, {"2.19578828e4", "6.77672149e4", "8.52129476e4", "9.53252754e4"}},
          {"2.34781022", -1, {"-2.16338828e4", "3.18311293e4", "-8.18603449e3", "8.37564742e2"}}},
         "3.65946625", 3, 1, {"64.2295222", "1503.45262", "49033", "1828012", "81913453", "4294913366"}, 1},
        {{{"1.66833595", 0, {"-3.55673715e0", "7.59367220e-1", "-4.19874548e-2"}},
          {"3.07137482", 0, {"-2.83560129e1", "1.64892143e1", "7.19542232e0"}}},
         "1.05249333", 2, 0, {"-9.43594504e-4", "1.76276088e-1", "3.99787449e-1"}, 2},
        {{{"1.64936036", 0, {"-1.2621862e-1", "1.176436e-2", "0"}},
          {"2.29848003", 0, {"0", "0", "6.921721e-2"}}},
         "3.91638946", 3, 0, {"-1.949525e-2", "-4.8877359e-1"}, 0},
    };
    return m;
}
static const std::vector<const char*> RET_A = {"3.064827731712776e-01", "4.843969950480238e-03",
                                               "7.793815409352866e-06", "1.031221966985517e-14",
                                               "4.204140311858030e-12"};
static const std::vector<const char*> RET_B = {"3.064827731712776e-01", "4.858660928580025e-03",
                                               "1.156839432134599e-05", "1.670845939899731e-08",
                                               "2.151070686307512e-17", "8.769598859882065e-15"};

// R = m * 2^e exactly (m > 0)
struct Dyadic {
    Mag m;
    int e;
};
static Mag mpow(const Mag& m, int n) {
    Mag r = ONE;
    for (int i = 0; i < n; i++) r = mul(r, m);
    return r;
}
// c * R^i at scale 2^M, any integer i (exact rational, rounded outward once)
static IV term(const Dec& c, const Dyadic& R, int i, int M) {
    if (is_zero(c.num.m)) return IV{};
    if (i >= 0) return enclose_scaled(imul(c.num, mk(false, mpow(R.m, i))), c.p, i * R.e, M);
    // c 10^p / (m^|i| 2^(|i| e)) * 2^M
    int n = -i, s = M - n * R.e;
    Int top = c.p >= 0 ? imul(c.num, mk(false, pow10(c.p))) : c.num;
    Int X = s >= 0 ? mk(top.neg, shl(top.m, s)) : top;
    Mag den = mpow(R.m, n);
    Int lo = div_dir(X, den, false), hi = div_dir(X, den, true);
    if (s < 0) { lo = floor_shr(lo, -s); hi = ceil_shr(hi, -s); }
    if (c.p < 0) { lo = div10_dir(lo, -c.p, false); hi = div10_dir(hi, -c.p, true); }
    return IV{lo, hi};
}
static Dec dec_mul_int(const Dec& c, int64_t k) {
    return Dec{imul(c.num, mk(k < 0, from_u64((uint64_t)(k < 0 ? -k : k)))), c.p};
}

struct Cache {  // per-precision constants that do not depend on R
    int M = -1;
    std::array<IV, 18> tailT, tailt;  // bounds of the Tang-Toennies tail for x >= 256
};

static void fill_cache(Cache& c, int M) {
    if (c.M == M) return;
    c.M = M;
    Int x256 = mk(false, shl(from_u64(256), M));
    IV e = exp_neg(x256, x256, M, M);
    Mag p = ONE;  // 256^n / n! as an upper bound at scale M: (e_hi * 256^n) / n!, ceil
    for (int n = 0; n < 18; n++) {
        if (n) p = mul(p, from_u64(256));
        Mag num = mul(e.hi.m, p);
        for (int i = 2; i <= n; i++) num = div_small_ceil(num, (uint32_t)i);
        c.tailt[n] = IV{Int(), mk(false, num)};
        c.tailT[n] = IV{Int(), mk(false, mul(num, from_u64((uint64_t)n + 1)))};
    }
}

// value (deriv = false) or dV/dR (deriv = true) at scale 2^M, summed over the components in `mask`
// (bit c = component c: BO, REL, QED). Each component is an exact-integer interval, so any split of the
// components and any order of adding them gives the same interval.
static IV evaluate_iv(const Dyadic& R, bool ret, bool deriv, int M, Cache& cache, int mask = 7) {
    fill_cache(cache, M);
    IV total{};
    const int S = M + 8;  // exponent arguments carried 8 bits finer
    for (size_t ci = 0; ci < model().size(); ci++) {
        if (!(mask >> ci & 1)) continue;
        const Component& comp = model()[ci];
        for (const ShortTerm& st : comp.shorts) {
            Dec alpha = dec(st.alpha);
            IV x = term(alpha, R, 1, S);
            IV E = exp_neg(x.lo, x.hi, S, M);
            IV poly{};
            for (size_t t = 0; t < st.a.size(); t++) {
                int i = st.imin + (int)t;
                Dec a = dec(st.a[t]);
                if (!deriv) {
                    poly = iv_add(poly, term(a, R, i, M));
                } else {  // d/dR [e^-aR P] = e^-aR (P' - a P)
                    if (i != 0) poly = iv_add(poly, term(dec_mul_int(a, i), R, i - 1, M));
                    Dec aa{imul(alpha.num, a.num), alpha.p + a.p};
                    poly = iv_sub(poly, term(aa, R, i, M));
                }
            }
            total = iv_add(total, iv_mul(E, poly, M));
        }
        Dec eta = dec(comp.eta);
        IV xS = term(eta, R, 1, S), x = iv_shift_down(xS, 8);
        bool far = icmp(xS.lo, mk(false, shl(from_u64(256), S))) >= 0;  // x >= 256: bounded tail
        IV E = far ? IV{} : exp_neg(xS.lo, xS.hi, S, M);
        IV sum = iv_exact(mk(false, shl(ONE, M))), piece = sum;  // sum_{i<=n} x^i/i!, last piece x^n/n!
        int n_done = 0;
        for (size_t t = 0; t < comp.C.size(); t++) {
            int k = comp.kmin + (int)t, n = 2 * k + comp.kadd;
#if INJECT == 11
            n -= 1;  // defect: Tang-Toennies order one too low
#endif
            if (!far)
                for (; n_done < n; n_done++) {
                    piece = iv_div_small(iv_mul(piece, x, M), (uint32_t)(n_done + 1));
                    sum = iv_add(sum, piece);
                }
            IV T = far ? cache.tailT[n] : iv_mul(E, sum, M);   // e^-x sum
            IV t_n = far ? cache.tailt[n] : iv_mul(E, piece, M);  // e^-x x^n / n!
#if INJECT == 8
            if (bitlen(xS.lo.m) > S + 6) { T = IV{}; t_n = IV{}; }  // defect: tail taken as 0 for x >= 64
#endif
            IV one = iv_exact(mk(false, shl(ONE, M)));
            IV D, dD = iv_mul(t_n, term(eta, R, 0, M), M);  // d f_n(eta R) / dR = eta e^-x x^n / n!
            bool kmin = t == 0;
            IV g{}, dg{};
            if (comp.ret_kind == 1 && kmin && ret) {
                const int G = M + 64;
                IV N = iv_exact(mk(false, shl(ONE, G))), Dn = N, dN{}, dDn{};
                for (size_t mm = 0; mm < RET_A.size(); mm++) {
                    N = iv_add(N, term(dec(RET_A[mm]), R, (int)mm + 1, G));
                    dN = iv_add(dN, term(dec_mul_int(dec(RET_A[mm]), (int64_t)mm + 1), R, (int)mm, G));
                }
                for (size_t mm = 0; mm < RET_B.size(); mm++) {
                    Dn = iv_add(Dn, term(dec(RET_B[mm]), R, (int)mm + 1, G));
                    dDn = iv_add(dDn, term(dec_mul_int(dec(RET_B[mm]), (int64_t)mm + 1), R, (int)mm, G));
                }
                g = iv_shift_down(iv_div_pos(N, Dn, G), G - M);
                IV num = iv_sub(iv_mul(dN, Dn, G), iv_mul(N, dDn, G));
                dg = iv_shift_down(iv_div_pos(num, iv_mul(Dn, Dn, G), G), G - M);
            }
#if INJECT == 6
            if (comp.ret_kind == 1 && kmin && ret) { g = one; dg = IV{}; }  // defect: BO retardation ignored
#endif
            if (comp.ret_kind == 1 && kmin && ret) {
                D = iv_sub(g, T);  // g + f - 1 = g - e^-x sum
                dD = iv_add(dD, dg);
            } else if (comp.ret_kind == 2 && kmin && ret) {
                D = iv_neg(T);     // f - 1
            } else {
                D = iv_sub(one, T);
            }
            Dec C = dec(comp.C[t]);
            if (!deriv) {
                total = iv_sub(total, iv_mul(D, term(C, R, -2 * k, M), M));
            } else {  // d/dR [-C D / R^2k] = -C D' / R^2k + 2k C D / R^(2k+1)
                total = iv_sub(total, iv_mul(dD, term(C, R, -2 * k, M), M));
#if INJECT != 5  // defect 5: the -2k D / R^(2k+1) term dropped
                total = iv_add(total, iv_mul(D, term(dec_mul_int(C, 2 * k), R, -2 * k - 1, M), M));
#endif
            }
        }
    }
    return total;
}

// ---------------------------------------------------------------------------
// Profiles, domain, rounding once
// ---------------------------------------------------------------------------
struct Profile {
    bool fx;
    int W, F;
};
struct Answer {
    std::string text;
};

static bool below_r_min(const Dyadic& R) {
    // R < 1.2 / 0.529177210903  <=>  m 2^e 529177210903 < 1200000000000
    Mag lhs = mul(R.m, from_u64(529177210903ull)), rhs = from_u64(1200000000000ull);
#if INJECT == 4
    // defect: the limit converted to binary64 and compared with <=. (With < this is NOT a defect on binary64
    // inputs: 1.2 / 0.529177210903 in binary64 rounds up to exactly the first input >= r_min.)
    double lim = 1.2 / 0.529177210903;
    return ldexp(strtod(to_dec(R.m).c_str(), nullptr), R.e) <= lim;
#endif
    if (R.e >= 0) lhs = shl(lhs, R.e);
    else rhs = shl(rhs, -R.e);
    return cmp(lhs, rhs) < 0;
}

// the rounded result of the enclosure end x (scale 2^M), or a halt
struct Rounded {
    bool halt;
    std::string raw;
    bool operator==(const Rounded& o) const { return halt == o.halt && raw == o.raw; }
};
static Rounded round_end(const Profile& p, const Int& x, int M) {
    if (p.fx) {
#if INJECT == 10
        Int q = floor_shr(x, M - p.F);  // defect: FX floor instead of nearest
#else
        Int q = round_shift(x, M - p.F);
#endif
        if (!fx_in_range(FX{p.W, p.F}, q)) return Rounded{true, ""};
        return Rounded{false, int_str(q)};
    }
    if (is_zero(x.m)) return Rounded{false, "0000000000000000"};
    try {
#if INJECT == 9
        int cut = std::max(0, bitlen(x.m) - 53);  // defect: binary64 rounding toward zero (truncation)
        uint64_t b = b64_round(x.neg ? 1 : 0, shr(x.m, cut), ONE, cut - M);
#else
        uint64_t b = b64_round(x.neg ? 1 : 0, x.m, ONE, -M);
#endif
        char buf[32];
        snprintf(buf, sizeof buf, "%016llx", (unsigned long long)b);
        return Rounded{false, buf};
    } catch (const Halt&) {
        return Rounded{true, ""};
    }
}

static std::string plain_binary64(const Dyadic& R, bool ret, bool deriv);

typedef IV (*Evaluator)(const Dyadic& R, bool ret, bool deriv, int M, Cache& cache);
static IV evaluate_all(const Dyadic& R, bool ret, bool deriv, int M, Cache& cache) {
    return evaluate_iv(R, ret, deriv, M, cache);
}

static std::string answer(char qty, bool ret, const Profile& p, const std::string& raw, Cache& cache,
                          Evaluator eval = evaluate_all) {
    Dyadic R;
    if (p.fx) {
        Int v = parse_int(raw);
        if (v.neg || is_zero(v.m)) return "domain physics_domain_exceeded";
        R = Dyadic{v.m, -p.F};
    } else {
        uint64_t b = strtoull(raw.c_str(), nullptr, 16);
        if (((b >> 52) & 0x7FF) == 0x7FF) return "refuse invalid_input";
        if ((b >> 63) || (b & ~SIGN) == 0) return "domain physics_domain_exceeded";
        Term t = decode(b);
        R = Dyadic{t.m, t.e};
    }
    // normalise m odd (cheaper powers), value unchanged
    while (!is_zero(R.m) && !odd(R.m)) { R.m = shr(R.m, 1); R.e++; }
    if (below_r_min(R)) return "domain physics_domain_exceeded";
    if (bitlen(R.m) + R.e > R_MAX_LOG2 + 1 ||
        (bitlen(R.m) + R.e == R_MAX_LOG2 + 1 && !(R.m.size() == 1 && R.m[0] == 1)))
        return "refuse beyond_native_range";
#if INJECT == 1
    if (!p.fx) return "ok " + plain_binary64(R, ret, qty == 'F') + " 53";
#endif
    for (int M = M_START; M <= M_CAP; M *= 2) {
#if INJECT == 2
        M = 64;  // defect: one modest precision, first answer taken
#endif
        IV v = eval(R, ret, qty == 'F', M, cache);
        if (qty == 'F') v = iv_neg(v);
        Rounded a = round_end(p, v.lo, M), b = round_end(p, v.hi, M);
#if INJECT == 2 || INJECT == 3
        b = a;  // defect 3: no refinement -- the lower end's rounding is accepted
#endif
        if (a == b) {
            if (a.halt) return "halt overflow";
            return "ok " + a.raw + " " + std::to_string(M);
        }
    }
    return "refuse undecided";
}

// the Fortran-like evaluation: every operation rounded in binary64 (fault injection 1 only)
static std::string plain_binary64(const Dyadic& R, bool ret, bool deriv) {
    double r = ldexp(strtod(to_dec(R.m).c_str(), nullptr), R.e), v = 0, dv = 0;
    for (const Component& comp : model()) {
        for (const ShortTerm& st : comp.shorts) {
            double al = strtod(st.alpha, nullptr), e = exp(-al * r), P = 0, dP = 0;
            for (size_t t = 0; t < st.a.size(); t++) {
                int i = st.imin + (int)t;
                double a = strtod(st.a[t], nullptr);
                P += a * pow(r, i);
                dP += i * a * pow(r, i - 1);
            }
            v += e * P;
            dv += e * (dP - al * P);
        }
        double eta = strtod(comp.eta, nullptr), x = eta * r;
        for (size_t t = 0; t < comp.C.size(); t++) {
            int k = comp.kmin + (int)t, n = 2 * k + comp.kadd;
            double s = 0, piece = 1;
            for (int i = 0; i <= n; i++) { if (i) piece *= x / i; s += piece; }
            double T = exp(-x) * s, tn = exp(-x) * piece, D = 1 - T, dD = eta * tn;
            if (comp.ret_kind == 1 && t == 0 && ret) {
                double N = 1, Dn = 1, dN = 0, dDn = 0;
                for (size_t m = 0; m < RET_A.size(); m++) { N += strtod(RET_A[m], nullptr) * pow(r, m + 1); dN += (m + 1) * strtod(RET_A[m], nullptr) * pow(r, m); }
                for (size_t m = 0; m < RET_B.size(); m++) { Dn += strtod(RET_B[m], nullptr) * pow(r, m + 1); dDn += (m + 1) * strtod(RET_B[m], nullptr) * pow(r, m); }
                D = N / Dn - T;
                dD += (dN * Dn - N * dDn) / (Dn * Dn);
            } else if (comp.ret_kind == 2 && t == 0 && ret) {
                D = -T;
            }
            double C = strtod(comp.C[t], nullptr);
            v -= C * D / pow(r, 2 * k);
            dv -= C * (dD / pow(r, 2 * k) - 2 * k * D / pow(r, 2 * k + 1));
        }
    }
    char buf[32];
    snprintf(buf, sizeof buf, "%016llx", (unsigned long long)bits_of(deriv ? -dv : v));
    return buf;
}

// ---------------------------------------------------------------------------
// Batch I/O shared by B0 and B1
// ---------------------------------------------------------------------------
struct Query {
    char qty;
    bool ret;
    Profile p;
    std::string raw;
};
static std::vector<Query> read_queries(const char* path) {
    std::ifstream in(path);
    std::vector<Query> qs;
    std::string line;
    while (std::getline(in, line)) {
        std::istringstream ss(line);
        std::string q, r, prof, raw;
        if (!(ss >> q >> r >> prof >> raw)) continue;
        Profile p{false, 64, 0};
        if (prof.rfind("FX:", 0) == 0) {
            p.fx = true;
            sscanf(prof.c_str() + 3, "%d:%d", &p.W, &p.F);
        }
        qs.push_back(Query{q[0], r == "1", p, raw});
    }
    return qs;
}
static void write_answers(const char* path, const std::vector<std::string>& ans) {
    std::string out;
    for (const std::string& a : ans) out += a + "\n";
    write_file(path, out);
}

}  // namespace ar2
