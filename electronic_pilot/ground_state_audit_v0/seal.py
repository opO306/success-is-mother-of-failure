"""Windows-side pre-execution seal; hash historic bytes without running CI."""
import argparse
import subprocess
from pathlib import Path
from .io import sha, read, write, verify


def git(*args):
    return subprocess.check_output(['git', *args], encoding='utf-8').strip()


def prepare(root, main, output):
    root, main, output = Path(root).resolve(), Path(main).resolve(), Path(output)
    spec = read(root/'electronic_pilot/ground_state_audit_v0/protocol.json')
    state = dict(branch=git('branch', '--show-current'), HEAD=git('rev-parse', 'HEAD'),
                 origin_master=git('rev-parse', 'origin/master'),
                 origin_branch=git('rev-parse', 'origin/'+spec['branch']),
                 ahead_behind=git('rev-list', '--left-right', '--count', 'HEAD...origin/'+spec['branch']),
                 dirty_tracked=git('diff', '--name-only'), untracked=git('ls-files', '--others', '--exclude-standard'))
    if (state['branch'] != spec['branch'] or state['HEAD'] != spec['base_commit'] or
        state['origin_master'] != spec['origin_master'] or state['origin_branch'] != spec['base_commit'] or state['dirty_tracked']):
        raise ValueError('Git precondition mismatch: '+repr(state))
    old = read(root/'runs/h2_ci_layer_audit_v0/audit_v0/execution_seal.json')
    bindings = {}
    for key, expected in old['bound_sha256'].items():
        if key.startswith('/mnt/c/'):
            path = Path('C:/'+key[7:])
            try:
                label = 'worktree:'+path.relative_to(root).as_posix()
            except ValueError:
                label = 'main:'+path.relative_to(main).as_posix()
        else:
            label = 'worktree:'+Path(key).as_posix()
        bindings[label] = expected
    inherited_count = verify(bindings, root, main)
    protected = git('ls-files', 'electronic_pilot', 'tests/test_h2*', 'docs/active/h2*').splitlines()
    for path in protected:
        bindings['worktree:'+path] = sha(root/path)
    for path in sorted((root/'runs/h2_ci_layer_audit_v0/audit_v0').iterdir()):
        if path.is_file():
            bindings['worktree:'+path.relative_to(root).as_posix()] = sha(path)
    source_paths = sorted((root/'electronic_pilot/ground_state_audit_v0').glob('*.py'))
    source_paths += sorted((root/'electronic_pilot/ground_state_audit_v0').glob('*.json'))
    source_paths += [root/'electronic_pilot/ground_state_audit_v0/DERIVATION.md']
    source_paths += sorted((root/'tests/h2_ground_state_audit_v0').glob('*.py'))
    for path in source_paths:
        bindings['worktree:'+path.relative_to(root).as_posix()] = sha(path)
    builder = root/'electronic_pilot/solver.py'
    historic = root/'docs/active/h2_qz44_sealed_v1/frozen_source/electronic_pilot__solver.py.txt'
    if sha(builder) != sha(historic):
        raise ValueError('historical direct-pair source bytes mismatch')
    archived = read(main/'runs/h2_qz44_sealed_v1/curve/R_0.4.json')['paths'][0]
    guards = read(root/spec['guards_source'].split(':')[0])['guards']
    energy_band = read(root/spec['energy_agreement_source'].split(':')[0])['comparison_energy_abs_max_hartree']
    output.mkdir(parents=True, exist_ok=False)
    write(output/'execution_seal.json', dict(spec=spec, Git=state, bound_sha256=bindings,
          inherited_bindings_checked=inherited_count, guards=guards, energy_agreement=energy_band,
          builder_sha256=sha(builder), archived_direct=archived,
          authorization='Human authorized exact sealed replay export after disclosure of missing archived vector; bitwise E required',
          original_npz_keys=['s', 'h', 'eri_s8', 'c']))
    print('SEALED', len(bindings), 'bindings; inherited', inherited_count, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--main', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    prepare(Path.cwd(), args.main, args.output)
