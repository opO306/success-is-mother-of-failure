// B0: the simplest serial native executor of A-Numeric VM 0.1 programs.
// docs/current/A_NUMERIC_EXECUTION_STACK_V1.md section 4. No threads, no optimisation.
// Usage: b0 <programs.txt> <results.txt>
#include "anvm_core.hpp"

static Int accumulate(const std::vector<Int>& xs) {
    Int s;
    for (const Int& x : xs) s = iadd(s, x);
    return s;
}

int main(int argc, char** argv) {
#if INJECT == 7
    _mm_setcsr(_mm_getcsr() | 0x8040);  // defect: flush-to-zero + denormals-are-zero
#endif
    if (argc != 3) {
        fprintf(stderr, "usage: b0 <programs.txt> <results.txt>\n");
        return 2;
    }
    std::string out;
    for (const Program& P : parse_programs(argv[1])) out += run_program(P);
    write_file(argv[2], out);
    return 0;
}
