"""Separate reference consumer; execute only after B1 energy/hash sealing."""
import argparse,json,time
from fractions import Fraction as F
from pathlib import Path
from .run import RAW,DOC,read,verify,check_seal,energy
from .measure import timed
from electronic_pilot.h2_stored_root_v1 import checker as ck

REFERENCE=F('-0.120230341178823')
TARGET=F('0.001')
PARENT=Path('C:/Users/zun24/.codex/worktrees/h2-qz-cause-v0/성공은 실패의 어머니')
DEFINITIONS=PARENT/'runs/h2_adversarial_v0/definitions_v1/basis_definitions.json'
GAUSSIAN_BINDINGS={
    'electronic_pilot/adversarial_v0/cardinal.py':'0f5861d1127d023d657f8f06c1d8b212dd77f62365076f6864815d4abfa425b8',
    'electronic_pilot/ao_micro_v0/reuse.py':'d3a9db91303df54ccca7172c83ca8ce0bfe9ccd6a79c99071e4e4fe47ecd25f3',
    'electronic_pilot/numerical_cause/core.py':'8432d2e5023c846c5af3fba38993b81cc5ac564efff5b7f5befad79838db950a',
    'electronic_pilot/solver.py':'af4448202196910949f9f0c60241a8d96d6b119d7c6c4115a9e5847c656786ac',
    'electronic_pilot/ao_micro_v0/protocol.json':'02229a1a0a9e587d36b1626debdb75de31c8008badafe9752ec21a47cbfa01e7'}
GAUSSIAN_BINDINGS[DEFINITIONS.as_posix()]='c5244d1e10250aabaccd091d96fa2c2d0c66316d62fb8507f968c69caae6ec5c'

def reference_gate():
    check_seal();seal=read(DOC/'evidence/energy_seal.json');verify(seal['bound_sha256'])
    if not seal['all_B1_energies_before_reference'] or seal['status']!='R04_FINITE_CAMPAIGN_ACCEPTED':
        raise ValueError('unaccepted/unsealed B1 campaign; no reference comparison or fresh Gaussian')
    return read(DOC/'evidence/campaign.json')

def compare():
    campaign=reference_gate();dest=DOC/'evidence/reference_comparison.json'
    if dest.exists():raise ValueError('exclusive reference comparison')
    final=campaign['final'];rows=[]
    for size in ('SMALL','MEDIUM','LARGE'):
        gap=abs(energy(final[size])-REFERENCE)
        rows.append(dict(size=size,energy=final[size]['energy'],absolute_gap=ck.decimal(gap,80),target_met=gap<=TARGET))
    first=next((r['size'] for r in rows if r['target_met']),None)
    result=dict(energy_seal_sha256=ck.sha(DOC/'evidence/energy_seal.json'),reference=str(float(REFERENCE)),
        reference_exact_decimal='-0.120230341178823',reference_authority='designer supplied fixed comparison value; no fitting',
        criterion='absolute gap <= 0.001 Eh',points=rows,first_target_meeting=first,
        target_status='R04_TARGET_ACCURACY_MET' if first else 'R04_TARGET_ACCURACY_NOT_MET',
        historical=dict(QZ='-0.11803113362157003',V5Z='-0.11959699456988826'),
        NOT_CERTIFIED=True,NOT_PRODUCTION_APPROVED=True)
    ck.write(dest,result)
    if first:
        verify(GAUSSIAN_BINDINGS)
        process=RAW/'gaussian_V5Z_measurement';output=RAW/'gaussian_V5Z_output'
        if process.exists() or output.exists():raise ValueError('do not repeat Gaussian benchmark')
        start=time.perf_counter()
        argv=['/bin/sh','-c','cd "$1" && exec "$2" -m electronic_pilot.adversarial_v0.cardinal --basis cc-pV5Z --output "$3" --definitions "$4"',
              'r04gaussian',ck.linux(Path.cwd()),'/home/otherside123/.venvs/h2-reference-pilot/bin/python',ck.linux(output),ck.linux(DEFINITIONS)]
        measurement=timed(argv,process,timeout=300);fresh=read(output/'result.json');post=read(output/'postcheck.json')
        verify(GAUSSIAN_BINDINGS)
        if not fresh['accepted'] or not post['unchanged']:raise ValueError('fresh Gaussian guard/postcheck failure')
        benchmark=dict(physical_basis_guards_unchanged=True,bindings=GAUSSIAN_BINDINGS,measurement=measurement,
                       total_benchmark_wall_seconds=time.perf_counter()-start,fresh_result=fresh,
                       historical_energy_preserved='-0.11959699456988826',result_sha256=ck.sha(output/'result.json'),
                       B1_first_target=first,B1_full_cost_through_first_target_seconds=campaign['cumulative_final_wall_seconds'][first],
                       B1_cost_includes='calibration, own parameter search, refused/retry attempts, native capture, interval validation, higher NMAX spot, unmodified vendor comparison',
                       comparability='same host and wrapper/one-thread env; different solvers and validation workloads; controller peak distinct from native GNU time peak',
                       classification='COST_COMPARISON_AVAILABLE',NOT_CERTIFIED=True)
        ck.write(DOC/'evidence/cost_comparison.json',benchmark)
        print(result['target_status']+' first='+first+' / fresh Gaussian measured / STOP',flush=True)
    else:
        ck.write(DOC/'evidence/cost_comparison.json',dict(classification='COST_COMPARISON_NOT_COMPARABLE',reason='no target-meeting B1 representation; fresh Gaussian not authorized'))
        print(result['target_status']+' / no Gaussian execution / STOP',flush=True)

if __name__=='__main__':compare()
