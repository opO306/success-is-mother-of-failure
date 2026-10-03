// Audit only: fixed binary64 AO data, explicit contractions, no averaging.
#include <quadmath.h>
#include <cmath>
#include <vector>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <string>
#include <stdexcept>
#include <limits>
#include <chrono>
#include <sys/resource.h>
template<class T> T root(T x){return sqrtl(x);}
template<> __float128 root(__float128 x){return sqrtq(x);}
template<class T> T magnitude(T x){return x<0?-x:x;}
template<class T> std::string decimal(T x){char b[160];snprintf(b,sizeof b,"%.24Lg",(long double)x);return b;}
template<> std::string decimal(__float128 x){char b[160];quadmath_snprintf(b,sizeof b,"%.38Qg",x);return b;}
template<class T> std::vector<T> load(const std::string& p,size_t n){std::vector<T>x(n);std::ifstream f(p,std::ios::binary);f.read((char*)x.data(),n*sizeof(T));if(!f||f.peek()!=EOF)throw std::runtime_error("size/read "+p);return x;}
template<class T> void save(const std::string&p,const std::vector<T>&x){std::ofstream f(p,std::ios::binary);f.write((const char*)x.data(),x.size()*sizeof(T));if(!f)throw std::runtime_error("write "+p);}
template<class T> void save64(const std::string&p,const std::vector<T>&x){std::vector<double>y(x.begin(),x.end());save(p,y);}
template<class T> void transform(const std::string&in,const std::string&out,int n){
 const auto start=std::chrono::steady_clock::now();const size_t n4=size_t(n)*n*n*n;
 auto cd=load<double>(in+"/c.bin",n*n),gd=load<double>(in+"/g_canonical.bin",n4),hd=load<double>(in+"/h_canonical.bin",n*n);
 std::vector<T>c(cd.begin(),cd.end()),a(gd.begin(),gd.end()),b(n4),h(n*n);std::vector<std::vector<std::pair<int,T>>>cols(n);
 for(int j=0;j<n;++j)for(int i=0;i<n;++i)if(c[i*n+j]!=0)cols[j].push_back({i,c[i*n+j]});
 // Contract one index at a time; all ordered output elements evaluated.
 for(int axis=3;axis>=0;--axis){size_t stride=1;for(int z=axis+1;z<4;++z)stride*=n;
  for(size_t base=0;base<n4;base+=stride*n)for(size_t tail=0;tail<stride;++tail)for(int j=0;j<n;++j){T sum=0;for(auto [i,v]:cols[j])sum+=a[base+i*stride+tail]*v;b[base+j*stride+tail]=sum;}
  a.swap(b);std::cout<<"axis "<<axis<<std::endl;
 }
 for(int i=0;i<n;++i)for(int j=0;j<n;++j){T sum=0;for(auto [u,x]:cols[i])for(auto [v,y]:cols[j])sum+=x*T(hd[u*n+v])*y;h[i*n+j]=sum;}
 auto idx=[n](int i,int j,int k,int l){return (((size_t(i)*n+j)*n+k)*n+l);};
 T ij=0,kl=0,pair=0,hasym=0;size_t pair_idx=0;
 for(int i=0;i<n;++i)for(int j=0;j<n;++j){hasym=std::max(hasym,magnitude(h[i*n+j]-h[j*n+i]));for(int k=0;k<n;++k)for(int l=0;l<n;++l){auto p=idx(i,j,k,l);ij=std::max(ij,magnitude(a[p]-a[idx(j,i,k,l)]));kl=std::max(kl,magnitude(a[p]-a[idx(i,j,l,k)]));T d=magnitude(a[p]-a[idx(k,l,i,j)]);if(d>pair){pair=d;pair_idx=p;}}}
 save(out+"/g_high.bin",a);save(out+"/one_body_high.bin",h);save64(out+"/g.bin",a);save64(out+"/one_body.bin",h);
 std::vector<std::pair<int,int>>states;for(int i=0;i<n;++i)for(int j=i;j<n;++j)states.push_back({i,j});int m=states.size();std::vector<T>H(size_t(m)*m);
 auto product=[&](int i,int j,int k,int l){return (j==l?h[i*n+k]:T(0))+(i==k?h[j*n+l]:T(0))+a[idx(i,k,j,l)];};
 for(int p=0;p<m;++p)for(int q=0;q<m;++q){auto [i,j]=states[p];auto [k,l]=states[q];H[size_t(p)*m+q]=(product(i,j,k,l)+product(i,j,l,k)+product(j,i,k,l)+product(j,i,l,k))/(root(T(2*(1+(i==j))))*root(T(2*(1+(k==l)))));}
 T Hasy=0;for(int p=0;p<m;++p)for(int q=0;q<m;++q)Hasy=std::max(Hasy,magnitude(H[size_t(p)*m+q]-H[size_t(q)*m+p]));
 save(out+"/singlet_matrix_high.bin",H);save64(out+"/singlet_matrix.bin",H);struct rusage r;getrusage(RUSAGE_SELF,&r);
 std::ofstream meta(out+"/transform.json");meta<<"{\"significand_bits\":"<<(std::is_same<T,__float128>::value?113:std::numeric_limits<long double>::digits)<<",\"MO_ij_max\":\""<<decimal(ij)<<"\",\"MO_kl_max\":\""<<decimal(kl)<<"\",\"MO_pair_max\":\""<<decimal(pair)<<"\",\"pair_flat_index\":"<<pair_idx<<",\"h_asym_max\":\""<<decimal(hasym)<<"\",\"H_asym_max\":\""<<decimal(Hasy)<<"\",\"dimension\":"<<m<<",\"canonical_MO_reuse\":false,\"runtime_seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peak_rss_kib\":"<<r.ru_maxrss<<"}";
}
void refine(const std::string&in,const std::string&out,int m){
 using T=__float128;auto H=load<T>(in+"/singlet_matrix_high.bin",size_t(m)*m);std::vector<T>v(m);
 std::ifstream f(in+"/vector.txt");std::string s;for(int i=0;i<m;++i){f>>s;v[i]=strtoflt128(s.c_str(),nullptr);}if(!f)throw std::runtime_error("vector");
 auto correction=load<double>(in+"/correction.bin",m);T norm=0;for(int i=0;i<m;++i){v[i]+=T(correction[i]);norm+=v[i]*v[i];}norm=root(norm);for(auto &x:v)x/=norm;
 std::vector<T>w(m),r(m);T e=0;for(int i=0;i<m;++i){T sum=0;for(int j=0;j<m;++j)sum+=H[size_t(i)*m+j]*v[j];w[i]=sum;e+=v[i]*sum;}
 T res=0,normerr=0;for(int i=0;i<m;++i){r[i]=w[i]-e*v[i];res+=r[i]*r[i];normerr+=v[i]*v[i];}save64(out+"/residual.bin",r);
 std::ofstream vec(out+"/vector.txt");for(auto x:v)vec<<decimal(x)<<"\n";save64(out+"/vector.bin",v);
 std::ofstream meta(out+"/refinement.json");meta<<"{\"electronic_energy\":\""<<decimal(e)<<"\",\"eigen_residual_l2\":\""<<decimal(root(res))<<"\",\"vector_norm_error\":\""<<decimal(magnitude(normerr-1))<<"\",\"significand_bits\":113}";
}
int main(int argc,char**argv){try{if(argc!=5)throw std::runtime_error("mode input output n");int n=std::stoi(argv[4]);std::string mode=argv[1];if(mode=="64")transform<long double>(argv[2],argv[3],n);else if(mode=="113")transform<__float128>(argv[2],argv[3],n);else if(mode=="refine")refine(argv[2],argv[3],n);else throw std::runtime_error("mode");return 0;}catch(std::exception&e){std::cerr<<e.what()<<std::endl;return 1;}}
