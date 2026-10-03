#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <cpython/longintrepr.h>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <cstdint>

// Observation only. CPython 3.12, one Python thread, no physics executor.
struct Entry { unsigned long long begin, bytes; };
struct Span { unsigned long long begin,end,bytes,bits; };
struct State {
    PyMemAllocatorEx previous;
    std::unordered_map<void*,Entry> live;
    std::vector<Span> integers;
    unsigned long long seq=0,allocations=0,total_bytes=0,live_bytes=0,peak_bytes=0;
    bool failed=false;
};
static thread_local State* active=nullptr;
static void inserted(State* s,void* p,size_t size) noexcept {
    if (!p || active!=s || s->failed) return;
    try {
        s->live.emplace(p,Entry{++s->seq,size});
        ++s->allocations;s->total_bytes+=size;s->live_bytes+=size;
        s->peak_bytes=std::max(s->peak_bytes,s->live_bytes);
    } catch (...) {s->failed=true;}
}
static void classified(State* s,void* p,Entry e,unsigned long long end) {
    if (e.bytes<sizeof(PyObject) || Py_TYPE((PyObject*)p)!=&PyLong_Type) return;
    auto* q=(PyLongObject*)p;
    size_t n=q->long_value.lv_tag>>3;
    if (n>(e.bytes - offsetof(PyLongObject,long_value.ob_digit))/sizeof(digit)) {
        s->failed=true;return;
    }
    unsigned long long bits=n ? (n-1)*PyLong_SHIFT : 0;
    if(n){digit high=q->long_value.ob_digit[n-1];while(high){++bits;high>>=1;}}
    s->integers.push_back(Span{e.begin,end,e.bytes,bits});
}
static void removed(State* s,void* p) noexcept {
    if (!p || active!=s || s->failed) return;
    try {
        auto it=s->live.find(p);if(it==s->live.end())return;
        classified(s,p,it->second,++s->seq);
        s->live_bytes-=it->second.bytes;s->live.erase(it);
    } catch (...) {s->failed=true;}
}
static void* observed_malloc(void* ctx,size_t n) {
    auto* s=(State*)ctx;void* p=s->previous.malloc(s->previous.ctx,n);inserted(s,p,n);return p;
}
static void* observed_calloc(void* ctx,size_t n,size_t k) {
    auto* s=(State*)ctx;void* p=s->previous.calloc(s->previous.ctx,n,k);inserted(s,p,n*k);return p;
}
static void observed_free(void* ctx,void* p) {
    auto* s=(State*)ctx;removed(s,p);s->previous.free(s->previous.ctx,p);
}
static void* observed_realloc(void* ctx,void* p,size_t n) {
    auto* s=(State*)ctx;
    // PyLong values are immutable and are not resized through this callback.
    Entry old{0,0};bool known=false;
    if(active==s && !s->failed){auto it=s->live.find(p);if(it!=s->live.end()){old=it->second;known=true;}}
    void* result=s->previous.realloc(s->previous.ctx,p,n);
    if(result){
        if(known){s->live_bytes-=old.bytes;s->live.erase(p);}
        inserted(s,result,n);
    }
    return result;
}
static PyObject* measure(PyObject*,PyObject* args) {
    PyObject* fn;unsigned long long calls;
    if(!PyArg_ParseTuple(args,"OK",&fn,&calls))return nullptr;
    if(!PyCallable_Check(fn) || !calls || active){PyErr_SetString(PyExc_ValueError,"single-thread callable and positive count required");return nullptr;}
    State s;PyMem_GetAllocator(PYMEM_DOMAIN_OBJ,&s.previous);
    PyMemAllocatorEx replacement{&s,observed_malloc,observed_calloc,observed_realloc,observed_free};
    active=&s;PyMem_SetAllocator(PYMEM_DOMAIN_OBJ,&replacement);
    bool python_error=false;
    for(unsigned long long i=0;i<calls;++i){
        PyObject* result=PyObject_CallNoArgs(fn);
        if(!result){python_error=true;break;}
        Py_DECREF(result);
    }
    // Always restore before allocating Python reports or returning an exception.
    active=nullptr;PyMem_SetAllocator(PYMEM_DOMAIN_OBJ,&s.previous);
    if(python_error)return nullptr;
    try {for(auto& row:s.live) classified(&s,row.first,row.second,++s.seq);}catch(...){s.failed=true;}
    if(s.failed){PyErr_SetString(PyExc_RuntimeError,"allocation observation unavailable");return nullptr;}
    unsigned long long big=0,bytes=0,max_bits=0,max_size=0;
    std::vector<std::pair<unsigned long long,long long>> events;
    for(auto e:s.integers){
        if(e.bits<=PyLong_SHIFT)continue;
        ++big;bytes+=e.bytes;max_bits=std::max(max_bits,e.bits);max_size=std::max(max_size,e.bytes);
        events.emplace_back(e.begin,(long long)e.bytes);events.emplace_back(e.end,-(long long)e.bytes);
    }
    std::sort(events.begin(),events.end());long long live=0,peak=0;
    for(auto e:events){live+=e.second;peak=std::max(peak,live);}
    return Py_BuildValue("{s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K,s:K}",
        "calls",calls,"heap_integer_objects",(unsigned long long)s.integers.size(),"bigint_objects",big,
        "bigint_allocated_bytes",bytes,"bigint_max_bits",max_bits,"bigint_max_object_bytes",max_size,
        "bigint_peak_live_bytes",(unsigned long long)peak,"object_allocator_allocations",s.allocations,
        "object_allocator_peak_live_bytes",s.peak_bytes);
}
static PyMethodDef methods[]={{"measure",measure,METH_VARARGS,"Observe actual PyLong object allocations; no timing claim."},{nullptr,nullptr,0,nullptr}};
static PyModuleDef module={PyModuleDef_HEAD_INIT,"pilot3_alloc_probe",nullptr,-1,methods};
PyMODINIT_FUNC PyInit_pilot3_alloc_probe(){
#if PY_MAJOR_VERSION != 3 || PY_MINOR_VERSION != 12
    PyErr_SetString(PyExc_ImportError,"CPython 3.12 required");return nullptr;
#else
    return PyModule_Create(&module);
#endif
}
