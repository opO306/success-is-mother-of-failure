// Shared arithmetic core of the native A-Numeric executors (B0 serial, B1 parallel).
//
// docs/current/A_NUMERIC_EXECUTION_STACK_V1.md section 4. Judged against the VM;
// never calls it. Same meaning, written separately:
//   * binary64 ADD SUB MUL DIV SQRT use the hardware (correctly rounded under
//     /fp:strict on x64 SSE2) and turn a non-finite result into a halt;
//   * SUM, DOT and CONST are EXACT accumulations with ONE rounding on a small
//     arbitrary-precision integer type -- never a float reduction;
//   * FX(W, F) is done entirely on exact integers.
// The including file defines accumulate() and main().
//
// Input (one program per P...E block):
//   P B64 | P FX W F
//   I name raw            (B64: 16 hex digits, FX: decimal integer)
//   X OP dst args...      (CONST dst num den; SUM dst k a1..ak; DOT dst k x1..xk y1..yk; CMP - a b)
//   E
// Output per program:
//   R / G name value / B pc result hexM e (margin = M * 2^e) / H pc reason | H - / E
//
// INJECT=n compiles a deliberate defect (fault injection, tests only).
#pragma once
#ifndef INJECT
#define INJECT 0
#endif

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
#if INJECT == 7
#include <pmmintrin.h>
#include <xmmintrin.h>
#endif

// ---------------------------------------------------------------------------
// Unsigned magnitudes: little-endian 32-bit limbs, no leading zero limbs.
// ---------------------------------------------------------------------------
typedef std::vector<uint32_t> Mag;

static void trim(Mag& a) {
    while (!a.empty() && a.back() == 0) a.pop_back();
}
static Mag from_u64(uint64_t v) {
    Mag a;
    while (v) { a.push_back((uint32_t)v); v >>= 32; }
    return a;
}
static const Mag ONE = from_u64(1);
static bool is_zero(const Mag& a) { return a.empty(); }
static bool odd(const Mag& a) { return !a.empty() && (a[0] & 1); }
static int bitlen(const Mag& a) {
    if (a.empty()) return 0;
    uint32_t t = a.back();
    int n = 0;
    while (t) { n++; t >>= 1; }
    return (int)(a.size() - 1) * 32 + n;
}
static bool bit(const Mag& a, int i) {
    size_t w = (size_t)i / 32;
    return w < a.size() && ((a[w] >> (i % 32)) & 1);
}
static bool is_pow2(const Mag& a) {
    int ones = 0;
    for (uint32_t w : a) for (uint32_t t = w; t; t &= t - 1) ones++;
    return ones == 1;
}
static int cmp(const Mag& a, const Mag& b) {
    if (a.size() != b.size()) return a.size() < b.size() ? -1 : 1;
    for (size_t i = a.size(); i-- > 0;)
        if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    return 0;
}
static Mag add(const Mag& a, const Mag& b) {
    Mag r(std::max(a.size(), b.size()) + 1, 0);
    uint64_t c = 0;
    for (size_t i = 0; i < r.size(); i++) {
        uint64_t s = c;
        if (i < a.size()) s += a[i];
        if (i < b.size()) s += b[i];
        r[i] = (uint32_t)s;
        c = s >> 32;
    }
    trim(r);
    return r;
}
static Mag sub(const Mag& a, const Mag& b) {  // requires a >= b
    Mag r(a.size(), 0);
    int64_t borrow = 0;
    for (size_t i = 0; i < a.size(); i++) {
        int64_t s = (int64_t)a[i] - borrow - (i < b.size() ? (int64_t)b[i] : 0);
        borrow = s < 0;
        if (s < 0) s += (int64_t)1 << 32;
        r[i] = (uint32_t)s;
    }
    trim(r);
    return r;
}
static Mag mul(const Mag& a, const Mag& b) {
    if (a.empty() || b.empty()) return Mag();
    Mag r(a.size() + b.size(), 0);
    for (size_t i = 0; i < a.size(); i++) {
        uint64_t carry = 0;
        for (size_t j = 0; j < b.size(); j++) {
            uint64_t t = (uint64_t)a[i] * b[j] + r[i + j] + carry;
            r[i + j] = (uint32_t)t;
            carry = t >> 32;
        }
        r[i + b.size()] = (uint32_t)carry;
    }
    trim(r);
    return r;
}
static Mag shl(const Mag& a, int n) {
    if (a.empty()) return a;
    size_t words = (size_t)n / 32;
    int bits = n % 32;
    Mag r(a.size() + words + 1, 0);
    for (size_t i = 0; i < a.size(); i++) {
        r[i + words] |= a[i] << bits;
        if (bits) r[i + words + 1] |= a[i] >> (32 - bits);
    }
    trim(r);
    return r;
}
static Mag shr(const Mag& a, int n) {
    size_t words = (size_t)n / 32;
    int bits = n % 32;
    if (words >= a.size()) return Mag();
    Mag r(a.size() - words, 0);
    for (size_t i = 0; i < r.size(); i++) {
        r[i] = a[i + words] >> bits;
        if (bits && i + words + 1 < a.size()) r[i] |= a[i + words + 1] << (32 - bits);
    }
    trim(r);
    return r;
}
static Mag low_bits(const Mag& a, int n) {  // a mod 2^n
    size_t words = (size_t)n / 32;
    int bits = n % 32;
    Mag r(a.begin(), a.begin() + std::min(a.size(), words + (bits ? 1 : 0)));
    if (bits && r.size() == words + 1) r[words] &= (1u << bits) - 1;
    trim(r);
    return r;
}
static void divmod(const Mag& a, const Mag& b, Mag& q, Mag& r) {  // b != 0
    if (is_pow2(b)) {
        int k = bitlen(b) - 1;
        q = shr(a, k);
        r = low_bits(a, k);
        return;
    }
    q.assign(a.size(), 0);
    r.clear();
    for (int i = bitlen(a) - 1; i >= 0; i--) {
        r = shl(r, 1);
        if (bit(a, i)) {
            if (r.empty()) r.push_back(1);
            else r[0] |= 1;
        }
        if (cmp(r, b) >= 0) {
            r = sub(r, b);
            q[i / 32] |= 1u << (i % 32);
        }
    }
    trim(q);
}
static Mag isqrt(const Mag& n) {  // floor(sqrt(n)), Newton from above
    if (n.empty()) return Mag();
    Mag x = shl(ONE, (bitlen(n) + 1) / 2);
    for (;;) {
        Mag q, r;
        divmod(n, x, q, r);
        Mag y = shr(add(x, q), 1);
        if (cmp(y, x) >= 0) return x;
        x = y;
    }
}
static uint64_t to_u64(const Mag& a) {
    uint64_t v = 0;
    for (size_t i = std::min<size_t>(a.size(), 2); i-- > 0;) v = (v << 32) | a[i];
    return v;
}
static Mag from_dec(const std::string& s) {
    Mag r;
    for (char c : s) r = add(mul(r, from_u64(10)), from_u64((uint64_t)(c - '0')));
    return r;
}
static std::string to_dec(Mag a) {
    if (a.empty()) return "0";
    std::string out;
    while (!a.empty()) {
        uint64_t rem = 0;
        for (size_t i = a.size(); i-- > 0;) {
            uint64_t cur = (rem << 32) | a[i];
            a[i] = (uint32_t)(cur / 1000000000u);
            rem = cur % 1000000000u;
        }
        trim(a);
        char buf[16];
        snprintf(buf, sizeof buf, a.empty() ? "%llu" : "%09llu", (unsigned long long)rem);
        out = std::string(buf) + out;
    }
    return out;
}
static std::string to_hex(const Mag& a) {
    if (a.empty()) return "0";
    std::string out;
    char buf[16];
    snprintf(buf, sizeof buf, "%x", a.back());
    out = buf;
    for (size_t i = a.size() - 1; i-- > 0;) {
        snprintf(buf, sizeof buf, "%08x", a[i]);
        out += buf;
    }
    return out;
}

// ---------------------------------------------------------------------------
// Signed integers (sign + magnitude; zero is never negative).
// ---------------------------------------------------------------------------
struct Int {
    bool neg = false;
    Mag m;
};
static Int mk(bool neg, const Mag& m) {
    Int r;
    r.m = m;
    trim(r.m);
    r.neg = neg && !r.m.empty();
    return r;
}
static Int iadd(const Int& a, const Int& b) {
    if (a.neg == b.neg) return mk(a.neg, add(a.m, b.m));
    int c = cmp(a.m, b.m);
    if (c == 0) return Int();
    return c > 0 ? mk(a.neg, sub(a.m, b.m)) : mk(b.neg, sub(b.m, a.m));
}
static Int ineg(const Int& a) { return mk(!a.neg, a.m); }
static Int isub(const Int& a, const Int& b) { return iadd(a, ineg(b)); }
static Int imul(const Int& a, const Int& b) { return mk(a.neg != b.neg, mul(a.m, b.m)); }
static int icmp(const Int& a, const Int& b) {
    if (a.neg != b.neg) return a.neg ? -1 : 1;
    int c = cmp(a.m, b.m);
    return a.neg ? -c : c;
}
static Int parse_int(const std::string& s) {
    bool neg = !s.empty() && s[0] == '-';
    return mk(neg, from_dec(neg ? s.substr(1) : s));
}
static std::string int_str(const Int& a) { return (a.neg ? "-" : "") + to_dec(a.m); }

struct Halt {
    std::string reason;
};

// Exact sum of integers. Each executor defines it (B0 serially, B1 split across
// threads). Integer addition is associative, so no split can change the value.
static int g_threads = 1;
static Int accumulate(const std::vector<Int>& xs);

// nearest-even rounding of num/den (both signs), used by FX DIV and CONST
static Int div_round(const Int& num, const Int& den) {
    Mag q, r;
    divmod(num.m, den.m, q, r);
    int c = cmp(shl(r, 1), den.m);
#if INJECT == 5
    if (c > 0) q = add(q, ONE);  // defect: ties toward zero
#else
    if (c > 0 || (c == 0 && odd(q))) q = add(q, ONE);
#endif
    return mk(num.neg != den.neg, q);
}

// ---------------------------------------------------------------------------
// FX(W, F): raw integers v meaning v / 2^F, range [-2^(W-1), 2^(W-1) - 1].
// ---------------------------------------------------------------------------
struct FX {
    int W, F;
};
static bool fx_in_range(const FX& p, const Int& v) {
#if INJECT == 8
    return true;  // defect: range check skipped
#endif
    int n = bitlen(v.m);
    if (n <= p.W - 1) return true;
    return v.neg && n == p.W && is_pow2(v.m);
}
static Int fx_check(const FX& p, const Int& v) {
    if (!fx_in_range(p, v)) throw Halt{"overflow"};
    return v;
}
// x / 2^F rounded to nearest, ties to even (floor-based, exact for negative x)
static Int round_shift(const Int& x, int F) {
    if (F == 0) return x;
    Mag q = shr(x.m, F), low = low_bits(x.m, F), rem;
    Int qi;
    if (!x.neg) {
        qi = mk(false, q);
        rem = low;
    } else if (is_zero(low)) {
        qi = mk(true, q);
    } else {
        qi = mk(true, add(q, ONE));
        rem = sub(shl(ONE, F), low);
    }
    int c = cmp(rem, shl(ONE, F - 1));
    if (c > 0 || (c == 0 && odd(qi.m))) qi = iadd(qi, mk(false, ONE));
    return qi;
}
static Int fx_mul(const FX& p, const Int& a, const Int& b) {
#if INJECT == 4
    Int x = imul(a, b);  // defect: floor instead of nearest-even
    Mag q = shr(x.m, p.F);
    Int qi = x.neg && !is_zero(low_bits(x.m, p.F)) ? mk(true, add(q, ONE)) : mk(x.neg, q);
    return fx_check(p, qi);
#endif
    return fx_check(p, round_shift(imul(a, b), p.F));
}
static Int fx_div(const FX& p, const Int& a, const Int& b) {
    if (is_zero(b.m)) throw Halt{"division_by_zero"};
    return fx_check(p, div_round(mk(a.neg, shl(a.m, p.F)), b));
}
static Int fx_sqrt(const FX& p, const Int& a) {
    if (a.neg) throw Halt{"sqrt_of_negative"};
    Mag n = shl(a.m, p.F);
    Mag r = isqrt(n);
#if INJECT != 11  // defect 11: floor root, never rounds up
    if (cmp(sub(n, mul(r, r)), r) > 0) r = add(r, ONE);  // n > (r + 1/2)^2 - 1/4
#endif
    return fx_check(p, mk(false, r));
}

// ---------------------------------------------------------------------------
// A-Binary64-Finite: raw 64-bit patterns.
// ---------------------------------------------------------------------------
static const uint64_t SIGN = 1ull << 63;
static const uint64_t MAXF = 0x7FEFFFFFFFFFFFFFull;

static double dbl(uint64_t b) {
    double d;
    memcpy(&d, &b, 8);
    return d;
}
static uint64_t bits_of(double d) {
    uint64_t b;
    memcpy(&b, &d, 8);
    return b;
}
struct Term {
    int sign;
    Mag m;
    int e;
};  // (-1)^sign * m * 2^e
static Term decode(uint64_t b) {
    int field = (int)((b >> 52) & 0x7FF);
    uint64_t frac = b & ((1ull << 52) - 1);
    if (field == 0) return Term{(int)(b >> 63), from_u64(frac), -1074};
    return Term{(int)(b >> 63), from_u64(frac | (1ull << 52)), field - 1075};
}
// round the exact positive value num/den * 2^shift to binary64, nearest-even
static uint64_t b64_round(int sign, Mag num, Mag den, int shift) {
    int k = bitlen(num) - bitlen(den);
    bool ge = k >= 0 ? cmp(num, shl(den, k)) >= 0 : cmp(shl(num, -k), den) >= 0;
    if (!ge) k--;  // now 2^k <= num/den < 2^(k+1)
    int e = std::max(k + shift - 52, -1074);
    int t = shift - e;
    if (t >= 0) num = shl(num, t);
    else den = shl(den, -t);
    Mag q, r;
    divmod(num, den, q, r);
    int c = cmp(shl(r, 1), den);
#if INJECT == 6
    if (c >= 0) q = add(q, ONE);  // defect: ties away from zero
#else
    if (c > 0 || (c == 0 && odd(q))) q = add(q, ONE);
#endif
    uint64_t qq = to_u64(q);
    if (qq == 1ull << 53) { qq = 1ull << 52; e++; }
    uint64_t s = (uint64_t)sign << 63;
    if (qq >= 1ull << 52) {
        int field = e + 1075;
        if (field >= 0x7FF) {
#if INJECT == 3
            return s | MAXF;  // defect: saturate instead of halting
#endif
            throw Halt{"overflow"};
        }
        return s | ((uint64_t)field << 52) | (qq - (1ull << 52));
    }
    return s | qq;  // subnormal: e == -1074
}
static uint64_t hw(double r) {
    if (!std::isfinite(r)) {
#if INJECT == 3
        return (std::signbit(r) ? SIGN : 0) | MAXF;
#endif
        throw Halt{"overflow"};
    }
    return bits_of(r);
}
static uint64_t exact_sum(const std::vector<Term>& ts) {
    int emin = ts[0].e;
    for (const Term& t : ts) emin = std::min(emin, t.e);
    std::vector<Int> xs;
    bool all_neg_zero = true;
    for (const Term& t : ts) {
        if (!(t.sign == 1 && is_zero(t.m))) all_neg_zero = false;
        xs.push_back(mk(t.sign == 1, shl(t.m, t.e - emin)));
    }
    Int s = accumulate(xs);
    if (is_zero(s.m)) {
#if INJECT == 9
        return 0;  // defect: exact zero is always +0
#endif
        return all_neg_zero ? SIGN : 0;
    }
    return b64_round(s.neg ? 1 : 0, s.m, ONE, emin);
}
static uint64_t b64_sum(const std::vector<uint64_t>& v) {
#if INJECT == 1
    double acc = dbl(v[0]);  // defect: sequential hardware float reduction
    for (size_t i = 1; i < v.size(); i++) acc = acc + dbl(v[i]);
    return hw(acc);
#endif
#if INJECT == 101
    // defect (B1): each thread reduces its chunk in hardware floats, partials added in floats
    size_t T = (size_t)g_threads, chunk = (v.size() + T - 1) / T;
    double total = 0.0;
    for (size_t c = 0; c < v.size(); c += chunk) {
        double acc = dbl(v[c]);
        for (size_t i = c + 1; i < std::min(v.size(), c + chunk); i++) acc = acc + dbl(v[i]);
        total = c == 0 ? acc : total + acc;
    }
    return hw(total);
#endif
    std::vector<Term> ts;
    for (uint64_t b : v) ts.push_back(decode(b));
    return exact_sum(ts);
}
static uint64_t b64_dot(const std::vector<uint64_t>& x, const std::vector<uint64_t>& y) {
#if INJECT == 2
    double acc = dbl(x[0]) * dbl(y[0]);  // defect: round every product and every addition
    for (size_t i = 1; i < x.size(); i++) acc = acc + dbl(x[i]) * dbl(y[i]);
    return hw(acc);
#endif
    std::vector<Term> ts;
    for (size_t i = 0; i < x.size(); i++) {
        Term a = decode(x[i]), b = decode(y[i]);
        ts.push_back(Term{a.sign ^ b.sign, mul(a.m, b.m), a.e + b.e});
    }
    return exact_sum(ts);
}
static uint64_t b64_const(const Int& num, const Int& den) {
    if (is_zero(num.m)) return 0;
#if INJECT == 12
    // defect: convert numerator and denominator to double first, then divide
    double n = strtod(to_dec(num.m).c_str(), nullptr), d = strtod(to_dec(den.m).c_str(), nullptr);
    return hw(num.neg ? -(n / d) : n / d);
#endif
    return b64_round(num.neg ? 1 : 0, num.m, den.m, 0);
}
// exact |a - b| of two finite patterns, as M * 2^e; also the comparison result
static int b64_cmp(uint64_t a, uint64_t b, Mag& M, int& e) {
    Term ta = decode(a), tb = decode(b);
    e = std::min(ta.e, tb.e);
    Int ia = mk(ta.sign == 1, shl(ta.m, ta.e - e)), ib = mk(tb.sign == 1, shl(tb.m, tb.e - e));
    M = isub(ia, ib).m;
#if INJECT == 10
    double d = std::fabs(dbl(a) - dbl(b));  // defect: margin through a rounded subtraction
    if (!std::isfinite(d)) { M.clear(); e = 0; }
    else { Term td = decode(bits_of(d)); M = td.m; e = td.e; }
#endif
    return icmp(ia, ib);
}

// ---------------------------------------------------------------------------
// Programs
// ---------------------------------------------------------------------------
struct Instr {
    std::string op, dst;
    std::vector<std::string> args;
};

static std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> out;
    std::istringstream is(line);
    std::string w;
    while (is >> w) out.push_back(w);
    return out;
}

struct Program {
    bool fx = false;
    FX p{0, 0};
    std::vector<std::pair<std::string, std::string>> inputs;
    std::vector<Instr> prog;
};

static std::vector<Program> parse_programs(const char* path) {
    std::ifstream in(path);
    std::string line;
    std::vector<Program> out;
    Program cur;
    while (std::getline(in, line)) {
        std::vector<std::string> w = split(line);
        if (w.empty()) continue;
        if (w[0] == "P") {
            cur = Program();
            cur.fx = w[1] == "FX";
            if (cur.fx) cur.p = FX{atoi(w[2].c_str()), atoi(w[3].c_str())};
        } else if (w[0] == "I") {
            cur.inputs.push_back({w[1], w[2]});
        } else if (w[0] == "X") {
            cur.prog.push_back(Instr{w[1], w[2], std::vector<std::string>(w.begin() + 3, w.end())});
        } else if (w[0] == "E") {
            out.push_back(cur);
        }
    }
    return out;
}

static std::string run_program(const Program& P) {
    const bool fx = P.fx;
    const FX& p = P.p;
    const auto& inputs = P.inputs;
    const auto& prog = P.prog;
    std::string out;
    std::map<std::string, Int> R;       // FX registers
    std::map<std::string, uint64_t> D;  // binary64 registers
    for (auto& kv : inputs) {
        if (fx) R[kv.first] = parse_int(kv.second);
        else D[kv.first] = strtoull(kv.second.c_str(), nullptr, 16);
    }
    std::string branches, halt = "H -\n";
    for (size_t pc = 0; pc < prog.size(); pc++) {
        const Instr& in = prog[pc];
        const std::vector<std::string>& a = in.args;
        try {
            if (in.op == "CONST") {
                Int num = parse_int(a[0]), den = parse_int(a[1]);
                if (fx) R[in.dst] = fx_check(p, div_round(mk(num.neg, shl(num.m, p.F)), den));
                else D[in.dst] = b64_const(num, den);
            } else if (in.op == "SUM" || in.op == "DOT") {
                int k = atoi(a[0].c_str());
                if (in.op == "SUM") {
                    if (fx) {
                        std::vector<Int> xs;
                        for (int i = 0; i < k; i++) xs.push_back(R.at(a[1 + i]));
                        R[in.dst] = fx_check(p, accumulate(xs));
                    } else {
                        std::vector<uint64_t> v;
                        for (int i = 0; i < k; i++) v.push_back(D.at(a[1 + i]));
                        D[in.dst] = b64_sum(v);
                    }
                } else if (fx) {
                    std::vector<Int> xs;
                    for (int i = 0; i < k; i++) xs.push_back(imul(R.at(a[1 + i]), R.at(a[1 + k + i])));
                    R[in.dst] = fx_check(p, round_shift(accumulate(xs), p.F));
                } else {
                    std::vector<uint64_t> x, y;
                    for (int i = 0; i < k; i++) { x.push_back(D.at(a[1 + i])); y.push_back(D.at(a[1 + k + i])); }
                    D[in.dst] = b64_dot(x, y);
                }
            } else if (in.op == "CMP") {
                Mag M;
                int e, res;
                if (fx) {
                    const Int &x = R.at(a[0]), &y = R.at(a[1]);
                    res = icmp(x, y);
                    M = isub(x, y).m;
                    e = -p.F;
                } else {
                    res = b64_cmp(D.at(a[0]), D.at(a[1]), M, e);
                }
                branches += "B " + std::to_string(pc) + " " + std::to_string(res) + " " + to_hex(M) + " " +
                            std::to_string(e) + "\n";
            } else if (fx) {
                const Int& x = R.at(a[0]);
                if (in.op == "ADD") R[in.dst] = fx_check(p, iadd(x, R.at(a[1])));
                else if (in.op == "SUB") R[in.dst] = fx_check(p, isub(x, R.at(a[1])));
                else if (in.op == "MUL") R[in.dst] = fx_mul(p, x, R.at(a[1]));
                else if (in.op == "DIV") R[in.dst] = fx_div(p, x, R.at(a[1]));
                else if (in.op == "NEG") R[in.dst] = fx_check(p, ineg(x));
                else if (in.op == "ABS") R[in.dst] = fx_check(p, mk(false, x.m));
                else if (in.op == "SQRT") R[in.dst] = fx_sqrt(p, x);
                else { fprintf(stderr, "unknown op %s\n", in.op.c_str()); exit(3); }
            } else {
                uint64_t x = D.at(a[0]);
                if (in.op == "ADD") D[in.dst] = hw(dbl(x) + dbl(D.at(a[1])));
                else if (in.op == "SUB") D[in.dst] = hw(dbl(x) - dbl(D.at(a[1])));
                else if (in.op == "MUL") D[in.dst] = hw(dbl(x) * dbl(D.at(a[1])));
                else if (in.op == "DIV") {
                    uint64_t y = D.at(a[1]);
                    if ((y & ~SIGN) == 0) throw Halt{"division_by_zero"};
                    D[in.dst] = hw(dbl(x) / dbl(y));
                } else if (in.op == "NEG") D[in.dst] = x ^ SIGN;
                else if (in.op == "ABS") D[in.dst] = x & ~SIGN;
                else if (in.op == "SQRT") {
                    if ((x & SIGN) && (x & ~SIGN)) throw Halt{"sqrt_of_negative"};
                    D[in.dst] = hw(std::sqrt(dbl(x)));  // sqrt(-0) = -0
                } else { fprintf(stderr, "unknown op %s\n", in.op.c_str()); exit(3); }
            }
        } catch (const Halt& h) {
            halt = "H " + std::to_string(pc) + " " + h.reason + "\n";
            break;
        }
    }
    out += "R\n";
    char buf[32];
    if (fx) for (auto& kv : R) out += "G " + kv.first + " " + int_str(kv.second) + "\n";
    else for (auto& kv : D) {
        snprintf(buf, sizeof buf, "%016llx", (unsigned long long)kv.second);
        out += "G " + kv.first + " " + buf + "\n";
    }
    out += branches + halt + "E\n";
    return out;
}

static void write_file(const char* path, const std::string& s) {
    std::ofstream o(path, std::ios::binary);
    o << s;
}

