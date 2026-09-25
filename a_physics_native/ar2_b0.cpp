// B0: serial native evaluator of the C1-A Ar-Ar V(R) and F(R) (ar2_core.hpp). No threads.
// Usage: ar2_b0 <queries.txt> <answers.txt>   |   ar2_b0 selftest
#include "ar2_core.hpp"

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

int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "selftest") return selftest();
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
