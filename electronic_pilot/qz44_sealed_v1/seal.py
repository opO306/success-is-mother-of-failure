"""Byte binding to the requested commit and pre-run canonical configuration."""
import hashlib
import json
import subprocess
from pathlib import Path

BASE='0e9e454246d700efd0303c59eb9120ef9bc78f2e'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def verify(mapping):
    changed=[name for name,value in mapping.items() if not Path(name).is_file() or sha(name)!=value]
    if changed: raise ValueError(f'SOURCE/CONFIG SEAL DRIFT: {changed}')


def make_seal(root):
    spec=json.loads(Path(__file__).with_name('protocol.json').read_text())
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    if head!=BASE or branch!=spec['expected_branch']: raise ValueError('unexpected pre-run Git base/branch')
    owned=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'electronic_pilot','tests/test_h2_static_pilot.py','tests/test_h2_numerical_cause.py','tests/test_h2_ao_micro_v0.py','docs/active/h2_static_pilot_v2','docs/active/h2_numerical_cause_v1','docs/active/h2_ao_micro_v0'],text=True).splitlines()
    frozen={}
    for name in owned:
        expected=hashlib.sha256(subprocess.check_output(['git','show',BASE+':'+name])).hexdigest()
        if sha(name)!=expected: raise ValueError(f'file differs from requested commit: {name}')
        frozen[name]=expected
    extension={str(p):sha(p) for p in Path('electronic_pilot/qz44_sealed_v1').iterdir() if p.is_file()}
    extension['tests/test_h2_qz44_sealed_v1.py']=sha('tests/test_h2_qz44_sealed_v1.py')
    numeric=json.loads(Path(spec['numerical_config_source']).read_text())
    parent=json.loads(Path(spec['grid_source']).read_text())
    grid=parent['R_grid_bohr']
    if len(grid)!=44 or len(set(grid))!=44: raise ValueError('wrong original grid')
    if numeric['guards']!=dict(Smin_floor=1e-10,orth_l2_max=1e-10,H_asym_max=1e-10,eigen_l2_max=1e-9,norm_max=1e-10): raise ValueError('guard mismatch')
    if parent['criteria']['P3_curve_max_abs_error_hartree']!=.001: raise ValueError('reference criterion mismatch')
    from pyscf import gto
    import numpy,scipy,pyscf,sys,os
    runtime_files={}
    for module in (gto.mole,gto.moleintor,numpy,scipy,pyscf):
        runtime_files[module.__file__]=sha(module.__file__)
    for library in Path(pyscf.__file__).parent.joinpath('lib').rglob('*.so'):
        runtime_files[str(library)]=sha(library)
    for module in (numpy,scipy):
        libraries=Path(module.__file__).parent.parent/(module.__name__+'.libs')
        for p in libraries.glob('*'):
            if p.is_file(): runtime_files[str(p)]=sha(p)
    env={name:os.environ.get(name) for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}
    if any(v!='1' for v in env.values()): raise ValueError('thread environment differs from V0')
    sources=root/'source_snapshots';sources.mkdir()
    for name in ('electronic_pilot/ao_micro_v0/reuse.py','electronic_pilot/numerical_cause/core.py','electronic_pilot/solver.py',spec['numerical_config_source'],spec['grid_source'],spec['reference_source'],spec['reference_checker']):
        (sources/(name.replace('/','__')+'.txt')).write_bytes(Path(name).read_bytes())
    seal=dict(spec=spec,base_commit=head,branch=branch,frozen_sha256=frozen,extension_sha256=extension,
        runtime_sha256=runtime_files,thread_environment=env,python=sys.version,
        packages=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),
        R_grid_bohr=grid,numerical_guards=numeric['guards'],canonical_rule=numeric['canonical_rule'],
        original_reference_criteria=parent['criteria'],H_basis_data=gto.basis.load('cc-pVQZ','H'),
        caveat='Frozen binary64 finite-basis numerical path; reference comparison does not certify MO integrals or solver correctness.')
    (root/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    return seal
