"""Post-calculation evidence and local bracket; outside the executor."""
import argparse
import hashlib
import json
from pathlib import Path
import mpmath as mp
import numpy as np


def assess(rows,old_right,spec):
    by_r={x['R_bohr']:x['paths'][0] for x in rows}
    if set(by_r)!=set(spec['R_bohr']): raise ValueError('incomplete four-point panel')
    control=by_r[1.4]
    difference=control['total_energy_hartree']-spec['control_EBO'] if control['accepted'] else None
    equivalence=(all(x['basis_size']==60 and x['singlet_dimension']==1830 for x in by_r.values()) and
                 control['accepted'] and abs(difference)<=spec['control_energy_max_difference'])
    three=by_r[1.3]['accepted'] and control['accepted'] and old_right['accepted']
    left_gap=by_r[1.3]['total_energy_hartree']-control['total_energy_hartree'] if three else None
    right_gap=old_right['total_energy_hartree']-control['total_energy_hartree'] if three else None
    bracket=equivalence and three and left_gap>0 and right_gap>0
    return dict(control_difference_hartree=difference,same_physics_numerical_path_supported=equivalence,
        local_minimum_resolved=bracket,local_minimum_R_bohr=1.4 if bracket else None,
        left_gap_hartree=left_gap,right_gap_hartree=right_gap,
        stop_without_expansion=bool(three and left_gap<=0),
        status='QZ LOCAL MINIMUM RESOLVED' if bracket else 'UNRESOLVED',
        not_certified=True,whole_curve_recomputed=False)


def exact_class(data,artifact):
    with np.load(artifact) as arrays: c=arrays['c']
    with mp.workdps(80):
        cc=[[mp.mpf(float(x)) for x in row] for row in c]
        i,j=data['worst_coupling']['pair_a'];k,l=data['worst_coupling']['pair_b']
        norm=mp.sqrt(2*(1+(i==j)))*mp.sqrt(2*(1+(k==l)))
        items={tuple(x['indices']):mp.mpf(x['value']) for x in data['ERI_class']['raw_values']}
        total=mp.mpf(0)
        for (p,q,r,s),value in items.items():
            weight=mp.fsum(cc[p][a]*cc[q][b]*cc[r][u]*cc[s][v] for a,b,u,v in ((i,k,j,l),(i,l,j,k),(j,k,i,l),(j,l,i,k)))/norm
            total+=weight*(value-items[(q,p,s,r)])
        return mp.nstr(total,80)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--suffix',default='');args=p.parse_args();root=Path(args.root)
    spec=json.loads(Path(__file__).with_name('protocol.json').read_text())
    stages={name:json.loads((root/(name+args.suffix if name in ('B','C') else name)/'results.json').read_text()) for name in ('selection','spot','B','C')}
    old_source=Path('runs/h2_numerical_cause_v1/qz_curve/results.json')
    old_row=next(x for x in json.loads(old_source.read_text())['rows'] if x['R_bohr']==1.5)
    assessment=assess(stages['C']['rows'],old_row['paths'][0],spec)
    assessment.update(numerical_cause_supported=stages['spot']['stage_B_gate_supported'],
        old_right_R_bohr=1.5,old_right_energy=old_row['paths'][0]['total_energy_hartree'],
        old_right_provenance=dict(path=str(old_source),sha256=hashlib.sha256(old_source.read_bytes()).hexdigest(),accepted=True),
        Stage_A_class_80digit={str(x['R_bohr']):exact_class(x,root/'selection'/f"R_{x['R_bohr']:g}.npz") for x in stages['selection']['rows']},
        wall_seconds={name:stage['wall_seconds'] for name,stage in stages.items()},
        stage_C_max_rss_bytes=max(x['peak_rss_bytes'] for x in stages['C']['rows']),
        narrow_scope='Only the four authorized QZ geometries. Archived 1.5 used only in post-analysis. No physical reference in evaluator.',
        unresolved='MO ERI pair-interchange roundoff remains. Small H/eigen residual is not a rigorous forward energy error or formal certificate.')
    protected=json.loads((root/'selection/seal.json').read_text())['protected']
    changed=[str(name) for name,sha in protected.items() if not Path(name).exists() or hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha]
    if changed: raise ValueError(f'protected files changed: {changed}')
    artifacts={}
    for stage in ('selection','B','C'):
        for row in stages[stage]['rows']:
            artifact=root/(stage+args.suffix if stage in ('B','C') else stage)/f"R_{row['R_bohr']:g}.npz"
            sha=hashlib.sha256(artifact.read_bytes()).hexdigest()
            if sha!=row['artifact_sha256']: raise ValueError(f'bad artifact: {artifact}')
            artifacts[str(artifact)]=sha
    assessment['preservation']=dict(protected_count=len(protected),changed=[],verified_npz=artifacts)
    target=root/('analysis'+args.suffix);target.mkdir(exist_ok=False)
    (target/'summary.json').write_text(json.dumps(assessment,indent=2)+'\n')
    print(json.dumps({k:v for k,v in assessment.items() if k not in ('Stage_A_class_80digit','preservation')},indent=2))

if __name__=='__main__': main()
