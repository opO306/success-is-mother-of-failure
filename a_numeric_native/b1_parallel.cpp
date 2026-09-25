// B1: parallel CPU executor of A-Numeric VM 0.1 programs.
// docs/current/A_NUMERIC_EXECUTION_STACK_V1.md section 4 (E9: the thread count
// must not change any result). Two levels of parallelism, both with T threads:
//   * independent programs run on different threads, results kept in input order;
//   * every SUM / DOT splits its terms into T contiguous chunks, each chunk is
//     summed EXACTLY on its own thread, and the exact partials are added.
// Exact integer addition is associative, so the split cannot change the value;
// the single rounding happens after the exact total, as in the VM.
// Usage: b1 <threads> <programs.txt> <results.txt>
#include <thread>

#include "anvm_core.hpp"

static Int accumulate(const std::vector<Int>& xs) {
    size_t T = (size_t)g_threads, n = xs.size();
    if (T <= 1 || n < 2) {
        Int s;
        for (const Int& x : xs) s = iadd(s, x);
        return s;
    }
#if INJECT == 102
    size_t chunk = std::max<size_t>(1, n / T);  // defect: floor chunk, the tail past T chunks is dropped
#else
    size_t chunk = (n + T - 1) / T;
#endif
    std::vector<Int> partial(T);
    std::vector<std::thread> pool;
    for (size_t t = 0; t < T; t++) {
        size_t lo = std::min(n, t * chunk), hi = std::min(n, lo + chunk);
        pool.emplace_back([&partial, &xs, t, lo, hi] {
            Int s;
            for (size_t i = lo; i < hi; i++) s = iadd(s, xs[i]);
            partial[t] = s;
        });
    }
    for (std::thread& th : pool) th.join();
    Int s;
    for (const Int& x : partial) s = iadd(s, x);
    return s;
}

int main(int argc, char** argv) {
    if (argc != 4 || atoi(argv[1]) < 1) {
        fprintf(stderr, "usage: b1 <threads> <programs.txt> <results.txt>\n");
        return 2;
    }
    g_threads = atoi(argv[1]);
    std::vector<Program> progs = parse_programs(argv[2]);
    std::vector<std::string> results(progs.size());
    std::vector<std::thread> pool;
    for (int t = 0; t < g_threads; t++)
        pool.emplace_back([&progs, &results, t] {
            for (size_t i = (size_t)t; i < progs.size(); i += (size_t)g_threads) results[i] = run_program(progs[i]);
        });
    for (std::thread& th : pool) th.join();
    std::string out;
    for (const std::string& r : results) out += r;
    write_file(argv[3], out);
    return 0;
}
