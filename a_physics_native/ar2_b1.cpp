// B1: parallel CPU evaluator of the C1-A Ar-Ar V(R) and F(R) (ar2_core.hpp).
// Two kinds of parallelism, neither of which may change a bit (E9-style layout independence):
//   * queries spread over T threads -- "chunk" (contiguous blocks) or "stride" (round-robin), each thread
//     with its own precision cache, answers written back in input order;
//   * "split": additionally, inside every query, the three components (BO, REL, QED) are evaluated on
//     separate threads and their exact integer intervals added in the order they finish.
// Usage: ar2_b1 <threads> <chunk|stride|split> <queries.txt> <answers.txt>
#include "ar2_core.hpp"

#include <atomic>
#include <future>
#include <mutex>

static Int accumulate(const std::vector<Int>& xs) {  // required by anvm_core; unused here
    Int s;
    for (const Int& x : xs) s = iadd(s, x);
    return s;
}

static ar2::IV split_eval(const ar2::Dyadic& R, bool ret, bool deriv, int M, ar2::Cache&) {
    std::vector<std::future<ar2::IV>> parts;
    for (int c = 0; c < 3; c++)
        parts.push_back(std::async(std::launch::async, [&, c]() {
            ar2::Cache own;
            return ar2::evaluate_iv(R, ret, deriv, M, own, 1 << c);
        }));
    // add in completion order (polling), not in component order
    ar2::IV total{};
    std::vector<bool> done(3, false);
    for (int left = 3; left > 0;)
        for (int c = 2; c >= 0; c--)
            if (!done[c] && parts[c].wait_for(std::chrono::microseconds(50)) == std::future_status::ready) {
#if INJECT == 101
                if (c == 1) { done[c] = true; left--; parts[c].get(); continue; }  // defect: REL part dropped
#endif
                total = ar2::iv_add(total, parts[c].get());
                done[c] = true;
                left--;
            }
    return total;
}

int main(int argc, char** argv) {
    if (argc != 5) {
        fprintf(stderr, "usage: ar2_b1 <threads> <chunk|stride|split> <queries.txt> <answers.txt>\n");
        return 2;
    }
    int T = std::max(1, atoi(argv[1]));
    std::string layout = argv[2];
    std::vector<ar2::Query> qs = ar2::read_queries(argv[3]);
    std::vector<std::string> ans(qs.size());
    size_t n = qs.size(), chunk = (n + T - 1) / T;
    std::vector<std::thread> th;
    for (int t = 0; t < T; t++)
        th.emplace_back([&, t]() {
            ar2::Cache cache;
            auto one = [&](size_t i) {
                ar2::Evaluator ev = layout == "split" ? split_eval : ar2::evaluate_all;
#if INJECT == 102
                if (t == T - 1 && T > 1) ev = [](const ar2::Dyadic& R, bool ret, bool deriv, int M, ar2::Cache& c) {
                    ar2::IV v = ar2::evaluate_iv(R, ret, deriv, 64, c);  // defect: last thread at fixed M = 64
                    return ar2::IV{mk(v.lo.neg, shl(v.lo.m, M - 64)), mk(v.lo.neg, shl(v.lo.m, M - 64))};
                };
#endif
                ans[i] = ar2::answer(qs[i].qty, qs[i].ret, qs[i].p, qs[i].raw, cache, ev);
            };
            if (layout == "stride")
                for (size_t i = t; i < n; i += T) one(i);
            else
                for (size_t i = t * chunk; i < std::min(n, (t + 1) * chunk); i++) one(i);
        });
    for (auto& x : th) x.join();
    ar2::write_answers(argv[4], ans);
    return 0;
}
