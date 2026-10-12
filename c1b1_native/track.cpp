// C3a native track (survey_only): one fixed-point Chin 4A / KDK track of the M10 brush pen, integers only.
// Plan: docs/active/C1B1_C3_NATIVE_PEN_PLAN_V0.md. Python reference: c1b1_t7.ladder.FxTrackX with
// c1b1_t7.lang_fx2.LangForceFX2 and the one-shot sweep (c1b1_native/reference.py). Integer types only (checked by a test).
//
// Protocol (stdin tokens, stdout one line per command; integers in hex, '-' for negative):
//   init fp fm j method(kdk|chin) h0 W  qr0 qr1 pr0 pr1  mu_d_num mu_d_den  mu_k_man mu_k_exp  ln2q
//        nterms {name imin kmin kadd na a.. nal al.. eta nc c..}*  nA A..  nB B..   -> ok
//   to_exit MAX | to N                                                            -> ok STATE | err ...
//   jet R            -> ok v d dd   (2^-P)
//   kickval cn cd g  -> ok y0 y1    (value before rounding, 2^-(fm+128) units)
//   calc OP args...  -> ok result   (arithmetic self-test, no init needed)
//   quit
// STATE = tick exit_tick substeps turns qr0 qr1 pr0 pr1 kicks cpu_ns
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <time.h>

#ifndef INJECT
#define INJECT 0      // fault injection for tests: 1 no gradient term, 2 kick rounds down, 3 ln2 bit 72 flipped,
#endif                // 4 drift truncates, 5 turn count reversed, 6 exp guard 8 bits

typedef unsigned __int128 u128;
typedef __int128 i128;
static const int NL = 28;                 // limb capacity: 1,792 bits

struct Z { uint64_t d[NL]; int n; bool neg; };

[[noreturn]] static void fail(const char* m) { throw std::runtime_error(m); }

static inline Z zero() { Z z; z.n = 0; z.neg = false; return z; }
static inline void trim(Z& a) { while (a.n > 0 && a.d[a.n - 1] == 0) a.n--; if (a.n == 0) a.neg = false; }
static Z from_i64(long long v) {
    Z z = zero();
    if (v) { z.neg = v < 0; z.d[0] = v < 0 ? (uint64_t)(-(v + 1)) + 1 : (uint64_t)v; z.n = 1; }
    return z;
}
static inline Z one() { return from_i64(1); }
static int bitlen(const Z& a) { return a.n ? 64 * (a.n - 1) + (64 - __builtin_clzll(a.d[a.n - 1])) : 0; }
static int mag_cmp(const Z& a, const Z& b) {
    if (a.n != b.n) return a.n < b.n ? -1 : 1;
    for (int i = a.n - 1; i >= 0; i--) if (a.d[i] != b.d[i]) return a.d[i] < b.d[i] ? -1 : 1;
    return 0;
}
static int cmp(const Z& a, const Z& b) {
    if (a.neg != b.neg) return a.neg ? -1 : 1;
    int c = mag_cmp(a, b);
    return a.neg ? -c : c;
}
static Z mag_add(const Z& a, const Z& b) {
    const Z& x = a.n >= b.n ? a : b; const Z& y = a.n >= b.n ? b : a;
    Z r = zero(); u128 c = 0;
    for (int i = 0; i < x.n; i++) { c += (u128)x.d[i] + (i < y.n ? y.d[i] : 0); r.d[i] = (uint64_t)c; c >>= 64; }
    r.n = x.n;
    if (c) { if (r.n >= NL) fail("overflow add"); r.d[r.n++] = (uint64_t)c; }
    return r;
}
static Z mag_sub(const Z& a, const Z& b) {           // |a| >= |b|
    Z r = zero(); uint64_t br = 0;
    for (int i = 0; i < a.n; i++) {
        uint64_t bi = i < b.n ? b.d[i] : 0;
        u128 t = (u128)a.d[i] - bi - br;
        r.d[i] = (uint64_t)t; br = (uint64_t)(t >> 64) ? 1 : 0;
    }
    r.n = a.n; trim(r); return r;
}
static Z add(const Z& a, const Z& b) {
    Z r;
    if (a.neg == b.neg) { r = mag_add(a, b); r.neg = a.neg; }
    else {
        int c = mag_cmp(a, b);
        if (c == 0) return zero();
        if (c > 0) { r = mag_sub(a, b); r.neg = a.neg; } else { r = mag_sub(b, a); r.neg = b.neg; }
    }
    trim(r); return r;
}
static inline Z neg(Z a) { if (a.n) a.neg = !a.neg; return a; }
static inline Z absz(Z a) { a.neg = false; return a; }
static inline Z sub(const Z& a, const Z& b) { return add(a, neg(b)); }
static Z mul(const Z& a, const Z& b) {
    if (!a.n || !b.n) return zero();
    if (a.n + b.n > NL) fail("overflow mul");
    Z r = zero(); r.n = a.n + b.n;
    for (int i = 0; i < r.n; i++) r.d[i] = 0;
    for (int i = 0; i < a.n; i++) {
        u128 c = 0;
        for (int j = 0; j < b.n; j++) { c += (u128)a.d[i] * b.d[j] + r.d[i + j]; r.d[i + j] = (uint64_t)c; c >>= 64; }
        r.d[i + b.n] = (uint64_t)c;
    }
    r.neg = a.neg != b.neg; trim(r); return r;
}
static Z shl(const Z& a, int s) {                    // magnitude shift, sign kept (exact)
    if (s < 0) fail("shl negative");
    if (!a.n || s == 0) return a;
    int w = s >> 6, b = s & 63, n = a.n + w + 1;
    if (n > NL + 1) fail("overflow shl");
    uint64_t t[NL + 2];
    for (int i = 0; i < n; i++) t[i] = 0;
    for (int i = 0; i < a.n; i++) {
        t[i + w] |= b ? (a.d[i] << b) : a.d[i];
        if (b) t[i + w + 1] |= a.d[i] >> (64 - b);
    }
    while (n > 0 && t[n - 1] == 0) n--;
    if (n > NL) fail("overflow shl");
    Z r = zero(); r.n = n; std::memcpy(r.d, t, 8 * n); r.neg = a.neg; return r;
}
static Z mag_shr(const Z& a, int s, bool* lost) {    // truncating magnitude shift
    *lost = false; Z r = zero();
    if (!a.n) return r;
    int w = s >> 6, b = s & 63;
    if (w >= a.n) { *lost = true; return r; }
    for (int i = 0; i < w; i++) if (a.d[i]) *lost = true;
    if (b && (a.d[w] & ((1ULL << b) - 1))) *lost = true;
    int n = a.n - w;
    for (int i = 0; i < n; i++) {
        if (!b) { r.d[i] = a.d[i + w]; continue; }
        uint64_t lo = a.d[i + w] >> b, hi = (i + w + 1 < a.n) ? a.d[i + w + 1] << (64 - b) : 0;
        r.d[i] = lo | hi;
    }
    r.n = n; trim(r); return r;
}
static Z shr(const Z& a, int s) {                    // floor(a / 2^s), as Python >>
    if (s < 0) fail("shr negative");
    bool lost; Z r = mag_shr(a, s, &lost);
    if (a.neg) { if (lost) r = mag_add(r, one()); r.neg = r.n > 0; }
    return r;
}
static void mag_divmod(const Z& u, const Z& v, Z& q, Z& r) {   // magnitudes, Knuth D (64-bit limbs)
    if (!v.n) fail("division by zero");
    q = zero(); r = zero();
    if (mag_cmp(u, v) < 0) { r = absz(u); return; }
    int m = u.n, n = v.n;
    if (n == 1) {
        u128 rem = 0;
        for (int i = m - 1; i >= 0; i--) { u128 cur = (rem << 64) | u.d[i]; q.d[i] = (uint64_t)(cur / v.d[0]); rem = cur % v.d[0]; }
        q.n = m; trim(q); r.d[0] = (uint64_t)rem; r.n = 1; trim(r); return;
    }
    int s = __builtin_clzll(v.d[n - 1]);
    uint64_t vn[NL], un[NL + 1];
    for (int i = n - 1; i > 0; i--) vn[i] = (v.d[i] << s) | (s ? v.d[i - 1] >> (64 - s) : 0);
    vn[0] = v.d[0] << s;
    un[m] = s ? u.d[m - 1] >> (64 - s) : 0;
    for (int i = m - 1; i > 0; i--) un[i] = (u.d[i] << s) | (s ? u.d[i - 1] >> (64 - s) : 0);
    un[0] = u.d[0] << s;
    for (int j = m - n; j >= 0; j--) {
        u128 num = ((u128)un[j + n] << 64) | un[j + n - 1];
        u128 qhat = num / vn[n - 1], rhat = num % vn[n - 1];
        while ((qhat >> 64) || qhat * vn[n - 2] > ((rhat << 64) | un[j + n - 2])) {
            qhat--; rhat += vn[n - 1];
            if (rhat >> 64) break;
        }
        i128 k = 0, t;
        for (int i = 0; i < n; i++) {
            u128 p = qhat * vn[i];
            t = (i128)un[i + j] - k - (i128)(uint64_t)p;
            un[i + j] = (uint64_t)t;
            k = (i128)(uint64_t)(p >> 64) - (t >> 64);
        }
        t = (i128)un[j + n] - k; un[j + n] = (uint64_t)t;
        q.d[j] = (uint64_t)qhat;
        if (t < 0) {
            q.d[j]--;
            u128 c = 0;
            for (int i = 0; i < n; i++) { c += (u128)un[i + j] + vn[i]; un[i + j] = (uint64_t)c; c >>= 64; }
            un[j + n] += (uint64_t)c;
        }
    }
    q.n = m - n + 1; trim(q);
    for (int i = 0; i < n - 1; i++) r.d[i] = (un[i] >> s) | (s ? un[i + 1] << (64 - s) : 0);
    r.d[n - 1] = un[n - 1] >> s; r.n = n; trim(r);
}
static void divmod_floor(const Z& a, const Z& b, Z& q, Z& r) {  // Python divmod
    Z qq, rr; mag_divmod(a, b, qq, rr);
    bool sq = a.neg != b.neg;
    if (!sq) { q = qq; q.neg = false; r = rr; r.neg = rr.n ? a.neg : false; }
    else if (rr.n) { q = mag_add(qq, one()); q.neg = true; r = mag_sub(absz(b), rr); r.neg = b.neg && r.n; }
    else { q = qq; q.neg = q.n > 0; r = zero(); }
    trim(q); trim(r);
}
static Z floordiv(const Z& a, const Z& b) { Z q, r; divmod_floor(a, b, q, r); return q; }
static Z isqrt(const Z& n) {                         // floor(sqrt(n)), as math.isqrt
    if (n.neg) fail("isqrt of negative");
    if (!n.n) return zero();
    Z x = shl(one(), (bitlen(n) + 1) / 2 + 1);
    while (true) {
        Z y = shr(add(x, floordiv(n, x)), 1);
        if (cmp(y, x) >= 0) return x;
        x = y;
    }
}
static Z half_even(const Z& num, const Z& den) {     // c1b1_method_bench.fixedpoint._half_even
    Z q, r; divmod_floor(num, den, q, r);
    int c = cmp(shl(r, 1), den);
    if (c > 0 || (c == 0 && q.n && (q.d[0] & 1))) q = add(q, one());
    return q;
}
static Z parse_hex(const std::string& s) {
    Z z = zero(); size_t i = 0; bool ng = false;
    if (!s.empty() && s[0] == '-') { ng = true; i = 1; }
    std::string h = s.substr(i);
    if (h.empty()) fail("bad hex");
    int nd = (int)h.size(), n = (nd + 15) / 16;
    if (n > NL) fail("overflow parse");
    for (int k = 0; k < n; k++) z.d[k] = 0;
    for (int k = 0; k < nd; k++) {
        char c = h[nd - 1 - k]; uint64_t v;
        if (c >= '0' && c <= '9') v = c - '0'; else if (c >= 'a' && c <= 'f') v = c - 'a' + 10; else fail("bad hex digit");
        z.d[k / 16] |= v << (4 * (k % 16));
    }
    z.n = n; z.neg = ng; trim(z); return z;
}
static std::string to_hex(const Z& z) {
    if (!z.n) return "0";
    char buf[20]; std::snprintf(buf, sizeof buf, "%llx", (unsigned long long)z.d[z.n - 1]);
    std::string s = buf;
    for (int i = z.n - 2; i >= 0; i--) { std::snprintf(buf, sizeof buf, "%016llx", (unsigned long long)z.d[i]); s += buf; }
    return (z.neg ? "-" : "") + s;
}

// ---------------------------------------------------------------- track state
static int FP, FM, JLEV, P, W; static bool CHIN; static long long H0;
static Z QR[2], PR[2], MU_D_NUM, MU_D_DEN, MU_K_MAN, LN2Q; static long long MU_K_EXP;
static long long TICK = 0, SUBSTEPS = 0, EXIT_TICK = -1, TURNS = 0, KICKS = 0;
static bool JVALID = false; static Z JC[2];
struct Term { std::string name; int imin, kmin, kadd; std::vector<Z> a, alpha, C; Z eta; };
static std::vector<Term> TERMS; static std::vector<Z> AC, BC;

// floor(exp(-X / 2^p) 2^p), X >= 0; ln2q = floor(ln2 2^(p+64))
static Z exp_neg(const Z& X, int p, const Z& ln2q) {
    const int G = INJECT == 6 ? 8 : 64, Q = p + G;
    Z ln2 = shr(ln2q, 64 - G);
#if INJECT == 3
    ln2 = add(ln2, shl(one(), 72 - (64 - G)));
#endif
    Z k, rem; divmod_floor(shl(X, G), ln2, k, rem);   // rem in [0, ln2) on 2^-Q
    if (k.n > 1 || (k.n && k.d[0] > (uint64_t)(Q + 4))) return zero();
    long long kk = k.n ? (long long)k.d[0] : 0;
    const int S = 8;
    Z y = shr(rem, S), oneq = shl(one(), Q), t = oneq, sum = oneq;
    for (int n = 1; n < 400; n++) {
        t = floordiv(shr(mul(t, y), Q), from_i64(n));
        if (!t.n) break;
        sum = (n & 1) ? sub(sum, t) : add(sum, t);
    }
    for (int i = 0; i < S; i++) sum = shr(mul(sum, sum), Q);
    return shr(sum, (int)kk + G);
}

struct Jet { Z v, d, dd; };
static Jet jet(const Z& R) {                         // c1b1_t7.lang_fx2.LangForceFX2.jet, integers on 2^-P
    Z ONE = shl(one(), P), IR = floordiv(shl(one(), 2 * P), R);
    Z pwp[7], pwn[19];
    pwp[0] = ONE; pwp[1] = R; pwn[0] = ONE; pwn[1] = IR;
    for (int m = 2; m <= 6; m++) pwp[m] = shr(mul(pwp[m - 1], R), P);
    for (int m = 2; m <= 18; m++) pwn[m] = shr(mul(pwn[m - 1], IR), P);
    auto pw = [&](int m) -> const Z& {
        if (m >= 0) { if (m > 6) fail("power range"); return pwp[m]; }
        if (-m > 18) fail("power range"); return pwn[-m];
    };
    Z v = zero(), d = zero(), dd = zero();
    for (const Term& T : TERMS) {
        int count = (int)T.a.size() / 2;
        for (size_t j = 0; j < T.alpha.size(); j++) {
            const Z& al = T.alpha[j];
            Z e = exp_neg(shr(mul(al, R), P), P, LN2Q);
            Z Pv = zero(), P1 = zero(), P2 = zero();
            for (int i = 0; i < count; i++) {
                int m = T.imin + i; const Z& c = T.a[j * count + i];
                Pv = add(Pv, shr(mul(c, pw(m)), P));
                if (m) {
                    P1 = add(P1, shr(mul(mul(c, from_i64(m)), pw(m - 1)), P));
                    if (m != 1) P2 = add(P2, shr(mul(mul(c, from_i64((long long)m * (m - 1))), pw(m - 2)), P));
                }
            }
            Z alP = shr(mul(al, Pv), P), alP1 = shr(mul(al, P1), P);
            v = add(v, shr(mul(e, Pv), P));
            d = add(d, shr(mul(e, sub(P1, alP)), P));
            dd = add(dd, shr(mul(e, add(sub(P2, shl(alP1, 1)), shr(mul(al, alP), P))), P));
        }
        const Z& eta = T.eta;
        Z x = shr(mul(eta, R), P), exn = exp_neg(x, P, LN2Q);
        int nmax = 2 * (T.kmin + (int)T.C.size() - 1) + T.kadd;
        std::vector<Z> terms(nmax + 1), sums(nmax + 1);
        terms[0] = ONE; sums[0] = ONE;
        for (int m = 1; m <= nmax; m++) { terms[m] = floordiv(shr(mul(terms[m - 1], x), P), from_i64(m)); sums[m] = add(sums[m - 1], terms[m]); }
        Z eta2 = shr(mul(eta, eta), P);
        for (size_t i = 0; i < T.C.size(); i++) {
            int k = T.kmin + (int)i, n = 2 * k + T.kadd; const Z& coef = T.C[i];
            Z f = sub(ONE, shr(mul(exn, sums[n]), P));
            Z f1 = shr(mul(eta, shr(mul(exn, terms[n]), P)), P);
            Z f2 = shr(mul(eta2, shr(mul(exn, sub(terms[n - 1], terms[n])), P)), P);
            if (i == 0 && T.name == "BO") {
                Z N = ONE, N1 = zero(), N2 = zero(), D = ONE, D1 = zero(), D2 = zero();
                for (size_t jj = 0; jj < AC.size(); jj++) {
                    long long q = (long long)jj;
                    N = add(N, shr(mul(AC[jj], pw((int)q + 1)), P));
                    N1 = add(N1, shr(mul(mul(AC[jj], from_i64(q + 1)), pw((int)q)), P));
                    if (jj) N2 = add(N2, shr(mul(mul(AC[jj], from_i64((q + 1) * q)), pw((int)q - 1)), P));
                }
                for (size_t jj = 0; jj < BC.size(); jj++) {
                    long long q = (long long)jj;
                    D = add(D, shr(mul(BC[jj], pw((int)q + 1)), P));
                    D1 = add(D1, shr(mul(mul(BC[jj], from_i64(q + 1)), pw((int)q)), P));
                    if (jj) D2 = add(D2, shr(mul(mul(BC[jj], from_i64((q + 1) * q)), pw((int)q - 1)), P));
                }
                Z DD = shr(mul(D, D), P);
                Z Wn = sub(shr(mul(N1, D), P), shr(mul(N, D1), P));
                f = add(f, sub(floordiv(shl(N, P), D), ONE));
                f1 = add(f1, floordiv(shl(Wn, P), DD));
                f2 = add(f2, sub(floordiv(shl(sub(shr(mul(N2, D), P), shr(mul(N, D2), P)), P), DD),
                                 floordiv(shl(shl(shr(mul(D1, Wn), P), 1), P), shr(mul(DD, D), P))));
            }
            if (i == 0 && T.name == "REL") f = sub(f, ONE);
            Z g = pw(-2 * k), g1 = mul(from_i64(-2 * k), pw(-2 * k - 1)),
              g2 = mul(from_i64((long long)2 * k * (2 * k + 1)), pw(-2 * k - 2));
            Z fg = shr(mul(f, g), P), f1g = shr(mul(f1, g), P);
            v = sub(v, shr(mul(coef, fg), P));
            d = sub(d, shr(mul(coef, add(f1g, shr(mul(f, g1), P))), P));
            dd = sub(dd, shr(mul(coef, add(add(shr(mul(f2, g), P), shl(shr(mul(f1, g1), P), 1)), shr(mul(f, g2), P))), P));
        }
    }
    return Jet{v, d, dd};
}

static Z TEN30;
// c (2^-P): coef (-V'/r + h^2 V' V'' / (24 mu_k r)), h = H0 / 2^JLEV
static Z kick_c(long long cn, long long cd, bool grad) {
    Z S = add(mul(QR[0], QR[0]), mul(QR[1], QR[1]));
    if (P <= FP) fail("P <= fp");
    Z R = isqrt(shl(S, 2 * (P - FP)));
    Jet t = jet(R);
    KICKS++;
    Z c = neg(floordiv(shl(t.d, P), R));
#if INJECT != 1
    if (grad) {
        Z g = mul(floordiv(mul(t.d, t.dd), R), from_i64(H0 * H0));
        Z den = mul(mul(shl(one(), 2 * JLEV), from_i64(24)), MU_K_MAN);
        if (MU_K_EXP < 0) g = shl(g, (int)-MU_K_EXP); else den = shl(den, (int)MU_K_EXP);
        c = add(c, floordiv(g, den));
    }
#else
    (void)grad;
#endif
    return floordiv(mul(c, from_i64(cn)), from_i64(cd));
}
static void kick(long long cn, long long cd, bool grad, Z out[2]) {   // round(c q_k 2^fm), 1e-30 tie guard
    Z c = kick_c(cn, cd, grad);
    int s = P + FP - FM;
    if (s < 2) fail("bad scale");
    Z unit = shl(one(), s), half = shl(one(), s - 1);
    for (int k = 0; k < 2; k++) {
        Z y = mul(c, QR[k]), q = shr(y, s), frac = sub(y, shl(q, s));
        Z dist = absz(sub(frac, half));
        if (cmp(mul(dist, TEN30), unit) < 0) fail("refuse: impulse within 1e-30 of a rounding tie");
#if INJECT == 2
        out[k] = q;
#else
        out[k] = cmp(frac, half) > 0 ? add(q, one()) : q;
#endif
    }
}
static void drift(long long dn, long long dd) {     // q += 2 half_even(p d 2^fp / (2^fm 2 mu))
    for (int k = 0; k < 2; k++) {
        Z num = shl(mul(mul(PR[k], from_i64(dn)), MU_D_DEN), FP);
        Z den = shl(mul(from_i64(dd), MU_D_NUM), FM + 1);
#if INJECT == 4
        Z q, r; mag_divmod(num, den, q, r); if (num.neg) q.neg = q.n > 0; QR[k] = add(QR[k], shl(q, 1));
#else
        QR[k] = add(QR[k], shl(half_even(num, den), 1));
#endif
    }
}
static void substep() {
    long long hd = 1LL << JLEV;
    Z J[2];
    if (CHIN) {
        if (!JVALID) kick(H0, 6 * hd, false, JC);
        PR[0] = add(PR[0], JC[0]); PR[1] = add(PR[1], JC[1]);
        drift(H0, 2 * hd);
        kick(2 * H0, 3 * hd, true, J);
        PR[0] = add(PR[0], J[0]); PR[1] = add(PR[1], J[1]);
        drift(H0, 2 * hd);
        kick(H0, 6 * hd, false, JC); JVALID = true;
        PR[0] = add(PR[0], JC[0]); PR[1] = add(PR[1], JC[1]);
    } else {
        if (!JVALID) kick(H0, 2 * hd, false, JC);
        PR[0] = add(PR[0], JC[0]); PR[1] = add(PR[1], JC[1]);
        drift(H0, hd);
        kick(H0, 2 * hd, false, JC); JVALID = true;
        PR[0] = add(PR[0], JC[0]); PR[1] = add(PR[1], JC[1]);
    }
}
static void advance_tick() {
    long long sub_n = 1LL << JLEV;
    for (long long i = 0; i < sub_n; i++) {
        bool x0n = QR[0].neg, y0n = QR[1].neg;
        substep();
        bool x1n = QR[0].neg, y1n = QR[1].neg;
        if (x0n && x1n) {                            // crossing of the negative x axis (atan2 branch cut)
            long long dt = 0;
            if (!y0n && y1n) dt = 1; else if (y0n && !y1n) dt = -1;
#if INJECT == 5
            dt = -dt;
#endif
            TURNS += dt;
        }
    }
    SUBSTEPS += sub_n; TICK++;
}
// 1 exit, 0 not yet; refuses inside the band where Python's 60-digit r() / pr() could decide differently
static int exit_check(const Z q[2], const Z p[2], int fp) {
    Z S = add(mul(q[0], q[0]), mul(q[1], q[1])), T = shl(from_i64(400), 2 * fp);
    Z diff = sub(S, T);
    if (cmp(absz(diff), shr(S, 190)) < 0) fail("refuse: radius within 2^-190 of 20");
    if (diff.neg) return 0;
    Z dot = add(mul(q[0], p[0]), mul(q[1], p[1]));
    Z mag = mul(add(absz(q[0]), absz(q[1])), add(absz(p[0]), absz(p[1])));
    if (cmp(absz(dot), shr(mag, 190)) < 0) fail("refuse: radial momentum within 2^-190 of zero");
    return dot.neg || !dot.n ? 0 : 1;
}
static long long cpu_ns() {
    struct timespec ts; clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}
static void print_state() {
    std::cout << "ok " << TICK << " " << EXIT_TICK << " " << SUBSTEPS << " " << TURNS << " " << to_hex(QR[0]) << " "
              << to_hex(QR[1]) << " " << to_hex(PR[0]) << " " << to_hex(PR[1]) << " " << KICKS << " " << cpu_ns() << "\n";
}
static std::string tok() { std::string s; if (!(std::cin >> s)) fail("eof"); return s; }
static long long tok_ll() { return std::stoll(tok()); }
static Z tok_z() { return parse_hex(tok()); }

static void calc() {
    std::string op = tok();
    if (op == "add") { Z a = tok_z(), b = tok_z(); std::cout << "ok " << to_hex(add(a, b)) << "\n"; }
    else if (op == "sub") { Z a = tok_z(), b = tok_z(); std::cout << "ok " << to_hex(sub(a, b)) << "\n"; }
    else if (op == "mul") { Z a = tok_z(), b = tok_z(); std::cout << "ok " << to_hex(mul(a, b)) << "\n"; }
    else if (op == "divmod") { Z a = tok_z(), b = tok_z(), q, r; divmod_floor(a, b, q, r); std::cout << "ok " << to_hex(q) << " " << to_hex(r) << "\n"; }
    else if (op == "shl") { Z a = tok_z(); int s = (int)tok_ll(); std::cout << "ok " << to_hex(shl(a, s)) << "\n"; }
    else if (op == "shr") { Z a = tok_z(); int s = (int)tok_ll(); std::cout << "ok " << to_hex(shr(a, s)) << "\n"; }
    else if (op == "isqrt") { Z a = tok_z(); std::cout << "ok " << to_hex(isqrt(a)) << "\n"; }
    else if (op == "halfeven") { Z a = tok_z(), b = tok_z(); std::cout << "ok " << to_hex(half_even(a, b)) << "\n"; }
    else if (op == "expneg") { Z x = tok_z(); int p = (int)tok_ll(); Z l = tok_z(); std::cout << "ok " << to_hex(exp_neg(x, p, l)) << "\n"; }
    else if (op == "exitcheck") { Z q[2], pp[2]; q[0] = tok_z(); q[1] = tok_z(); pp[0] = tok_z(); pp[1] = tok_z(); int fp = (int)tok_ll(); std::cout << "ok " << exit_check(q, pp, fp) << "\n"; }
    else if (op == "roundguard") {          // round(y / 2^s) with the kick tie guard
        Z y = tok_z(); int s = (int)tok_ll();
        Z unit = shl(one(), s), half = shl(one(), s - 1), q = shr(y, s), frac = sub(y, shl(q, s));
        if (cmp(mul(absz(sub(frac, half)), TEN30), unit) < 0) fail("refuse: tie");
        std::cout << "ok " << to_hex(cmp(frac, half) > 0 ? add(q, one()) : q) << "\n";
    }
    else fail("unknown calc op");
}
static void init() {
    FP = (int)tok_ll(); FM = (int)tok_ll(); JLEV = (int)tok_ll();
    std::string m = tok(); if (m != "chin" && m != "kdk") fail("method"); CHIN = m == "chin";
    H0 = tok_ll(); W = (int)tok_ll(); P = W + 96;
    QR[0] = tok_z(); QR[1] = tok_z(); PR[0] = tok_z(); PR[1] = tok_z();
    MU_D_NUM = tok_z(); MU_D_DEN = tok_z(); MU_K_MAN = tok_z(); MU_K_EXP = tok_ll(); LN2Q = tok_z();
    if (MU_D_NUM.neg || !MU_D_NUM.n || MU_D_DEN.neg || !MU_D_DEN.n || MU_K_MAN.neg || !MU_K_MAN.n) fail("mu");
    int nt = (int)tok_ll(); TERMS.clear();
    for (int i = 0; i < nt; i++) {
        Term T; T.name = tok(); T.imin = (int)tok_ll(); T.kmin = (int)tok_ll(); T.kadd = (int)tok_ll();
        int na = (int)tok_ll(); for (int k = 0; k < na; k++) T.a.push_back(tok_z());
        int nal = (int)tok_ll(); for (int k = 0; k < nal; k++) T.alpha.push_back(tok_z());
        T.eta = tok_z();
        int nc = (int)tok_ll(); for (int k = 0; k < nc; k++) T.C.push_back(tok_z());
        TERMS.push_back(T);
    }
    int nA = (int)tok_ll(); AC.clear(); for (int k = 0; k < nA; k++) AC.push_back(tok_z());
    int nB = (int)tok_ll(); BC.clear(); for (int k = 0; k < nB; k++) BC.push_back(tok_z());
    if (tok() != "end") fail("init end");
    TICK = SUBSTEPS = TURNS = KICKS = 0; EXIT_TICK = -1; JVALID = false;
    print_state();
}
int main() {
    std::ios::sync_with_stdio(false);
    TEN30 = from_i64(1);
    for (int i = 0; i < 30; i++) TEN30 = mul(TEN30, from_i64(10));
    std::string cmd;
    while (std::cin >> cmd) {
        try {
            if (cmd == "quit") break;
            else if (cmd == "calc") calc();
            else if (cmd == "init") init();
            else if (cmd == "to_exit") {
                long long mx = tok_ll();
                while (EXIT_TICK < 0) {
                    advance_tick();
                    if (exit_check(QR, PR, FP)) EXIT_TICK = TICK;
                    else if (TICK >= mx) fail("no exit");
                }
                print_state();
            }
            else if (cmd == "to") { long long n = tok_ll(); while (TICK < n) advance_tick(); print_state(); }
            else if (cmd == "jet") { Z R = tok_z(); Jet t = jet(R); std::cout << "ok " << to_hex(t.v) << " " << to_hex(t.d) << " " << to_hex(t.dd) << "\n"; }
            else if (cmd == "kickval") {
                long long cn = tok_ll(), cd = tok_ll(); bool g = tok_ll() != 0;
                Z c = kick_c(cn, cd, g); int s = P + FP - FM - 128;
                std::cout << "ok " << to_hex(shr(mul(c, QR[0]), s)) << " " << to_hex(shr(mul(c, QR[1]), s)) << "\n";
            }
            else fail("unknown command");
        } catch (const std::exception& e) {
            std::cout << "err " << e.what() << "\n";
        }
        std::cout.flush();
    }
    return 0;
}
