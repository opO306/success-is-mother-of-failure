"""Postprocessing only. Package a stopped audit without changing its results."""
import csv
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import time


def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    raw=Path('runs/h2_failure_cause_v0');audit=raw/'audit_v2'
    data=json.loads((audit/'results.json').read_text())
    seal=json.loads((audit/'seal.json').read_text())
    for name,value in (seal['protected_sha256']|seal['source_sha256']|seal['input_sha256']).items():
        if sha(name)!=value: raise ValueError('sealed bytes changed '+name)
    old=json.loads(Path('docs/active/h2_qz44_sealed_v1/results.json').read_text())
    originals={r['R_bohr']:r['paths'][0]['total_energy_hartree'] for r in old['rows']}
    with Path('electronic_pilot/reference_pachucki_v2.csv').open() as f:
        refs={float(r['R_bohr']):r['total_energy_hartree'] for r in csv.DictReader(f)}
    stage_A=data['rows'][0];stage_B=data['rows'][1]
    upper=Fraction(*map(int,stage_A['exact']['exact_upper_squared']))
    nominal=Fraction('1e-10');binary_threshold=Fraction(float(1e-10))
    assert upper<nominal**2 and upper<binary_threshold**2
    candidates=[r for r in data['rows'] if r['stage']=='C1']
    stop=json.loads((raw/'controlled_stop.json').read_text())
    points=[]
    for r in (.4,.6,.7,.8):
        attempted=[x for x in candidates if x['R_bohr']==r]
        points.append(dict(R_bohr=r,our_BO_energy=originals[r],independent_validated_BO_energy=None,
            valid_same_basis_difference=None,physical_reference_error_hartree=str(Decimal(str(originals[r]))-Decimal(refs[r])),
            classification=['UNRESOLVED'],candidate_records=len(attempted),
            first_observed_disagreement_layer='CI Hamiltonian/action on shared frozen MO inputs' if r==.4 else None,
            status='CANDIDATES_INVALID' if r==.4 else 'WORKER_ABORTED_NO_RESULT' if r==.6 else 'NOT_EXECUTED',
            independence=dict(CI='independent determinant action and direct pair construction; candidate validation FAILED',
                              transformation='one shared compact path, one distinct generalized-h/four-leg NumPy path',
                              AO='shared saved canonical binary64 libcint AO; no independent generator',
                              arithmetic='binary64, shared libraries; exact arithmetic only for orthogonality audit')))
    for c in candidates:
        c['candidate_difference_from_our_hartree']=str(Decimal(str(c['BO_energy']))-Decimal(str(c['original_BO_energy'])))
        c['physical_reference_error_hartree']=str(Decimal(str(c['BO_energy']))-Decimal(refs[c['R_bohr']]))
        c['accepted_as_same_basis_reference']=False
    summary=dict(status='PARTIAL_DIAGNOSIS_STOPPED_BY_THREE_FAILURE_RULE',not_certified=True,
        original_QZ44_gate_unchanged='NUMERICAL FAIL; 43 accepted /1 refused; reference-exceeding four points unchanged',
        Stage_A=stage_A,Stage_B=stage_B,Stage_C=points,invalid_C1_candidates=candidates,
        threshold_semantics=dict(nominal_decimal='1e-10',original_binary64_hex=float(1e-10).hex(),
            original_binary64_exact_fraction=str(binary_threshold),exact_upper_below_both=True,
            prototype_uses_nominal_decimal=True,
            caveat='Prototype nominal exact-decimal comparison differs by sub-ulp from binary64 threshold representation at a boundary; no impact on this case, no original guard edits, production boundary semantics not approved'),
        costs=dict(completed_campaign_elapsed_lower_bound_seconds=data['wall_seconds'],
                   observed_seal_to_controlled_stop_seconds=stop['time']-(audit/'seal.json').stat().st_mtime,
                   elapsed_note='Second metric uses filesystem seal mtime and wall-clock stop timestamp, includes aborted R0.6 worker; not a successful full campaign or benchmark',
                   completed_peak_RSS_bytes=max(r['peak_rss_bytes'] for r in data['rows']),
                   additional_dependency='none; existing Python/NumPy/SciPy/PySCF',
                   precision='exact dyadic integers/Fraction for StageA fallback; directed binary64 interval for cheap guard; binary64 C1'),
        unresolved=['Validated short-R same-basis energy reference','Origin of MO pair-interchange error and all-entry/energy bounds',
                    'Original solver vs representation limit','AO generator absolute accuracy in these four geometries',
                    'Adaptive guard production/boundary semantics'],
        C2_executed=False,C3_executed=False,
        stop_rule='AGENTS.md: 3 attempts fail -> stop and report; two preseal infrastructure failures plus invalid C1 diagnostic campaign',
        designer_decision_required='Whether to authorize the next small diagnostic: independent direct-pair singlet matrix with alternate dense LAPACK solver; same inputs/guards, no QZ44 rerun')
    target=Path('docs/active/h2_failure_cause_v0');target.mkdir(exist_ok=False)
    (target/'.gitattributes').write_text('* -text\n')
    (target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for source in audit.glob('*.json'): shutil.copyfile(source,target/source.name)
    for source in raw.glob('*.json'): shutil.copyfile(source,target/source.name)
    for source in raw.glob('*.log'): shutil.copyfile(source,target/source.name)
    for source in Path('electronic_pilot/failure_cause_v0').glob('*'):
        if source.is_file(): shutil.copyfile(source,target/(source.name+'.txt'))
    for source in (Path(__file__),Path('tests/test_h2_failure_cause_v0.py')):
        shutil.copyfile(source,target/(source.name+'.txt'))
    originals_checked={}
    original_root=Path(seal['evidence_root']).parent.parent.parent
    for folder in ('h2_static_pilot_v2','h2_numerical_cause_v1','h2_ao_micro_v0','h2_qz44_sealed_v1'):
        manifest=json.loads((Path('docs/active')/folder/'raw_manifest.json').read_text())
        for name,value in manifest.items():
            path=original_root/Path(name.replace('\\','/'))
            if sha(path)!=value['sha256']: raise ValueError('original raw changed '+str(path))
        originals_checked[folder]=len(manifest)
    preservation=dict(protected_count=len(seal['protected_sha256']),source_count=len(seal['source_sha256']),
        input_count=len(seal['input_sha256']),original_raw_checked=originals_checked,
        original_raw_changed=[],old_QZ44_gate_sha256=sha('docs/active/h2_qz44_sealed_v1/gate.json'),
        original_QZ44_results_sha256=sha('docs/active/h2_qz44_sealed_v1/results.json'),
        postprocessor_sha256=sha(__file__))
    (target/'preservation.json').write_text(json.dumps(preservation,indent=2)+'\n')
    manifest={str(p):dict(sha256=sha(p),bytes=p.stat().st_size) for p in raw.rglob('*') if p.is_file()}
    (target/'raw_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(protected=preservation['protected_count'],old_raw=originals_checked,
                         raw_count=len(manifest),summary_status=summary['status']),indent=2))

if __name__=='__main__': main()
