"""Postprocess and package actual evidence; never invoke a physical evaluator."""
from pathlib import Path
from decimal import Decimal
import shutil
import numpy as np
from electronic_pilot.frontend_reference_v0.audit import read,write,sha,verify

ROOT=Path('runs/h2_adversarial_v0')
DEST=Path('docs/active/h2_adversarial_v0/evidence')

def main():
    DEST.mkdir(parents=True,exist_ok=False)
    latest=read(ROOT/'seals/conditioning_and_symmetry_diagnostic_v0_seal.json')
    count=verify(latest['bound_sha256'],Path.cwd(),Path('C:/Users/zun24/성공은 실패의 어머니'))
    cardinal={name:read(ROOT/('cardinal_v0/'+name+'/result.json')) for name in ('DZ','TZ','QZ','V5Z','uncontracted_QZ')}
    spectrum={name:np.load(ROOT/('cardinal_v0/'+name+'/overlap_spectrum.npy')).tolist() for name in cardinal}
    original=read('C:/Users/zun24/성공은 실패의 어머니/runs/h2_qz44_sealed_v1/curve/R_0.4.json')['paths'][0]
    qz=cardinal['QZ'];bit_equal=qz['electronic_energy_hartree'].hex()==original['electronic_energy_hartree'].hex()
    definition=read(ROOT/'definitions_v1/basis_definitions.json')
    maxnorm=max(sh['normalization_max_relative'] for row in definition['records'].values() for sh in row['actual_shells'])
    summary=dict(cardinal=cardinal,overlap_spectra=spectrum,QZ_replay_energy_bitwise_equal=bit_equal,
      QZ_electronic_energy_hex=qz['electronic_energy_hartree'].hex(),maximum_radial_norm_relative_difference=maxnorm,
      basis_span_check_arithmetic='exact rational on supplied binary64 coefficients/exponent identities; not exact real integral certification',
      phase_bindings_verified=count,reference_status='REFERENCE_SIDE_UNRESOLVED',strict_state_irrep_status='UNRESOLVED',
      QZ44_status='FAIL unchanged',MO_pair_interchange_status='UNRESOLVED',certification='NOT CERTIFIED',
      finite_basis_evidence='SUPPORTED UNDER CHECKED ASSUMPTIONS: observed four-point cardinal trend, not a proven error decomposition')
    write(DEST/'summary.json',summary)
    copies={'symmetry.json':'symmetry_v0/symmetry.json','symmetry_diagnostic.json':'symmetry_diagnostic_v0/diagnostic.json',
       'basis_definitions.json':'definitions_v1/basis_definitions.json','initial_column_refusal.json':'definitions_v0/cc-pVDZ_MISMATCH.json',
       'AO_comparison.json':'libint_v0/AO_comparison.json','native_execution_seal.json':'libint_v0/execution_seal.json',
       'native_input_seal.json':'libint_v0/input_seal.json','native_postcheck.json':'libint_v0/postcheck.json',
       'factorial.json':'factorial_v0/summary.json','factorial_input_seal.json':'factorial_v0/input_seal.json',
       'factorial_postcheck.json':'factorial_v0/postcheck.json','conditioning.json':'conditioning_v0/diagnostic.json',
       'symmetry_input_seal.json':'seals/symmetry_input_seal.json','symmetry_postcheck.json':'seals/symmetry_input_postcheck.json',
       'symmetry_diagnostic_input_seal.json':'symmetry_diagnostic_v0/input_seal.json',
       'cardinal_execution_inputs.json':'seals/cardinal_execution_inputs.json','runtime_postrun.json':'runtime_observed_postrun.json',
       'reference_acquisition_v1.json':'reference_acquisition_v1/sources.json','reference_initial_failure.log':'reference_acquisition_v0.log',
       'initial_collection_failure.log':'algebra_tests_v0.log','initial_definition_failure.log':'definitions_v0.log',
       'native_compile.log':'libint_compile_v0.log','native.log':'libint_v0/native.log',
       'Ndeke_R04_row.png':'reference_acquisition_v1/Ndeke_R04_row.png',
       'diagnostic_even_projected_vector.npy':'symmetry_diagnostic_v0/diagnostic_even_projected_vector.npy'}
    for label,row in cardinal.items():
        copies[label+'_input_seal.json']='cardinal_v0/'+label+'/input_seal.json'
        copies[label+'_postcheck.json']='cardinal_v0/'+label+'/postcheck.json'
    for p in (ROOT/'seals').glob('*_seal.json'):copies[p.name]='seals/'+p.name
    for new,old in copies.items():shutil.copyfile(ROOT/old,DEST/new)
    raw={}
    for sub in ('cardinal_v0','libint_v0','factorial_v0','symmetry_v0','symmetry_diagnostic_v0','conditioning_v0','reference_acquisition_v1'):
        for path in sorted((ROOT/sub).rglob('*')):
            if path.is_file():raw[path.as_posix()]=dict(bytes=path.stat().st_size,sha256=sha(path))
    write(DEST/'raw_inventory.json',dict(files=raw,large_arrays_kept_outside_Git=True,
        native_executable_task_local='/home/otherside123/h2-adversarial-v0/libint_driver',
        native_dependencies_task_local='/home/otherside123/h2-adversarial-v0/deps'))
    write(DEST/'preservation.json',dict(unchanged=True,bindings_checked=count,source_seal='conditioning_and_symmetry_diagnostic_v0_seal.json'))
    print('PACKAGED',len(raw),'raw artifacts; preserved',count,'bindings',flush=True)

if __name__=='__main__':main()
