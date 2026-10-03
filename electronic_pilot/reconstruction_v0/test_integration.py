"""Explicit WSL native tests; separate from Windows related-test collection."""
from pathlib import Path
import subprocess,json
import numpy as np
from electronic_pilot.reconstruction_v0.run import canon_eri
from electronic_pilot.ground_state_audit_v0.operator import dense


def execute(tmp_path,h,g,c):
    inp=tmp_path/'input';out=tmp_path/'output';inp.mkdir();out.mkdir()
    h.tofile(inp/'h_canonical.bin');canon_eri(g)[0].tofile(inp/'g_canonical.bin');c.tofile(inp/'c.bin')
    subprocess.run(['/home/otherside123/h2-reconstruction-io-v2/numeric','113',str(inp),str(out),str(len(c))],check=True,capture_output=True)
    return out


def test_ordered_quad_transform_and_ci_match_fermion_operator(tmp_path):
    h=np.array([[-1.,.1],[.1,-.5]]);g=np.arange(16,dtype=float).reshape((2,)*4)/100;c=np.array([[1.,.2],[0.,1.1]])
    out=execute(tmp_path,h,g,c)
    hm=np.fromfile(out/'one_body.bin').reshape(2,2);gm=np.fromfile(out/'g.bin').reshape((2,)*4);H=np.fromfile(out/'singlet_matrix.bin').reshape(3,3)
    expected=dense(hm,gm)[0]
    assert np.max(abs(expected-H))<1e-14
    assert (out/'one_body_high.bin').stat().st_size==4*16
    assert (out/'singlet_matrix_high.bin').stat().st_size==9*16
    assert json.loads((out/'transform.json').read_text())['canonical_MO_reuse'] is False


def test_asymmetric_one_body_is_not_repaired(tmp_path):
    out=execute(tmp_path,np.array([[-1.,.2],[.1,-.5]]),np.zeros((2,)*4),np.eye(2))
    H=np.fromfile(out/'singlet_matrix.bin').reshape(3,3)
    assert np.max(abs(H-H.T))>1e-2
    assert float(json.loads((out/'transform.json').read_text())['H_asym_max'])>1e-2
