// Independent integral generation only. No libcint calls or CI/energy code.
// Coefficients already include the independently checked radial normalization.
// Cartesian monomials remain unnormalized; polynomial spherical map is external.
#include <libint2.hpp>
#include <fstream>
#include <iostream>
#include <chrono>
#include <vector>
#include <array>
#include <stdexcept>
#include <sys/resource.h>

void store(const std::string& path,const std::vector<double>& a) {
  std::ofstream f(path,std::ios::binary);f.write(reinterpret_cast<const char*>(a.data()),a.size()*sizeof(double));
  if(!f)throw std::runtime_error("binary write failed");
}
int main(int argc,char**argv) {
 try {
  if(argc!=3)throw std::runtime_error("input output-directory");
  const auto start=std::chrono::steady_clock::now();std::ifstream input(argv[1]);
  size_t ns;input>>ns;std::vector<libint2::Shell> shells;size_t maxprim=0;int maxl=0;
  std::vector<size_t> loc{0};
  for(size_t sh=0;sh<ns;++sh){
    int l;size_t np;std::array<double,3> xyz;input>>l>>np>>xyz[0]>>xyz[1]>>xyz[2];
    libint2::svector<double> alpha,coeff;
    for(size_t k=0;k<np;++k){double a,c;input>>a>>c;alpha.push_back(a);coeff.push_back(c);}
    libint2::svector<libint2::Shell::Contraction> ctr{{l,false,coeff}};
    shells.emplace_back(alpha,ctr,xyz,false);
    loc.push_back(loc.back()+shells.back().size());maxprim=std::max(maxprim,np);maxl=std::max(maxl,l);
  }
  if(!input || shells.empty())throw std::runtime_error("invalid shell input");
  const size_t n=loc.back();std::string out=argv[2];libint2::initialize();
  std::vector<double> s(n*n),t(n*n),v(n*n),eri(n*n*n*n);
  std::vector<libint2::Operator> ops{libint2::Operator::overlap,libint2::Operator::kinetic,libint2::Operator::nuclear};
  for(size_t type=0;type<ops.size();++type){
    libint2::Engine eng(ops[type],maxprim,maxl,0);eng.set_precision(0);eng.set(libint2::CartesianShellNormalization::standard);
    if(type==2)eng.set_params(std::vector<std::pair<double,std::array<double,3>>>{{1.,{0.,0.,-.2}},{1.,{0.,0.,.2}}});
    auto& dest=type==0?s:(type==1?t:v);
    for(size_t a=0;a<ns;++a)for(size_t b=0;b<ns;++b){
      eng.compute(shells[a],shells[b]);const double* buf=eng.results()[0];
      for(size_t i=0;i<shells[a].size();++i)for(size_t j=0;j<shells[b].size();++j)
        dest[(loc[a]+i)*n+loc[b]+j]=buf?buf[i*shells[b].size()+j]:0.;
    }
  }
  libint2::Engine eng(libint2::Operator::coulomb,maxprim,maxl,0);eng.set_precision(0);eng.set(libint2::CartesianShellNormalization::standard);
  size_t nullblocks=0;
  for(size_t a=0;a<ns;++a){
   for(size_t b=0;b<ns;++b)for(size_t c=0;c<ns;++c)for(size_t d=0;d<ns;++d){
    eng.compute(shells[a],shells[b],shells[c],shells[d]);const double* buf=eng.results()[0];if(!buf)++nullblocks;
    size_t pos=0;
    for(size_t i=0;i<shells[a].size();++i)for(size_t j=0;j<shells[b].size();++j)
     for(size_t k=0;k<shells[c].size();++k)for(size_t m=0;m<shells[d].size();++m,++pos)
      eri[(((loc[a]+i)*n+loc[b]+j)*n+loc[c]+k)*n+loc[d]+m]=buf?buf[pos]:0.;
   }
   std::cout<<"shell "<<a+1<<"/"<<ns<<std::endl;
  }
  store(out+"/s_cart.bin",s);store(out+"/t_cart.bin",t);store(out+"/v_cart.bin",v);store(out+"/eri_cart.bin",eri);
  struct rusage mem;getrusage(RUSAGE_SELF,&mem);
  const auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  std::ofstream meta(out+"/native.json");
  meta<<"{\"ncart\":"<<n<<",\"shells\":"<<ns<<",\"null_ERI_blocks\":"<<nullblocks<<",\"runtime_seconds\":"<<seconds<<",\"peak_rss_kib\":"<<mem.ru_maxrss
      <<",\"screening_precision\":0,\"normalization_embedded\":false,\"Cartesian_convention\":\"standard\",\"byteorder\":\"little host x86_64\"}";
  libint2::finalize();return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
