"""Windows Git/source/input seal; execute before numerical construction."""
import argparse
from pathlib import Path
import subprocess
from electronic_pilot.frontend_reference_v0.audit import read,write,sha,verify


def main(main_root,output):
    root=Path.cwd();main_root=Path(main_root);out=Path(output)
    p=read(root/'electronic_pilot/reconstruction_v0/protocol.json')
    def git(*a):return subprocess.check_output(['git',*a],encoding='utf-8').strip()
    state=dict(branch=git('branch','--show-current'),HEAD=git('rev-parse','HEAD'),
               origin_master=git('rev-parse','origin/master'),origin_branch=git('rev-parse','origin/'+p['branch']),
               ahead_behind=git('rev-list','--left-right','--count','HEAD...origin/'+p['branch']),
               dirty=git('diff','--name-only'),untracked=git('ls-files','--others','--exclude-standard'),
               remote=git('ls-remote','origin','refs/heads/master','refs/heads/'+p['branch']))
    if state['HEAD']!=p['base_commit'] or state['branch']!=p['branch'] or state['origin_master']!=p['origin_master'] or state['origin_branch']!=p['base_commit'] or state['dirty']:
        raise ValueError('precondition mismatch '+repr(state))
    if p['base_commit']+'\trefs/heads/'+p['branch'] not in state['remote'] or p['origin_master']+'\trefs/heads/master' not in state['remote']:
        raise ValueError('live remote mismatch')
    inherited=read(root/'docs/active/h2_adversarial_v0/evidence/conditioning_and_symmetry_diagnostic_v0_seal.json')['bound_sha256']
    count=verify(inherited,root,main_root);bindings=dict(inherited)
    for path in git('ls-files','electronic_pilot','tests/*h2*','tests/h2*','docs/active/H2*','docs/active/h2*').splitlines():
        bindings['worktree:'+path]=sha(root/path)
    for folder in ('electronic_pilot/reconstruction_v0','tests/h2_reconstruction_v0'):
        for path in sorted((root/folder).iterdir()):
            if path.is_file():bindings['worktree:'+path.relative_to(root).as_posix()]=sha(path)
    out.mkdir(parents=True,exist_ok=False)
    write(out/'execution_seal.json',dict(Git=state,protocol=p,execution=read(root/'electronic_pilot/reconstruction_v0/execution.json'),
            bound_sha256=bindings,inherited_verified_count=count,numerical_calls_before_seal=0))
    print('SEALED',len(bindings),'inherited',count,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--main',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.main,a.output)
