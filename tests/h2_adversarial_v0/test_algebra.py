import math
import itertools
import numpy as np
import pytest
from electronic_pilot.adversarial_v0.inputs_v1 import span
from electronic_pilot.adversarial_v0.inputs import radial,uncontract
from electronic_pilot.adversarial_v0.symmetry import angular_generator,coefficient_matrix,spin_action
from electronic_pilot.adversarial_v0.symmetry_diagnostic import cart_generator,monomials
from electronic_pilot.adversarial_v0.transform import four,interaction,diagnostic
import ast
from pathlib import Path
# Execute the sealed pure definitions without importing the Linux-only worker
# resource module. The acquisition/eigensolve worker remains unchanged.
tree=ast.parse(Path('electronic_pilot/adversarial_v0/factorial.py').read_text(encoding='utf-8'))
pure=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef)
                     and node.name in {'pair_indices','pack8','expand8','lower'}],type_ignores=[])
namespace={'np':np};exec(compile(pure,'sealed_factorial_pure_definitions','exec'),namespace)
pack8,expand8,lower=[namespace[name] for name in ('pack8','expand8','lower')]

def test_segmented_and_general_contractions_same_span_exact():
    ours=[[0,[2.,1.],[.2,0.]],[0,[.2,1.]]]
    other=[[0,[2.,1.,0.],[.2,.3,1.]]]
    assert span(ours,other)['equal_span']
    assert not span(ours,[other[0][0:2]])['equal_span']

def test_independent_coefficient_error_reopens_span():
    ours=[[0,[2.,1.],[.2,.3]]];bad=[[0,[2.,1.],[.2,np.nextafter(.3,1.)]]]
    assert not span(ours,bad)['equal_span']

def test_zero_coefficients_not_spurious_functions():
    assert span([[0,[2.,1.],[.2,0.]]],[[0,[2.,1.]]])['equal_span']

def test_uncontract_has_every_original_exponent_no_cutoff():
    a=[[0,[2.,1.],[1e-20,.3]],[0,[2.,.2]],[1,[2.,1.]]]
    assert uncontract(a)==[[0,[1e-20,1.]], [0,[2.,1.]], [1,[2.,1.]]]

@pytest.mark.parametrize('l',[0,1,2,3,4])
def test_analytic_radial_norm(l):
    ex=np.array([.23,1.7]);coef=np.array([[.3],[-.1]]);r=radial(l,ex,coef)
    integrals=math.gamma(l+1.5)/(2*(ex[:,None]+ex[None,:])**(l+1.5))
    assert (r.T@integrals@r).item()==pytest.approx(1.,abs=1e-14)

def test_direct_tensor_contraction_against_explicit_scalar_definition():
    rng=np.random.default_rng(301);g=rng.normal(size=(2,)*4);c=rng.normal(size=(2,2));actual=four(g,c)
    for out in itertools.product(range(2),repeat=4):
        expected=sum(g[a,b,d,e]*c[a,out[0]]*c[b,out[1]]*c[d,out[2]]*c[e,out[3]]
                     for a,b,d,e in itertools.product(range(2),repeat=4))
        assert actual[out]==pytest.approx(expected,abs=1e-13)

def test_axis_swap_fault_detected_on_nonsymmetric_raw_tensor():
    g=np.arange(16.).reshape((2,)*4);c=np.array([[1.,.2],[-.3,.7]])
    assert not np.allclose(four(g,c),four(g.swapaxes(1,2),c))

def test_canonical_representative_has_no_averaging():
    raw=np.arange(81.).reshape((3,)*4);packed=pack8(raw);out=expand8(packed,3)
    for i,j,k,l in itertools.product(range(3),repeat=4):
        a,b=sorted((i,j),reverse=True);d,e=sorted((k,l),reverse=True)
        if a*(a+1)//2+b<d*(d+1)//2+e:a,b,d,e=d,e,a,b
        assert out[i,j,k,l]==raw[a,b,d,e]
    assert diagnostic(out)['pair']['max_absolute']==0
    m=np.array([[1.,9.],[2.,3.]])
    assert np.array_equal(lower(m),[[1.,2.],[2.,3.]])

def test_interaction_detects_nonlinear_connected_effect():
    assert interaction(-2.,-1.8,-1.7,-1.1)==pytest.approx(.4)
    assert interaction(-2.,-1.8,-1.7,-1.5)==pytest.approx(0.)

def test_singlet_normalization_and_spin_ladders():
    order=np.array([[0,0],[0,1],[1,1]]);v=np.array([.2,.7,-.3]);m=coefficient_matrix(v,order,2)
    assert np.linalg.norm(m)==pytest.approx(np.linalg.norm(v))
    assert spin_action(v,order,True)==0 and spin_action(v,order,False)==0

@pytest.mark.parametrize('l',[0,1,2,3,4])
def test_cartesian_generator_matches_independent_polynomial_derivative(l):
    points=np.array([[.23,.47,.81],[-.4,.3,-.2]]);powers=monomials(l);g=cart_generator(l)
    values=np.array([[x**a*y**b*z**c for a,b,c in powers] for x,y,z in points])
    analytic=np.array([[(-a*x**(a-1)*y**(b+1)*z**c if a else 0)+(b*x**(a+1)*y**(b-1)*z**c if b else 0)
                        for a,b,c in powers] for x,y,z in points])
    assert np.allclose(values@g.T,analytic,rtol=0,atol=1e-14)

def test_non_sigma_and_odd_state_faults_are_visible():
    g,f=angular_generator(1);px=np.diag([1.,0.,0.])
    assert np.linalg.norm(g.T@px+px@g)>1.
    zstate=np.diag([0.,0.,1.]);assert np.linalg.norm(g.T@zstate+zstate@g)==0
    parity=np.diag([1.,-1.]);mixed=np.ones((2,2));assert np.linalg.norm(parity.T@mixed@parity-mixed)>1.
