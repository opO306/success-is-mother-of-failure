"""Portable byte protection; each newly implemented phase is sealed separately."""
import argparse
from pathlib import Path
import subprocess
from electronic_pilot.frontend_reference_v0.audit import read,write,sha,verify


def seal(output,phase,main):
    root=Path.cwd();output=Path(output);output.mkdir(parents=True,exist_ok=True)
    spec=read(root/'electronic_pilot/adversarial_v0/protocol.json')
    def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
    if git('rev-parse','HEAD')!=spec['base_commit'] or git('branch','--show-current')!=spec['branch']:
        raise ValueError('wrong base checkout')
    prior=read(root/'docs/active/h2_frontend_reference_v0/evidence/execution_seal.json')['bound_sha256']
    inherited=verify(prior,root,main);bindings=dict(prior)
    paths=git('ls-files','electronic_pilot','tests/*h2*','tests/h2*','docs/active/H2*','docs/active/h2*').splitlines()
    for name in paths:bindings['worktree:'+name]=sha(root/name)
    for folder in ('electronic_pilot/adversarial_v0','tests/h2_adversarial_v0','runs/h2_adversarial_v0/basis_sources_v0'):
        if not (root/folder).is_dir():continue
        for path in sorted((root/folder).iterdir()):
            if path.is_file():bindings['worktree:'+path.relative_to(root).as_posix()]=sha(path)
    for name in ('docs/active/h2_ground_state_audit_v0/evidence/v_direct_reproduced.npy',
                 'docs/active/h2_ground_state_audit_v0/evidence/direct_state_order.npy'):
        bindings['worktree:'+name]=sha(root/name)
    write(output/(phase+'_seal.json'),dict(spec=spec,phase=phase,bound_sha256=bindings,
         inherited_bindings_checked=inherited,HEAD=git('rev-parse','HEAD'),
         guards=read(root/spec['guards_source'].split(':')[0])['guards'],
         energy_band=read(root/spec['same_basis_energy_band_source'].split(':')[0])['comparison_energy_abs_max_hartree']))
    print('SEALED',phase,len(bindings),'bindings',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--phase',required=True)
    p.add_argument('--main',required=True);a=p.parse_args();seal(a.output,a.phase,a.main)
