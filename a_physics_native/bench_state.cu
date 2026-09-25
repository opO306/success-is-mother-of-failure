// CUDA benchmark of C1-B1 state operations by position width (designer 13th ed. item 10). One thread per pair.
// Usage: bench_state_cuda check <limbs 2|3|4> <npairs> <out.txt>
//        bench_state_cuda time  <limbs> <npairs> <iters>     -> ns per pair (GPU time) for drift, dr, R2, kick, bundle
//        bench_state_cuda e2e   <limbs> <npairs>             -> ns per pair: bundle + one C1-A F(R) evaluation (B2 device)
#define AR2_B2_NO_MAIN
#include "ar2_b2.cu"  // device evaluator of C1-A F(R) (B2) + upload_model()
#include "bench_state_io.hpp"

using namespace bench;

template <int N>
__global__ void k_op(Pair<N>* ps, Out<N>* os, const int64_t* Js, int n, int iters, int which, uint32_t* sink) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    Pair<N> s = ps[i];
    Out<N> o = os[i];
    uint32_t acc = 0;
    for (int it = 0; it < iters; it++) {
        if (which == 0 || which == 4) acc += op_drift(s, K_DRIFT);
        if (which == 1 || which == 2 || which == 4) op_dr(s, o);
        if (which == 2 || which == 4) op_R2(o);
        if (which == 3 || which == 4) acc += op_kick(s, &Js[3 * i]);
        acc += o.R2.w[0] ^ o.dr[0].w[0];
    }
    ps[i] = s;
    os[i] = o;
    atomicAdd(sink, acc);
}

template <int N>
__global__ void k_check(Pair<N>* ps, Out<N>* os, const int64_t* Js, int n, int* ok) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    bool g = op_drift(ps[i], K_DRIFT);
    g &= op_kick(ps[i], &Js[3 * i]);
    op_dr(ps[i], os[i]);
    op_R2(os[i]);
    ok[i] = g;
}

template <int N>
__global__ void k_e2e(Pair<N>* ps, Out<N>* os, const int64_t* Js, int n, DAns* ans) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    Pair<N> s = ps[i];
    Out<N> o;
    op_drift(s, K_DRIFT);
    op_dr(s, o);
    op_R2(o);
    double R = sqrt(to_double(o.R2)) / 281474976710656.0;           // timing-proxy input
    DQuery q{1, 1, 0, 64, 0, (uint64_t)__double_as_longlong(R < 2.3 ? 2.3 : R)};
    answer(q, &ans[i], threadIdx.x);
    op_kick(s, &Js[3 * i]);
    ps[i] = s;
}

template <class T>
static T* up(const std::vector<T>& v) {
    T* d;
    CK(cudaMalloc(&d, v.size() * sizeof(T)));
    CK(cudaMemcpy(d, v.data(), v.size() * sizeof(T), cudaMemcpyHostToDevice));
    return d;
}

template <int N>
static int run(const std::string& mode, size_t n, int iters, const char* out) {
    std::vector<Pair<N>> ps;
    std::vector<int64_t> Js;
    make_pairs<N>(ps, Js, n);
    if (mode == "e2e") {
        Rng g;
        for (auto& p : ps)
            for (int k = 0; k < 3; k++) p.rj[k] = add(p.ri[k], from_i64<N>(g.range(6ll << 48)));
    }
    std::vector<Out<N>> os(n);
    Pair<N>* dps = up(ps);
    Out<N>* dos = up(os);
    int64_t* dJ = up(Js);
    uint32_t* sink;
    CK(cudaMalloc(&sink, 4));
    CK(cudaMemset(sink, 0, 4));
    const int B = 128, G = (int)((n + B - 1) / B);
    if (mode == "check") {
        int* dok;
        CK(cudaMalloc(&dok, n * sizeof(int)));
        k_check<N><<<G, B>>>(dps, dos, dJ, (int)n, dok);
        CK(cudaDeviceSynchronize());
        std::vector<int> ok(n);
        CK(cudaMemcpy(ps.data(), dps, n * sizeof(Pair<N>), cudaMemcpyDeviceToHost));
        CK(cudaMemcpy(os.data(), dos, n * sizeof(Out<N>), cudaMemcpyDeviceToHost));
        CK(cudaMemcpy(ok.data(), dok, n * sizeof(int), cudaMemcpyDeviceToHost));
        std::string text;
        for (size_t i = 0; i < n; i++) text += check_line(ps[i], os[i], ok[i] != 0) + "\n";
        std::ofstream(out) << text;
        return 0;
    }
    cudaEvent_t a, b;
    CK(cudaEventCreate(&a));
    CK(cudaEventCreate(&b));
    if (mode == "time") {
        const char* names[] = {"drift", "dr", "dr+R2", "kick", "bundle"};
        for (int w = 0; w < 5; w++) {
            k_op<N><<<G, B>>>(dps, dos, dJ, (int)n, 1, w, sink);   // warm-up
            CK(cudaDeviceSynchronize());
            CK(cudaEventRecord(a));
            k_op<N><<<G, B>>>(dps, dos, dJ, (int)n, iters, w, sink);
            CK(cudaEventRecord(b));
            CK(cudaEventSynchronize(b));
            float ms;
            CK(cudaEventElapsedTime(&ms, a, b));
            printf("%s %.4f\n", names[w], ms * 1e6 / ((double)n * iters));
        }
        return 0;
    }
    if (mode == "e2e") {
        upload_model();
        CK(cudaDeviceSetLimit(cudaLimitStackSize, 60 * 1024));
        DAns* dans;
        CK(cudaMalloc(&dans, n * sizeof(DAns)));
        k_e2e<N><<<G, B>>>(dps, dos, dJ, (int)n, dans);                // warm-up
        CK(cudaDeviceSynchronize());
        CK(cudaEventRecord(a));
        k_e2e<N><<<G, B>>>(dps, dos, dJ, (int)n, dans);
        CK(cudaEventRecord(b));
        CK(cudaEventSynchronize(b));
        CK(cudaGetLastError());
        float ms;
        CK(cudaEventElapsedTime(&ms, a, b));
        printf("e2e_ns %.2f pairs %zu\n", ms * 1e6 / (double)n, n);
        return 0;
    }
    return 2;
}

int main(int argc, char** argv) {
    if (argc < 4) return 2;
    std::string mode = argv[1];
    int L = atoi(argv[2]);
    size_t n = (size_t)atoll(argv[3]);
    int iters = argc > 4 && mode == "time" ? atoi(argv[4]) : 1;
    const char* out = argc > 4 ? argv[4] : "";
    if (L == 2) return run<2>(mode, n, iters, out);
    if (L == 3) return run<3>(mode, n, iters, out);
    if (L == 4) return run<4>(mode, n, iters, out);
    return 2;
}
