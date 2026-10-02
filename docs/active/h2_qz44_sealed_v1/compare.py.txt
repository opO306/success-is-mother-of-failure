"""Independent record/reference decision; stdlib, no evaluator imports."""
import argparse
import csv
import hashlib
import json
import math
from decimal import Decimal as D
from pathlib import Path
from electronic_pilot.check_reference import compare as original_compare


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(rows,reference,controls,grid,guards,criteria,control_max,explicit_control):
    expected={D(str(r)) for r in grid}
    got=[D(str(x['R_bohr'])) for x in rows]
    if len(rows)!=44 or len(got)!=len(set(got)) or set(got)!=expected: raise ValueError('fresh grid incomplete/duplicate/changed')
    table={D(x['R_bohr']):D(x['total_energy_hartree']) for x in reference}
    if len(reference)!=44 or set(table)!=expected: raise ValueError('reference coverage mismatch')
    by_r={D(str(x['R_bohr'])):x['paths'][0] for x in rows}
    failures={};errors=[]
    for outer in rows:
        r=D(str(outer['R_bohr']));row=outer['paths'][0]
        if row['basis_size']!=60 or row['singlet_dimension']!=1830 or row['basis']!='cc-pVQZ' or row['electrons']!=2 or row['sector']!='singlet': raise ValueError('dimension/physics record mismatch')
        if not outer['source_seal_valid'] or not outer['AO']['lower_representatives_match_raw']: raise ValueError('canonical source/provenance mismatch')
        if not row['accepted']:
            failures.setdefault(str(r),[]).append('REFUSED: '+row['failure_stage'])
            continue
        vals=[row[k] for k in ('total_energy_hartree','electronic_energy_hartree','nuclear_repulsion_hartree','orthogonality_l2','singlet_asymmetry','eigen_residual_l2','vector_norm_error','Smin')]
        if not all(math.isfinite(x) for x in vals): raise ValueError('nonfinite accepted record')
        if not (row['Smin']>guards['Smin_floor'] and row['orthogonality_l2']<=guards['orth_l2_max'] and row['singlet_asymmetry']<=guards['H_asym_max'] and row['eigen_residual_l2']<=guards['eigen_l2_max'] and row['vector_norm_error']<=guards['norm_max']): raise ValueError('accepted record violates original guards')
        error=D(str(row['total_energy_hartree']))-table[r]
        ok=abs(error)<=D(str(criteria['P3_curve_max_abs_error_hartree']))
        errors.append(dict(R_bohr=float(r),signed_error_hartree=str(error),within_original_reference_criterion=ok))
        if not ok: failures.setdefault(str(r),[]).append('REFERENCE_ERROR_EXCEEDS_0.001_HARTREE')
    comparisons=[]
    controls=controls+[dict(source='explicit original R=1.4 control',R_bohr=1.4,total_energy_hartree=explicit_control)]
    for old in controls:
        r=D(str(old['R_bohr']));new=by_r[r]
        diff=D(str(new['total_energy_hartree']))-D(str(old['total_energy_hartree'])) if new['accepted'] else None
        ok=diff is not None and abs(diff)<=D(str(control_max))
        comparisons.append(dict(source=old['source'],R_bohr=float(r),difference_hartree=str(diff) if diff is not None else None,consistent=ok))
        if not ok: failures.setdefault(str(r),[]).append('PREVIOUS_ACCEPTED_CONTROL_DISAGREEMENT')
    accepted=sum(x['paths'][0]['accepted'] for x in rows)
    passed=accepted==44 and not failures
    return dict(gate='H₂ STATIC QZ 44-POINT REFERENCE-COMPARISON GATE = '+('NUMERICAL PASS' if passed else 'NUMERICAL FAIL'),
        numerical_pass=passed,attempted=44,accepted=accepted,refused=44-accepted,pointwise_reference=errors,
        reference_exceeding_R_bohr=[x['R_bohr'] for x in errors if not x['within_original_reference_criterion']],
        previous_accepted_comparisons=comparisons,control_inconsistency_count=sum(not x['consistent'] for x in comparisons),
        max_control_abs_difference_hartree=max((abs(D(x['difference_hartree'])) for x in comparisons if x['difference_hartree'] is not None),default=D(0)).__str__(),
        failed_points=[dict(R_bohr=float(r),reasons=reasons) for r,reasons in sorted(failures.items(),key=lambda x:D(x[0]))],
        reference_threshold_hartree=criteria['P3_curve_max_abs_error_hartree'],control_threshold_hartree=control_max,
        unresolved=['MO ERI pair-interchange accuracy','all solver/integral accuracy','formal certification','production foundation approval'],
        not_certified=True)


def control_records(spec):
    records=[]
    for name in spec['controls']:
        data=json.loads(Path(name).read_text())
        for outer in data['rows']:
            if 'paths' in outer:
                row=outer['paths'][0]
                if outer['basis']=='cc-pVQZ' and row['accepted']:
                    records.append(dict(source=name,R_bohr=outer['R_bohr'],total_energy_hartree=row['total_energy_hartree']))
            elif outer.get('kind')=='curve' and outer['basis']=='cc-pVQZ':
                records.append(dict(source=name,R_bohr=outer['R_bohr'],total_energy_hartree=outer['total_energy_hartree']))
    return records


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);args=p.parse_args();root=Path(args.root)
    seal=json.loads((root/'seal.json').read_text());check=json.loads((root/'post_run_seal_check.json').read_text())
    bound=seal['frozen_sha256']|seal['extension_sha256']
    if any(digest(name)!=h for name,h in bound.items()): raise ValueError('seal drift before comparison')
    if digest(root/'results.json')!=check['results_sha256'] or not check['verified']: raise ValueError('fresh results seal mismatch')
    data=json.loads((root/'results.json').read_text());spec=seal['spec']
    with Path(spec['reference_source']).open(newline='') as f: reference=list(csv.DictReader(f))
    numeric=json.loads(Path(spec['numerical_config_source']).read_text())
    parent=json.loads(Path(spec['grid_source']).read_text())
    verdict=assess(data['rows'],reference,control_records(spec),seal['R_grid_bohr'],numeric['guards'],parent['criteria'],numeric['control_energy_max_difference'],numeric['control_EBO'])
    # Existing checker receives fresh curve energies only. The old QZ atomic
    # reference is a disclosed postprocessing input, not a new molecular solve.
    atoms=[x for x in json.loads(Path(spec['controls'][0]).read_text())['rows'] if x.get('kind')=='atom' and x['basis']=='cc-pVQZ']
    records=atoms.copy()
    for outer in data['rows']:
        row=outer['paths'][0]
        if row['accepted']: records.append(dict(row,process_peak_rss_bytes=outer['peak_rss_bytes']))
        else: records.append(dict(status='FAILED_PRESERVED',job=dict(kind='curve',basis='cc-pVQZ',R=outer['R_bohr']),error='REFUSED: '+row['failure_stage']))
    comparison=original_compare(dict(rows=records),dict(parent,bases=['cc-pVQZ']),reference)
    target=root/'comparison';target.mkdir(exist_ok=False)
    (target/'seal.json').write_text(json.dumps(dict(checker_sha256=digest(spec['reference_checker']),decision_sha256=digest(__file__),criteria=parent['criteria'],fresh_results_sha256=digest(root/'results.json'),reference_sha256=digest(spec['reference_source']),atomic_reference_source=spec['controls'][0]),indent=2)+'\n')
    (target/'checker_records.json').write_text(json.dumps(dict(rows=records),indent=2)+'\n')
    (target/'reference_comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    (target/'gate.json').write_text(json.dumps(verdict,indent=2)+'\n')
    print(verdict['gate'],verdict['accepted'],'accepted',verdict['refused'],'refused',verdict['failed_points'])
    print(json.dumps(comparison['summaries'],indent=2))

if __name__=='__main__': main()
