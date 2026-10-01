"""Detect coefficient, mass-weighted gradient, negative drift and gate faults."""
import mpmath as m
import pytest


class Harmonic:
    def __init__(self, mu=1):
        self.mu=m.mpf(mu)
    def force(self,q):
        return [-x for x in q]
    def gradient_force(self,q,h):
        return [-x+h*h*x/(24*self.mu) for x in q]


@pytest.mark.parametrize('method',['yoshida4','chin4a'])
def test_harmonic_global_fourth_order_and_reversibility(method):
    from c1b1_integrator_benchmark.methods import advance
    with m.workdps(60):
        errors=[]
        for count in (5,10,20):
            h=m.mpf(1)/count;q=[m.mpf(1),m.mpf(0)];p=[m.mpf(0),m.mpf(0)]
            for _ in range(count):
                q,p=advance(method,q,p,h,m.mpf(1),Harmonic(),lambda a,b:None)
            errors.append(abs(q[0]-m.cos(1))+abs(p[0]+m.sin(1)))
            for _ in range(count):
                q,p=advance(method,q,p,-h,m.mpf(1),Harmonic(),lambda a,b:None)
            assert abs(q[0]-1)+abs(p[0])<m.mpf('1e-50')
        assert 14<errors[0]/errors[1]<18
        assert 14<errors[1]/errors[2]<18


def test_chin_gradient_uses_inverse_mass():
    from c1b1_integrator_benchmark.methods import advance
    with m.workdps(60):
        q,p=advance('chin4a',[m.mpf(1)],[m.mpf(0)],m.mpf('.2'),m.mpf(3),Harmonic(3),lambda a,b:None)
        assert abs(q[0]-m.cos(m.mpf('.2')/m.sqrt(3)))<m.mpf('1e-8')


def test_negative_internal_chord_is_checked():
    from c1b1_integrator_benchmark.methods import advance
    with m.workdps(40):
        drifts=[]
        advance('yoshida4',[m.mpf(20),m.mpf(0)],[m.mpf(1),m.mpf(0)],m.mpf(1),m.mpf(1),Harmonic(),lambda a,b:drifts.append(b[0]-a[0]))
        assert len(drifts)==3
        assert any(x<0 for x in drifts)


@pytest.mark.parametrize('error,cost,gain,stable,want',[
    ('2e-5','1','1',True,'REJECT_ACCURACY'),
    ('1e-7','5','30',True,'REJECT_COST'),
    ('1e-8','1.5','300',True,'PROMISING_PARETO'),
    ('1e-6','.8','3',True,'BEATS_KDK20_KERNEL'),
    ('1e-9','.8','3000',False,'UNRESOLVED_PRECISION'),
])
def test_first_stage_gate(error,cost,gain,stable,want):
    from c1b1_integrator_benchmark.methods import first_gate
    assert first_gate(float(error),float(cost),float(gain),stable,True,True)==want


def test_domain_and_bad_conservation_stop():
    from c1b1_integrator_benchmark.methods import first_gate
    assert first_gate(1e-9,.8,3000,True,False,True)=='REJECT_DOMAIN'
    assert first_gate(1e-9,.8,3000,True,True,False)=='REJECT_CONSERVATION'


def test_gradient_calls_are_counted_and_do_not_poison_energy_cache():
    from c1b1_integrator_benchmark.study import Field
    class HarmonicPES:
        def value_derivative(self,r):return r*r/2,r
    with m.workdps(50):
        field=Field(m.mpf(4),HarmonicPES)
        q=[m.mpf(3),m.mpf(4)];h=m.mpf('.2')
        f=field.gradient_force(q,h)
        assert abs(f[0]-(-3+h*h*3/96))<m.mpf('1e-40')
        assert field.value==m.mpf('12.5')
        assert field.calls['force']==1
        assert field.calls['gradient_derivative']>=2
        field.force(q)
        assert field.calls['force']==1


def test_all_internal_chords_detect_domain_crossing():
    from c1b1_integrator_benchmark.study import chord_minimum
    assert chord_minimum([m.mpf(5),m.mpf(0)],[m.mpf(-5),m.mpf(0)])==0


def test_benchmark_import_boundary():
    import ast
    from pathlib import Path
    for path in Path('c1b1_integrator_benchmark').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
            assert not any(x.split('.')[0] in {'a_reference','a_numeric','engine','audit','c1b1_replay'} for x in names)


def test_local_trajectory_is_refused_before_os_or_physics(monkeypatch):
    from c1b1_integrator_benchmark.study import simulate
    monkeypatch.delenv('C1B1_REMOTE_BENCHMARK',raising=False)
    with pytest.raises(ValueError,match='remote-only'):
        simulate(('chin4a','boundary_pass',60,0))
