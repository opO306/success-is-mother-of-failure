// Independent unpivoted interval LDL^T, not derived from H2SOLV.
// Nonzero interval pivots certify a congruence. A zero-containing pivot refuses.
#include <mpfr.h>
#include <gmp.h>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <stdexcept>
#include <chrono>
#include <algorithm>

struct I {
    mpfr_t lo, hi;
    I() { mpfr_init(lo); mpfr_init(hi); mpfr_set_zero(lo,0); mpfr_set_zero(hi,0); }
    I(const I& a):I() { mpfr_set(lo,a.lo,MPFR_RNDD); mpfr_set(hi,a.hi,MPFR_RNDU); }
    ~I() { mpfr_clear(lo); mpfr_clear(hi); }
};
size_t ix(size_t i,size_t j) { return i*(i+1)/2+j; }
void valid(const I& a) {
    if (!mpfr_number_p(a.lo)||!mpfr_number_p(a.hi)||mpfr_cmp(a.lo,a.hi)>0)
        throw std::runtime_error("nonfinite/unordered interval");
}
void sub(I& c,const I& a,const I& b) {
    mpfr_sub(c.lo,a.lo,b.hi,MPFR_RNDD);
    mpfr_sub(c.hi,a.hi,b.lo,MPFR_RNDU); valid(c);
}
void mul(I& c,const I& a,const I& b,I& tmp) {
    mpfr_mul(c.lo,a.lo,b.lo,MPFR_RNDD);
    mpfr_mul(c.hi,a.lo,b.lo,MPFR_RNDU);
    mpfr_srcptr aa[2]={a.lo,a.hi},bb[2]={b.lo,b.hi};
    for(int u=0;u<2;u++) for(int v=0;v<2;v++) if(u||v) {
        mpfr_mul(tmp.lo,aa[u],bb[v],MPFR_RNDD);
        mpfr_mul(tmp.hi,aa[u],bb[v],MPFR_RNDU);
        if(mpfr_cmp(tmp.lo,c.lo)<0) mpfr_set(c.lo,tmp.lo,MPFR_RNDD);
        if(mpfr_cmp(tmp.hi,c.hi)>0) mpfr_set(c.hi,tmp.hi,MPFR_RNDU);
    }
    valid(c);
}
void reciprocal(I& c,const I& a) {
    if(mpfr_sgn(a.lo)<=0&&mpfr_sgn(a.hi)>=0) throw std::runtime_error("division by zero interval");
    mpfr_ui_div(c.lo,1,a.hi,MPFR_RNDD);
    mpfr_ui_div(c.hi,1,a.lo,MPFR_RNDU); valid(c);
}
void dyadic(mpfr_srcptr v) {
    mpz_t z; mpz_init(z); auto e=mpfr_get_z_2exp(z,v);
    char* s=mpz_get_str(nullptr,10,z); std::cout << s << ' ' << e;
    void (*freefunc)(void*,size_t); mp_get_memory_functions(nullptr,nullptr,&freefunc);
    freefunc(s,std::char_traits<char>::length(s)+1); mpz_clear(z);
}
int main(int argc,char** argv) { try {
    if(argc!=4) throw std::runtime_error("args: matrix bits SPD|INERTIA");
    long bits=std::stol(argv[2]); if(bits<32||bits>4096) throw std::runtime_error("bits");
    mpfr_set_default_prec(bits);
    std::ifstream in(argv[1]); size_t n;
    if(!(in>>n)||n==0||n>1000) throw std::runtime_error("dimension");
    std::vector<I> a(n*(n+1)/2); mpz_t z; mpz_init(z);
    for(auto& v:a) {
        std::string m; long e;
        if(!(in>>m>>e)||mpz_set_str(z,m.c_str(),10)||e<-100000||e>100000)
            throw std::runtime_error("bad dyadic");
        mpfr_set_z_2exp(v.lo,z,e,MPFR_RNDD); mpfr_set_z_2exp(v.hi,z,e,MPFR_RNDU); valid(v);
    }
    mpz_clear(z); std::string extra; if(in>>extra) throw std::runtime_error("trailing data");
    const bool spd=std::string(argv[3])=="SPD";
    if(!spd&&std::string(argv[3])!="INERTIA") throw std::runtime_error("mode");
    I rec, ratio, prod, tmp, term; int neg=0,pos=0; size_t done=0,chosen=0;
    std::string status="COMPLETE"; auto start=std::chrono::steady_clock::now();
    for(size_t k=0;k<n;k++) {
        auto& d=a[ix(k,k)];
        int sign=mpfr_sgn(d.lo)>0?1:(mpfr_sgn(d.hi)<0?-1:0);
        std::cout << "PIVOT "<<k<<' '<<sign<<' '; dyadic(d.lo); std::cout<<' ';dyadic(d.hi);std::cout<<'\n';
        if(!sign) { status="UNCERTAIN"; chosen=k; break; }
        if(sign<0) neg++; else pos++;
        if(spd&&sign<0) { status="NOT_SPD"; chosen=k; break; }
        if(mpfr_cmp(d.lo,a[ix(chosen,chosen)].lo)<0) chosen=k;
        reciprocal(rec,d);
        for(size_t j=k+1;j<n;j++) {
            mul(ratio,a[ix(j,k)],rec,tmp);
            for(size_t i=j;i<n;i++) {
                mul(prod,a[ix(i,k)],ratio,tmp);
                sub(a[ix(i,j)],a[ix(i,j)],prod);
            }
        }
        // Save interval L entries after the Schur update, using no overwritten inputs.
        for(size_t i=k+1;i<n;i++) {
            mul(ratio,a[ix(i,k)],rec,tmp);
            mpfr_set(a[ix(i,k)].lo,ratio.lo,MPFR_RNDD);
            mpfr_set(a[ix(i,k)].hi,ratio.hi,MPFR_RNDU);
        }
        done=k+1;
    }
    std::cout << "RESULT "<<status<<' '<<neg<<' '<<pos<<' '<<(status=="UNCERTAIN"?1:0)<<' '<<done<<' '<<n<<'\n';
    if(spd&&status!="UNCERTAIN") {
        // One approximate Schur direction. Exact dyadic qform is checked separately in Python.
        std::vector<I> x(chosen+1); mpfr_set_ui(x[chosen].lo,1,MPFR_RNDN);
        for(int i=int(chosen)-1;i>=0;i--) {
            mpfr_set_zero(x[i].lo,0);
            for(size_t j=i+1;j<=chosen;j++) {
                mpfr_add(tmp.lo,a[ix(j,i)].lo,a[ix(j,i)].hi,MPFR_RNDN);
                mpfr_div_2ui(tmp.lo,tmp.lo,1,MPFR_RNDN);
                mpfr_mul(term.lo,tmp.lo,x[j].lo,MPFR_RNDN);
                mpfr_sub(x[i].lo,x[i].lo,term.lo,MPFR_RNDN);
            }
        }
        for(size_t i=0;i<x.size();i++) { std::cout<<"DIRECTION "<<i<<' ';dyadic(x[i].lo);std::cout<<'\n'; }
        if(status=="COMPLETE") {
            // ||L^-1||_inf <= max_i b_i, b_i=1+sum_{j<i}|L_ij|b_j.
            // ||L^-1||_2^2 <= n*max(b)^2; lambda_min(S)>=min(D)/(n*max(b)^2).
            std::vector<I> b(n); mpfr_set_ui(prod.hi,1,MPFR_RNDU);
            for(size_t i=0;i<n;i++) {
                mpfr_set_ui(b[i].hi,1,MPFR_RNDU);
                for(size_t j=0;j<i;j++) {
                    mpfr_abs(tmp.lo,a[ix(i,j)].lo,MPFR_RNDU);
                    mpfr_abs(tmp.hi,a[ix(i,j)].hi,MPFR_RNDU);
                    if(mpfr_cmp(tmp.lo,tmp.hi)>0) mpfr_set(tmp.hi,tmp.lo,MPFR_RNDU);
                    mpfr_mul(term.hi,tmp.hi,b[j].hi,MPFR_RNDU);
                    mpfr_add(b[i].hi,b[i].hi,term.hi,MPFR_RNDU);
                }
                if(mpfr_cmp(b[i].hi,prod.hi)>0) mpfr_set(prod.hi,b[i].hi,MPFR_RNDU);
            }
            mpfr_sqr(tmp.hi,prod.hi,MPFR_RNDU);mpfr_mul_ui(tmp.hi,tmp.hi,n,MPFR_RNDU);
            mpfr_div(term.lo,a[ix(chosen,chosen)].lo,tmp.hi,MPFR_RNDD);
            std::cout<<"LAMBDA_MIN_LOWER ";dyadic(term.lo);std::cout<<'\n';
        }
    }
    std::cout<<"ENV "<<mpfr_get_version()<<' '<<gmp_version<<' '<<bits<<'\n';
    std::cout<<"SECONDS "<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<'\n';
    return 0;
} catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 2; } }
