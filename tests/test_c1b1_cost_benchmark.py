"""Reject biased/incomplete costs and numerical reproduction faults."""
import copy
import pytest


def runs(y=110):
    return [dict(method=m,phase='single',cpu_seconds=t,wall_seconds=t,
                 observation_pass=True,reproduction_pass=True)
            for m,t in [('kdk20',100),('yoshida4',y),('yoshida4',y),
                        ('kdk20',100),('kdk20',100),('yoshida4',y)]]


def test_warmups_are_excluded_and_median_not_fastest_is_used():
    from c1b1_cost_benchmark import single_summary
    data=runs(109);data[1]['wall_seconds']=100;data[2]['wall_seconds']=110
    data.append(dict(method='yoshida4',phase='warmup',wall_seconds=1,cpu_seconds=1))
    result=single_summary(data)
    assert result['yoshida4']['median_wall']==109
    assert result['wall_ratio']==1.09


def test_missing_measurement_and_large_jitter_stop():
    from c1b1_cost_benchmark import single_summary
    with pytest.raises(ValueError,match='three'):
        single_summary(runs()[:-1])
    data=runs();data[1]['wall_seconds']=180
    with pytest.raises(ValueError,match='variation'):
        single_summary(data)


@pytest.mark.parametrize('fault', ['observation_pass','reproduction_pass'])
def test_accuracy_failure_is_not_a_cost_verdict(fault):
    from c1b1_cost_benchmark import single_summary
    data=runs();data[0][fault]=False
    with pytest.raises(ValueError,match='numerical'):
        single_summary(data)


def test_incomplete_panel_cannot_be_a_winner():
    from c1b1_cost_benchmark import aggregate
    with pytest.raises(ValueError,match='nine'):
        aggregate([],list('abcdefghi'))


@pytest.mark.parametrize('ratio,want',[(.8,'A'),(1.05,'A'),(1.3,'B')])
def test_aggregate_uses_both_cpu_and_wall_and_keeps_all_outputs(ratio,want):
    from c1b1_cost_benchmark import aggregate
    data=[]
    for key in 'abcdefghi':
        for method,time in [('kdk20',10),('yoshida4',10*ratio)]:
            data.append(dict(id=key,method=method,phase='panel',wall_seconds=time,
                cpu_seconds=time,outer_steps=2,calls={'force':3},output_bytes=9,
                peak_rss_kib=20,observation_pass=True,reproduction_pass=True))
    result=aggregate(data,list('abcdefghi'))
    assert result['conclusion']==want
    assert result['totals']['kdk20']['output_bytes']==81
    mixed=copy.deepcopy(data)
    for r in mixed:
        if r['method']=='yoshida4':
            r['cpu_seconds']=20
            r['wall_seconds']=10
    assert aggregate(mixed,list('abcdefghi'))['conclusion']=='C'


def test_local_scattering_is_refused_before_reading_inputs(monkeypatch,tmp_path):
    from c1b1_cost_benchmark import run_trajectory
    monkeypatch.delenv('C1B1_REMOTE_BENCHMARK',raising=False)
    with pytest.raises(ValueError,match='remote-only'):
        run_trajectory('kdk20',None,tmp_path,'bad',None)


def test_common_observer_writes_all_states_and_counts_real_force_calls(monkeypatch,tmp_path):
    import gzip,json,sys,types
    import mpmath as m
    import c1b1_cost_benchmark as bench
    class FreePES:
        def value_derivative(self,r):return m.mpf(0),m.mpf(0)
    original=bench.Field
    monkeypatch.setattr(bench,'Field',lambda mu:original(mu,FreePES))
    monkeypatch.setattr(bench,'MASS','2/1')
    monkeypatch.setattr(bench,'DE','1')
    monkeypatch.setenv('C1B1_REMOTE_BENCHMARK','1')
    # Windows unit test supplies only the Linux OS telemetry boundary.
    if sys.platform=='win32':
        monkeypatch.setitem(sys.modules,'resource',types.SimpleNamespace(
            RUSAGE_SELF=0,getrusage=lambda _:types.SimpleNamespace(ru_maxrss=0)))
        monkeypatch.setattr(bench.os,'sched_getaffinity',lambda _:{0},raising=False)
    # Hand-derived noncanonical free-motion unit input: q=(3,0), p=(1/64,0).
    raw=[0]*12;raw[6]=3*2**48;raw[9]=2**75
    row=dict(id='unit_free',input={'raw':raw},base_radius='3.1',reference=dict(
        H='0.0001220703125',L='0',chi='0',direction='0',r_min='3',sweep='0',time='0'))
    for method,want_q,want_calls in [('kdk20','3.3125',2),('yoshida4','3.625',4)]:
        r=bench.run_trajectory(method,row,tmp_path,method,None)
        assert r['outer_steps']==1 and r['calls']['force']==want_calls
        assert abs(m.mpf(r['q_out'][0])-m.mpf(want_q))<m.mpf('1e-20')
        assert m.mpf(r['energy_max_change_De'])==0
        with gzip.open(tmp_path/(method+'.jsonl.gz'),'rt') as stream:
            states=[json.loads(x) for x in stream]
        assert len(states)==2 and states[0][0]==0 and states[-1][0]==1
        assert r['output_bytes']==sum((tmp_path/(method+s)).stat().st_size for s in ('.json','.jsonl.gz'))


def test_extension_preserves_original_bytes_and_rejects_replacement(tmp_path):
    import io,json,tarfile
    from tools.c1b1_cost_package import build
    base=tmp_path/'base.tar.gz'
    with tarfile.open(base,'w:gz') as tf:
        for name,data in [('code/original.py',b'original'),('manifest.json',json.dumps(
                {'originals':{},'objects':{'code/original.py':{'sha256':'unused','bytes':8}}}).encode())]:
            member=tarfile.TarInfo(name);member.size=len(data);tf.addfile(member,io.BytesIO(data))
    out=tmp_path/'extended.tar.gz';build(base,{'code/new.py':b'new'},out)
    with tarfile.open(out) as tf:assert tf.extractfile('code/original.py').read()==b'original'
    with pytest.raises(ValueError,match='replace'):
        build(base,{'code/original.py':b'mutant'},tmp_path/'bad.tar.gz')
