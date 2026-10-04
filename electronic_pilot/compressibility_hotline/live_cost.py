"""Separately sealed live fixed-H corridor and fresh-process RSS/cost probe.

No modification of the completed checkpoint-accounting capture.
Each physical round evolves the preceding actual restored output.
The full dense unitary is charged to every path; no cheap evolution claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time
import numpy as np
from . import baseline,checker,tensor


def rss():
    return int(next(line for line in Path('/proc/self/smaps_rollup').read_text().splitlines() if line.startswith('Rss:')).split()[1])*1024


def load(key):
    with np.load('docs/active/electronic_representation_survey_v1/'+key+'_corpus.npz') as z:d={k:z[k] for k in z.files}
    d.update(label=key,electrons=1 if key=='A' else 2)
    return d


def child(key,path):
    p=json.loads(Path('electronic_pilot/compressibility_hotline/protocol.json').read_text())
    samples=[rss()];stop=threading.Event()
    def sample():
        while not stop.wait(.002):samples.append(rss())
    th=threading.Thread(target=sample);th.start()
    d=load(key);samples.append(rss())
    before=time.process_time()
    step=d['u'] @ (np.exp(-1j*d['e']*.5)[:,None]*(d['u'].T@d['s']))
    prepare=time.process_time()-before
    independent=checker.unitary(d,.5)
    assert np.max(abs(independent-step))<1e-9
    times=[];counters=[];corridor=[];outputs={}
    for repeat in range(p['cost_repeats']):
        c=dict(evolution_cpu=0.,observable_cpu=0.,baseline_cpu=0.,monitor_cpu=0.,conversion_cpu=0.,
               refine_cpu=0.,enclosure_cpu=0.,monitor_with_acquisition_cpu=0.,accounting_total_cpu=0.)
        start=time.process_time()
        for name,initial in zip(p['states'],d['states']):
            for order in p['orders']:
                v=initial.copy();reference=initial.copy();ind=initial.copy();states=[]
                for epoch in range(3):
                    if epoch:
                        t=time.process_time();v=step@v;c['evolution_cpu']+=time.process_time()-t
                        reference=step@reference;ind=independent@ind
                    # Every path has its own evolving v, dependent on its previous output.
                    if path!='REF':
                        receipt,out=baseline.run(np.array([v]),d,p,path,order)
                        v=out[0]
                        c['accounting_total_cpu']+=receipt['cost']['total_cpu']
                        for k in c:
                            if k in receipt['cost']:c[k]+=receipt['cost'][k]
                    t=time.process_time()
                    np.vdot(v,d['s']@v);np.vdot(v,d['h']@v)
                    tensor.density(v,d)
                    [np.vdot(v,op@v) for op in d['dipoles']]
                    c['observable_cpu']+=time.process_time()-t
                    assert v.tobytes()==reference.tobytes()
                    met=checker.physical(ind,v,d)
                    assert max(met.values())<1e-9
                    states.append(v.copy())
                    if repeat==0:corridor.append(dict(state=name,order=order,epoch=epoch,
                         canonical_bits_equal_dense=True,independent_metrics=met))
                if repeat==0:outputs[name,order]=np.array(states)
        c['engine_cpu']=c['evolution_cpu']+c['observable_cpu']+c['accounting_total_cpu']
        times.append(time.process_time()-start);counters.append(c);samples.append(rss())
    for name in p['states']:
        assert all(outputs[name,o].tobytes()==outputs[name,'ascending'].tobytes() for o in p['orders'])
    plus=outputs['plus','ascending'][-1];minus=outputs['minus','ascending'][-1]
    fp,fm=step@plus,step@minus
    phase=dict(future_density_difference=float(np.max(abs(checker.density(fp,d)-checker.density(fm,d)))),
               future_dipole_difference=float(max(abs(np.vdot(fp,o@fp)-np.vdot(fm,o@fm)) for o in d['dipoles'])))
    stop.set();th.join()
    costs={k:statistics.median(r[k] for r in counters) for k in counters[0]}
    return dict(corpus=key,path=path,cpu_samples=times,cpu_median=statistics.median(times),cost_medians=costs,
      propagator_preparation_cpu=prepare,observed_peak_RSS_bytes=max(samples),initial_RSS_bytes=samples[0],samples=len(samples),
      independent_live_corridor=corridor,phase=phase,
      cost_scope='5 repeats; each 5 states x 3 orders x 3 physical rounds; validation and source monitoring charged; propagator setup separate',
      representation_scope='per-round accounting classifier restarts COLD; hysteresis temporal tests are separate primary/control traces',
      RAM_scope='fresh child smaps_rollup boundaries + 2ms samples, observed maximum including interpreter/monitor, not absolute peak')


def main(output):
    folder=Path(output);folder.mkdir(parents=True,exist_ok=False)
    source=Path(__file__)
    seal=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              primary_capture_unchanged_sha256=hashlib.sha256(Path('runs/electronic_compressibility_hotline_v1_20261004/capture_v1/closure.json').read_bytes()).hexdigest(),
              protocol='existing fixed times/states/orders/cost_repeats; full propagator; exact restore before next round')
    (folder/'seal.json').write_text(json.dumps(seal,indent=2))
    results=[]
    for key in ['A','B']:
        for path in ['REF','BASELINE','HOTLINE']:
            r=subprocess.run([sys.executable,'-m','electronic_pilot.compressibility_hotline.live_cost',
                              '--corpus',key,'--path',path],capture_output=True,text=True,check=True)
            (folder/(key+'_'+path+'_stdout.json')).write_text(r.stdout)
            results.append(json.loads(r.stdout));print(key,path,'finished',flush=True)
    (folder/'results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output');parser.add_argument('--corpus');parser.add_argument('--path');a=parser.parse_args()
    if a.output:main(a.output)
    else:print(json.dumps(child(a.corpus,a.path)))
