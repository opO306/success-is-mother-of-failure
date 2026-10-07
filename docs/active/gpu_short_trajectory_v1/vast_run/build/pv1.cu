// GPU_PAIR_VECTOR_V1 (protocol.json): pair impulses J = (h*g)*d (gate A) and the canonical per-atom reduction (gate B)
// on the GPU, replicating exact_expression_gate_v1.stream.run's forces() with the E2 force.
//
// The G0 device arithmetic, the G(R^2) program interpreter's constant memory and the G0 host API are included
// VERBATIM from experiments/gpu_force_feasibility_v1/g0.cu (sha256_lf dc519a9c..., not modified). Everything below
// is new: the pair table, kernel 1 (d, r2, K.domain), kernel 2 (G), kernel 3 (J), kernel 4 (canonical reduction).
// Stage faults use d_pvfault (G0's own d_fault stays 0 except fault 14, which reuses G0 fault 8 with reduced width).
#include "g0.cu"

#define PV_ST_PROVEN 0
#define PV_ST_UNPROVEN 1
#define PV_ST_VIOLATED 2
#define PV_ST_REF_WIDTH 3
#define PV_ST_REF_PREC 4
#define WORDS_FULL 114   // status, pid, mask, prec, r2, G, J0, J1, J2
#define WORDS_COMPACT 68 // status, pid, J0, J1, J2
#define WORDS_ATOM 26    // atom, component, prec, status, F

__device__ int d_pvfault;
__constant__ uint32_t c_h[WORDS_MPI];
__constant__ uint32_t c_rmin_a[DL + 1];  // R_MIN2 = a / b (n, limbs)
__constant__ uint32_t c_rmin_b[DL + 1];

__device__ __noinline__ void load_iv(MPI& v, const uint32_t* w) {
    load_mp(v.a, w);
    load_mp(v.b, w + WORDS_MP);
}
__device__ __noinline__ void store_iv(uint32_t* w, const MPI& v) {
    store_mp(w, v.a);
    store_mp(w + WORDS_MP, v.b);
}
__device__ __forceinline__ void iv_zero(MPI& v) { mp_zero(v.a); mp_zero(v.b); }
__device__ __noinline__ void const_dn(DN& d, const uint32_t* w) {
    d.n = (int)w[0];
    for (int i = 0; i < d.n; i++) d.w[i] = w[1 + i];
}
// sign of (x - a/b) for a finite mpf x, a, b > 0; returns -2 on width overflow
__device__ __noinline__ int cmp_rmin(const MP& x) {
    if (!x.n || x.sign) return -1;
    DN a, b, m, l, r;
    const_dn(a, c_rmin_a);
    const_dn(b, c_rmin_b);
    mp_man(m, x);
    dn_mul(l, m, b);
    if (x.exp >= 0) { dn_shl(l, l, (int)x.exp); dn_copy(r, a); }
    else { dn_shl(r, a, (int)-x.exp); }
    if (bad(l) || bad(r)) return -2;
    return dn_cmp(l, r);
}

// kernel 1: d[k] = q[j][k] - q[i][k]; r2 = (d0*d0 + d1*d1) + d2*d2; status = K.domain(r2)
__global__ void pv_k_dr2(int N, int P, const int* pairs, const uint32_t* pos, uint32_t* dbuf, uint32_t* r2buf, int* st) {
    int stride = gridDim.x * blockDim.x;
    for (int pid = blockIdx.x * blockDim.x + threadIdx.x; pid < P; pid += stride) {
        int i = pairs[2 * pid], j = pairs[2 * pid + 1];
        Ctx c;
        c.prec = c_prec;
        c.flags = 0;
        MPI d[3], qi, qj, a, b, t, r2;
        for (int k = 0; k < 3; k++) {
            int jj = (d_pvfault == 2 && k == 1) ? (j + 1) % N : j;  // fault 2: dy from another pair
            load_iv(qi, pos + (size_t)(3 * i + k) * WORDS_MPI);
            load_iv(qj, pos + (size_t)(3 * jj + k) * WORDS_MPI);
            if (d_pvfault == 1 && k == 0) mpi_sub(d[k], qi, qj, c);   // fault 1: dx sign reversed
            else mpi_sub(d[k], qj, qi, c);
        }
        mpi_mul(a, d[0], d[0], c);
        mpi_mul(b, d[1], d[1], c);
        mpi_add(t, a, b, c);
        if (d_pvfault == 5) {
            r2 = t;                                                    // fault 5: one R^2 term missing
        } else {
            mpi_mul(a, d[2], d[2], c);
            mpi_add(r2, t, a, c);
        }
        int s;
        if (c.flags) {
            s = (c.flags & 1) ? PV_ST_REF_WIDTH : PV_ST_REF_PREC;
        } else {
            int lo = cmp_rmin(r2.a), hi = cmp_rmin(r2.b);
            if (lo == -2 || hi == -2) s = PV_ST_REF_WIDTH;
            else if (lo >= 0) s = PV_ST_PROVEN;
            else if (hi < 0) s = PV_ST_VIOLATED;
            else s = PV_ST_UNPROVEN;
            if (d_pvfault == 6 && s != PV_ST_REF_WIDTH) s = PV_ST_PROVEN;  // fault 6: domain check removed
        }
        for (int k = 0; k < 3; k++) store_iv(dbuf + ((size_t)pid * 3 + k) * WORDS_MPI, d[k]);
        store_iv(r2buf + (size_t)pid * WORDS_MPI, r2);
        st[pid] = s;
    }
}

// kernel 2: G(r2) by the G0 program (copied interpreter loop of g0_kernel) for PROVEN pairs
__global__ void pv_k_G(int P, const uint32_t* r2buf, int* st, uint32_t* gbuf, int* mask) {
    int stride = gridDim.x * blockDim.x;
    for (int pid = blockIdx.x * blockDim.x + threadIdx.x; pid < P; pid += stride) {
        MPI res;
        iv_zero(res);
        int m = 0;
        if (st[pid] == PV_ST_PROVEN) {
            MPI regs[NREG];
            load_iv(regs[0], r2buf + (size_t)pid * WORDS_MPI);
            Ctx c;
            c.prec = c_prec;
            c.flags = 0;
            int status = 0;
            for (int k = 0; k < c_ncode && !status; k++) {
                int code = c_code[4 * k], dst = c_code[4 * k + 1], a = c_code[4 * k + 2], b = c_code[4 * k + 3];
                MPI va, vb, r;
                get_val(va, regs, a);
                switch (code) {
                case 0: get_val(vb, regs, b); mpi_add(r, va, vb, c); break;
                case 1: get_val(vb, regs, b); mpi_sub(r, va, vb, c); break;
                case 2: get_val(vb, regs, b); mpi_mul(r, va, vb, c); break;
                case 3: get_val(vb, regs, b); mpi_div(r, va, vb, c); break;
                case 4: mpi_neg(r, va, c); break;
                case 5: mpi_sqrt(r, va, c); break;
                case 6: mpi_exp(r, va, c); break;
                case 7:
                    if (mp_sgn(va.a) > 0) m |= 1 << b;
                    else status = 1;
                    break;
                case 8: res = va; break;
                }
                if (c.flags) status = (c.flags & 1) ? 2 : 3;
                if (!status && dst >= 0) regs[dst] = r;
            }
            if (status == 1) st[pid] = PV_ST_UNPROVEN;  // RwForce raises DomainStop(UNPROVEN)
            else if (status == 2) st[pid] = PV_ST_REF_WIDTH;
            else if (status == 3) st[pid] = PV_ST_REF_PREC;
        }
        store_iv(gbuf + (size_t)pid * WORDS_MPI, res);
        mask[pid] = m;
    }
}

// kernel 3: J[k] = (h*g)*d[k], h*g recomputed per k as in the source; writes the full and the compact records
__global__ void pv_k_J(int P, const uint32_t* dbuf, const uint32_t* r2buf, const uint32_t* gbuf, const int* st,
                       const int* mask, uint32_t* jbuf, uint32_t* full, uint32_t* compact) {
    int stride = gridDim.x * blockDim.x;
    for (int pid = blockIdx.x * blockDim.x + threadIdx.x; pid < P; pid += stride) {
        MPI J[3], h, g, d, hg, gd;
        for (int k = 0; k < 3; k++) iv_zero(J[k]);
        int s = st[pid];
        Ctx c;
        c.prec = c_prec;
        c.flags = 0;
        if (s == PV_ST_PROVEN) {
            load_iv(h, c_h);
            load_iv(g, gbuf + (size_t)pid * WORDS_MPI);
            for (int k = 0; k < 3; k++) {
                load_iv(d, dbuf + ((size_t)pid * 3 + k) * WORDS_MPI);
                if (d_pvfault == 4) {                         // fault 4: h*(g*d)
                    mpi_mul(gd, g, d, c);
                    mpi_mul(J[k], h, gd, c);
                } else {
                    mpi_mul(hg, h, g, c);
                    mpi_mul(J[k], hg, d, c);
                }
                if (d_pvfault == 3 && k == 2) iv_zero(J[k]);  // fault 3: dz component not written
            }
            if (c.flags) s = (c.flags & 1) ? PV_ST_REF_WIDTH : PV_ST_REF_PREC;
        }
        for (int k = 0; k < 3; k++) store_iv(jbuf + ((size_t)pid * 3 + k) * WORDS_MPI, J[k]);
        uint32_t* f = full + (size_t)pid * WORDS_FULL;
        f[0] = (uint32_t)s;
        f[1] = (uint32_t)pid;
        f[2] = (uint32_t)mask[pid];
        f[3] = (uint32_t)c_prec;
        for (int w = 0; w < WORDS_MPI; w++) {
            f[4 + w] = r2buf[(size_t)pid * WORDS_MPI + w];
            f[4 + WORDS_MPI + w] = gbuf[(size_t)pid * WORDS_MPI + w];
        }
        for (int k = 0; k < 3; k++) store_iv(f + 4 + 2 * WORDS_MPI + k * WORDS_MPI, J[k]);
        uint32_t* o = compact + (size_t)pid * WORDS_COMPACT;
        o[0] = (uint32_t)s;
        o[1] = (uint32_t)pid;
        for (int k = 0; k < 3; k++) store_iv(o + 2 + k * WORDS_MPI, J[k]);
    }
}

__device__ __forceinline__ int pair_id(int N, int i, int j) { return i * (2 * N - i - 1) / 2 + (j - i - 1); }

// kernel 4: one thread per (atom a, component k); canonical order: +J for (i, a), i < a, then -J for (a, j), j > a
__global__ void pv_k_reduce(int N, const uint32_t* jbuf, const int* st, uint32_t* atoms) {
    int stride = gridDim.x * blockDim.x;
    for (int t = blockIdx.x * blockDim.x + threadIdx.x; t < 3 * N; t += stride) {
        int a = t / 3, k = t % 3;
        Ctx c;
        c.prec = c_prec;
        c.flags = 0;
        MPI F, J, r;
        iv_zero(F);
        int status = 0, n = N - 1;
        int rot = (d_pvfault == 11 && n > 0) ? (int)(blockIdx.x % n) : 0;  // fault 11: layout-dependent order
        for (int q = 0; q < n; q++) {
            int idx = (q + rot) % n;                          // position in a's canonical pair list
            if (d_pvfault == 10) idx = (idx < n - a) ? idx + a : idx - (n - a);  // fault 10: (a, j) pairs first
            int other = idx < a ? idx : idx + 1;
            int i = other < a ? other : a, j = other < a ? a : other;
            int pid = pair_id(N, i, j);
            if (st[pid] != PV_ST_PROVEN) { status = st[pid]; break; }
            load_iv(J, jbuf + ((size_t)pid * 3 + k) * WORDS_MPI);
            bool plus = (a == j);
            if (d_pvfault == 9) plus = !plus;                 // fault 9: + / - reversed
            if (plus) mpi_add(r, F, J, c);
            else mpi_sub(r, F, J, c);
            F = r;
        }
        if (c.flags) status = (c.flags & 1) ? PV_ST_REF_WIDTH : PV_ST_REF_PREC;
        if (status) iv_zero(F);
        uint32_t* o = atoms + (size_t)t * WORDS_ATOM;
        o[0] = (uint32_t)a;
        o[1] = (uint32_t)k;
        o[2] = (uint32_t)c_prec;
        o[3] = (uint32_t)status;
        store_iv(o + 4, F);
    }
}

// ---------------------------------------------------------------------------
// Host API (ctypes)
// ---------------------------------------------------------------------------
static int pv_N = 0, pv_P = 0;
static int* pv_pairs = nullptr;
static int *pv_st = nullptr, *pv_mask = nullptr;
static uint32_t *pv_pos = nullptr, *pv_d = nullptr, *pv_r2 = nullptr, *pv_g = nullptr, *pv_j = nullptr;
static uint32_t *pv_full = nullptr, *pv_compact = nullptr, *pv_atoms = nullptr;
static size_t pv_bytes = 0;

G0_API int pv_upload_consts(const uint32_t* h, const uint32_t* rmin_a, const uint32_t* rmin_b) {
    cudaError_t e = cudaMemcpyToSymbol(c_h, h, WORDS_MPI * 4);
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(c_rmin_a, rmin_a, (DL + 1) * 4);
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(c_rmin_b, rmin_b, (DL + 1) * 4);
    return (int)e;
}

static void pv_release() {
    void* ps[] = {pv_pairs, pv_st, pv_mask, pv_pos, pv_d, pv_r2, pv_g, pv_j, pv_full, pv_compact, pv_atoms};
    for (void* p : ps)
        if (p) cudaFree(p);
    pv_pairs = nullptr; pv_st = pv_mask = nullptr;
    pv_pos = pv_d = pv_r2 = pv_g = pv_j = pv_full = pv_compact = pv_atoms = nullptr;
    pv_N = pv_P = 0;
    pv_bytes = 0;
}

// allocates every buffer for N atoms and uploads the canonical pair table; bytes[0..10] = per-buffer bytes
G0_API int pv_alloc(int N, unsigned long long* bytes, double* ms) {
    auto t0 = std::chrono::steady_clock::now();
    pv_release();
    int P = N * (N - 1) / 2;
    size_t sz[11] = {(size_t)P * 2 * 4, (size_t)P * 4, (size_t)P * 4, (size_t)N * 3 * WORDS_MPI * 4,
                     (size_t)P * 3 * WORDS_MPI * 4, (size_t)P * WORDS_MPI * 4, (size_t)P * WORDS_MPI * 4,
                     (size_t)P * 3 * WORDS_MPI * 4, (size_t)P * WORDS_FULL * 4, (size_t)P * WORDS_COMPACT * 4,
                     (size_t)N * 3 * WORDS_ATOM * 4};
    void** dst[11] = {(void**)&pv_pairs, (void**)&pv_st, (void**)&pv_mask, (void**)&pv_pos, (void**)&pv_d,
                      (void**)&pv_r2, (void**)&pv_g, (void**)&pv_j, (void**)&pv_full, (void**)&pv_compact,
                      (void**)&pv_atoms};
    cudaError_t e = cudaSuccess;
    for (int b = 0; b < 11 && e == cudaSuccess; b++) {
        e = cudaMalloc(dst[b], sz[b] ? sz[b] : 4);
        bytes[b] = sz[b];
        pv_bytes += sz[b];
    }
    if (e == cudaSuccess && P > 0) {
        int* tab = new int[2 * P];
        int k = 0;
        for (int i = 0; i < N; i++)
            for (int j = i + 1; j < N; j++) { tab[k++] = i; tab[k++] = j; }
        e = cudaMemcpy(pv_pairs, tab, (size_t)P * 2 * 4, cudaMemcpyHostToDevice);
        delete[] tab;
    }
    pv_N = N;
    pv_P = P;
    *ms = ms_since(t0);
    return (int)e;
}

// want: bit0 full pair records, bit1 compact pair records, bit2 atom reduction + atom records
// times: [h2d, k_dr2, k_G, k_J, k_reduce, d2h_full, d2h_compact, d2h_atoms]
G0_API int pv_run(const uint32_t* pos, int want, int block, int grid, int fault, int g0fault, int wl,
                  uint32_t* out_full, uint32_t* out_compact, uint32_t* out_atoms, float* times) {
    if (!pv_P) return -3;
    if (wl < 1 || wl > DL) return -4;
    int N = pv_N, P = pv_P;
    cudaError_t e = cudaMemcpyToSymbol(d_pvfault, &fault, sizeof(int));
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(d_fault, &g0fault, sizeof(int));
    if (e == cudaSuccess) e = cudaMemcpyToSymbol(d_wl, &wl, sizeof(int));
    if (e != cudaSuccess) return (int)e;
    auto gsz = [&](int work) { return grid > 0 ? grid : (work + block - 1) / block; };
    cudaEvent_t ev[9];
    for (int i = 0; i < 9; i++) cudaEventCreate(&ev[i]);
    for (int i = 0; i < 8; i++) times[i] = 0;
    cudaEventRecord(ev[0]);
    e = cudaMemcpy(pv_pos, pos, (size_t)N * 3 * WORDS_MPI * 4, cudaMemcpyHostToDevice);
    cudaEventRecord(ev[1]);
    if (e == cudaSuccess) { pv_k_dr2<<<gsz(P), block>>>(N, P, pv_pairs, pv_pos, pv_d, pv_r2, pv_st); e = cudaGetLastError(); }
    cudaEventRecord(ev[2]);
    if (e == cudaSuccess) { pv_k_G<<<gsz(P), block>>>(P, pv_r2, pv_st, pv_g, pv_mask); e = cudaGetLastError(); }
    cudaEventRecord(ev[3]);
    if (e == cudaSuccess) {
        pv_k_J<<<gsz(P), block>>>(P, pv_d, pv_r2, pv_g, pv_st, pv_mask, pv_j, pv_full, pv_compact);
        e = cudaGetLastError();
    }
    cudaEventRecord(ev[4]);
    if (e == cudaSuccess && (want & 4)) { pv_k_reduce<<<gsz(3 * N), block>>>(N, pv_j, pv_st, pv_atoms); e = cudaGetLastError(); }
    cudaEventRecord(ev[5]);
    if (e == cudaSuccess && (want & 1)) e = cudaMemcpy(out_full, pv_full, (size_t)P * WORDS_FULL * 4, cudaMemcpyDeviceToHost);
    cudaEventRecord(ev[6]);
    if (e == cudaSuccess && (want & 2)) e = cudaMemcpy(out_compact, pv_compact, (size_t)P * WORDS_COMPACT * 4, cudaMemcpyDeviceToHost);
    cudaEventRecord(ev[7]);
    if (e == cudaSuccess && (want & 4)) e = cudaMemcpy(out_atoms, pv_atoms, (size_t)N * 3 * WORDS_ATOM * 4, cudaMemcpyDeviceToHost);
    cudaEventRecord(ev[8]);
    cudaEventSynchronize(ev[8]);
    if (e == cudaSuccess) e = cudaGetLastError();
    for (int i = 0; i < 8; i++) cudaEventElapsedTime(&times[i], ev[i], ev[i + 1]);
    for (int i = 0; i < 9; i++) cudaEventDestroy(ev[i]);
    return (int)e;
}

// copies the device position buffer back (input echo)
G0_API int pv_echo_positions(uint32_t* out) {
    if (!pv_N) return -3;
    return (int)cudaMemcpy(out, pv_pos, (size_t)pv_N * 3 * WORDS_MPI * 4, cudaMemcpyDeviceToHost);
}

G0_API void pv_free() { pv_release(); }
