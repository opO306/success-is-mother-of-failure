"""Compact whole-grid evidence, streamed manifests and row-level CSV."""
import csv
import json
import shutil
from pathlib import Path
from .seal import sha,verify


def main():
    root=Path('runs/h2_qz44_sealed_v1');curve=root/'curve'
    seal=json.loads((curve/'seal.json').read_text())
    verify(seal['frozen_sha256']|seal['extension_sha256'])
    data=json.loads((curve/'results.json').read_text())
    historical={}
    for name in ('h2_static_pilot_v2','h2_numerical_cause_v1','h2_ao_micro_v0'):
        manifest=Path('docs/active')/name/'raw_manifest.json';records=json.loads(manifest.read_text())
        bad=[]
        for file,record in records.items():
            path=Path(file.replace('\\','/'))
            if not path.exists() or sha(path)!=record['sha256']: bad.append(file)
        if bad: raise ValueError(f'historical raw evidence drift: {bad}')
        historical[name]=dict(checked=len(records),manifest_sha256=sha(manifest),changed=[])
    for row in data['rows']:
        path=curve/f"R_{row['R_bohr']:g}.npz"
        if sha(path)!=row['artifact_sha256']: raise ValueError(f'new artifact mismatch: {path}')
    target=Path('docs/active/h2_qz44_sealed_v1');target.mkdir(exist_ok=False)
    (target/'.gitattributes').write_text('* -text\n')
    for src,dest in (('curve/seal.json','execution_seal.json'),('curve/results.json','results.json'),('curve/post_run_seal_check.json','post_run_seal_check.json'),
        ('curve/comparison/seal.json','comparison_seal.json'),('curve/comparison/gate.json','gate.json'),('curve/comparison/reference_comparison.json','reference_comparison.json'),
        ('curve/comparison/checker_records.json','checker_records.json'),('curve/failure_diagnostic/seal.json','failure_diagnostic_seal.json'),
        ('curve/failure_diagnostic/results.json','failure_diagnostic_results.json'),('curve_console.log','curve_console.log'),
        ('comparison_console.log','comparison_console.log'),('failure_diagnostic_console.log','failure_diagnostic_console.log'),
        ('tests_preflight_windows.log','tests_preflight_windows.log'),('tests_windows_final.log','tests_windows_final.log'),('tests_wsl_final.log','tests_wsl_final.log'),
        ('tests_diagnostic_wsl.log','tests_diagnostic_wsl.log'),('preflight_failure_v0/failure.json','preflight_failure.json'),('preflight_failure_v0/test_executed.py.txt','preflight_test_executed.py.txt')):
        shutil.copyfile(root/src,target/dest)
    snapshots=target/'frozen_source';snapshots.mkdir()
    for source in (curve/'source_snapshots').iterdir(): shutil.copyfile(source,snapshots/source.name)
    for source in Path(__file__).parent.iterdir():
        if source.is_file(): shutil.copyfile(source,target/(source.name+'.txt'))
    for source in ('tests/test_h2_qz44_sealed_v1.py','tests/test_h2_qz44_failure_diagnostic.py'):
        shutil.copyfile(source,target/(Path(source).name+'.txt'))
    gate=json.loads((curve/'comparison/gate.json').read_text())
    errors={x['R_bohr']:x for x in gate['pointwise_reference']}
    columns=['R_bohr','accepted','failure_stage','BO_energy_hartree','orthogonality_l2','H_asymmetry','eigen_residual_l2',
        'MO_ERI_pair_interchange_residual','Smin','condition','worker_wall_seconds','worker_wall_with_startup_seconds','peak_rss_bytes','reference_error_hartree','reference_criterion_pass']
    with (target/'points.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for row in data['rows']:
            x=row['paths'][0];error=errors.get(row['R_bohr'],{})
            writer.writerow(dict(R_bohr=row['R_bohr'],accepted=x['accepted'],failure_stage=x['failure_stage'],BO_energy_hartree=x['total_energy_hartree'],
                orthogonality_l2=x['orthogonality_l2'],H_asymmetry=x['singlet_asymmetry'],eigen_residual_l2=x['eigen_residual_l2'],
                MO_ERI_pair_interchange_residual=x['transformed_ERI_symmetry']['pair_swap_max'],Smin=x['Smin'],condition=x['condition'],
                worker_wall_seconds=row['wall_seconds'],worker_wall_with_startup_seconds=row['worker_wall_with_startup_seconds'],peak_rss_bytes=row['peak_rss_bytes'],
                reference_error_hartree=error.get('signed_error_hartree'),reference_criterion_pass=error.get('within_original_reference_criterion')))
    (target/'preservation.json').write_text(json.dumps(dict(historical=historical,new_NPZ_verified=len(data['rows']),frozen_base_files=len(seal['frozen_sha256']),
        source_sha256={str(p):sha(p) for p in Path(__file__).parent.glob('*') if p.is_file()},
        test_sha256={p:sha(p) for p in ('tests/test_h2_qz44_sealed_v1.py','tests/test_h2_qz44_failure_diagnostic.py')}),indent=2)+'\n')
    manifest={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in root.rglob('*') if p.is_file()}
    (target/'raw_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(historical=historical,raw_count=len(manifest),new_NPZ_verified=44,frozen_files=len(seal['frozen_sha256'])),indent=2))

if __name__=='__main__': main()
