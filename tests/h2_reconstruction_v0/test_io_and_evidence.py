from pathlib import Path
import json
import numpy as np
import mpmath as mp
import pytest
from electronic_pilot.reconstruction_v0.post import quadruple


def test_quadruple_decoder_retains_binary113():
    bits=(16383<<112)+(1<<111)+(1<<20)
    data=np.array([bits&((1<<64)-1),bits>>64],dtype=np.uint64).reshape(1,2)
    with mp.workdps(80):
        assert quadruple(data,(0,))==mp.mpf('1.5')+mp.power(2,-92)
    data[0,1]|=np.uint64(1<<63)
    with mp.workdps(80):assert quadruple(data,(0,))<0


def test_io_repair_changes_only_names_not_numerical_expressions():
    folder=Path('electronic_pilot/reconstruction_v0')
    original=(folder/'numeric.cpp').read_text(encoding='utf-8')
    expected=original
    for a,b in {'/h_high.bin':'/one_body_high.bin','/H_high.bin':'/singlet_matrix_high.bin','/h.bin':'/one_body.bin','/H.bin':'/singlet_matrix.bin'}.items():expected=expected.replace(a,b)
    assert expected==(folder/'numeric_io_v1.cpp').read_text(encoding='utf-8')
    runner=(folder/'run_io_v2.py').read_text(encoding='utf-8')
    assert 'higone_body' not in runner
    assert "target/'singlet_matrix_high.bin'" in runner
    assert "dest/'113/singlet_matrix_high.bin'" in runner


def test_executed_disagreement_is_not_relabelled_equivalent():
    p=Path('docs/active/h2_reconstruction_v0/evidence/summary.json')
    assert p.is_file(), 'actual executed evidence required'
    summary=json.loads(p.read_text(encoding='utf-8'))
    assert summary['overall_accepted_count']==2
    assert summary['measured_classifications']['INDEPENDENT_AO_PATH_DISAGREEMENT']
    assert not summary['measured_classifications']['SAME_BASIS_ENERGY_EQUIVALENCE_SUPPORTED']
    assert summary['inter_arm_comparison']['measured_relation']=='OUTSIDE_BAND'
    assert summary['inter_arm_comparison']['uncertainty_relation']=='UNRESOLVED'
    for row in summary['arms']:
        assert set(row['numerical_guards'])=={'Smin','orth','rank','H','eigen','norm'}
        assert set(row['spatial_guards'])=={'inversion','reflection','Sigma_generator','exchange','rotation_pi_over_7','rotation_pi_over_5','rotation_pi_over_2','raising','lowering','Sz'}
        assert all(x=='PASS' for x in [*row['numerical_guards'].values(),*row['spatial_guards'].values()])
        assert row['precision'][0]['eigensolve']['status']=='REFUSED'
        assert row['precision'][0]['eigensolve']['energy'] is None
        assert row['ground_refinement_converged']
        assert row['energy_64_to_113_shift'] is None
    assert summary['NOT_CERTIFIED'] and summary['STOP']


def test_canonical_zero_is_not_an_independent_accuracy_claim():
    p=json.loads(Path('electronic_pilot/reconstruction_v0/protocol.json').read_text(encoding='utf-8'))
    assert 'never an independent accuracy check' in p['canonical_reuse']['zero_residual']
    for arm in ('L','I'):
        p=Path('docs/active/h2_reconstruction_v0/evidence')/arm/'transform_input_seal.json'
        v=json.loads(p.read_text(encoding='utf-8'))
        assert v['canonical_zero_not_independent_validation']
        assert v['compact_and_direct_share_canonical_AO']
