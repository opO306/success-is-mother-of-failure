"""Deployment faults must fail before any paid node start or trajectory."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest


@pytest.mark.parametrize('name', ['/tmp/source', 'D:/reference/a', '../escape', 'code/../../escape', 'code\\source'])
def test_reject_nonportable_manifest_names(name):
    from tools.c1b1_dt40_package import portable_name
    with pytest.raises(ValueError):
        portable_name(name)


def test_only_location_assignment_may_change():
    from tools.c1b1_dt40_package import relocate
    old="from pathlib import Path\nSOURCE = Path('D:/reference/ar2_lang2024/S2_ar2_pot.f90')\ndef physics(x): return x*x\n"
    new=relocate('c1b1_o1/model.py',old)
    assert 'D:/' not in new
    assert 'def physics(x): return x*x' in new
    with pytest.raises(ValueError):
        relocate('c1b1_o1/model.py',old.replace('SOURCE =','OTHER ='))


def test_real_package_roundtrip_and_tamper_refusal(tmp_path):
    from tools.c1b1_dt40_package import build,extract,verify
    root=Path(__file__).resolve().parents[1]
    original=root/'runs/c1b1_dt40_integrator_benchmark_20261001_v1/deployment_bundle.tar.gz'
    package=tmp_path/'portable.tar.gz'
    build(root,original,package)
    restored=tmp_path/'restored'
    extract(package,restored)
    result=verify(restored)
    assert result['originals_verified']==272
    assert result['reference_sha256']=='a598057183121b9c928b3a9804c8e2e99afa553bad570a471aa4130f20e6b049'
    assert (restored/'reference/ar2_lang2024/S2_ar2_pot.f90').is_file()
    source=(restored/'code/c1b1_o1/model.py').read_text()
    assert 'D:/' not in source
    assert len(result['location_only_transforms'])==3
    probe = subprocess.run([sys.executable, '-I', '-B', '-c',
        "import sys;sys.path.insert(0,sys.argv[1]);from c1b1_integrator_benchmark.study import load;from c1b1_o1.model import parse;assert len(parse())==14;print(load()['phase_one_case'])",
        str(restored/'code')], cwd=tmp_path, capture_output=True, text=True)
    assert probe.returncode==0,probe.stderr
    assert probe.stdout.strip()=='boundary_pass'
    assert verify(restored)['originals_verified']==272
    related=subprocess.run([sys.executable,'-B','-m','pytest',
        'tests/test_c1b1_integrator_benchmark.py','tests/test_c1b1_o1.py','tests/test_c1b1_o1_diagnostic.py','-q',
        '-p','no:cacheprovider'],cwd=restored/'code',capture_output=True,text=True)
    assert related.returncode==0,related.stdout+related.stderr
    assert '49 passed' in related.stdout
    (restored/'reference/ar2_lang2024/S2_ar2_pot.f90').write_bytes(b'fault')
    with pytest.raises(ValueError,match='hash'):
        verify(restored)


def test_reject_any_nonlocation_ast_mutation():
    from tools.c1b1_dt40_package import check_transform
    a="SOURCE=1\ndef force(x): return -x\n"
    b="SOURCE=2\ndef force(x): return x\n"
    with pytest.raises(ValueError,match='nonlocation'):
        check_transform(a,b,'SOURCE')
