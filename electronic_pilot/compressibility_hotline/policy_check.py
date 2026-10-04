"""Post-capture tightening: bind control thresholds to a separately supplied policy.

Preserves primary checker and raw capture unchanged; never derives authority from
threshold metadata inside the receipt it is judging.
"""
import copy
import hashlib
import json
from pathlib import Path
from . import checker


def control(receipt,protocol,expected=None):
    required=protocol['control_thresholds'] if expected is None else expected
    if receipt['thresholds']!=required:raise ValueError('threshold policy binding')
    return checker.control(receipt,protocol)


def main():
    evidence=Path('docs/active/electronic_compressibility_hotline_v1')
    p=json.loads(Path('electronic_pilot/compressibility_hotline/protocol.json').read_text())
    captured=json.loads((evidence/'controls_and_mutations.json').read_text())
    raw=Path('runs/electronic_compressibility_hotline_v1_20261004/policy_binding_v1');raw.mkdir(exist_ok=False)
    seal={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'primary_source_preserved':True,'normal_expected':p['control_thresholds'],
          'safety_probe_expected':{'enter':.02,'exit':.002,'safety':.008}}
    (raw/'seal.json').write_text(json.dumps(seal,indent=2))
    for r in captured['controls'][:6]:control(r,p)
    control(captured['controls'][6],p,expected=seal['safety_probe_expected'])
    altered=copy.deepcopy(captured['controls'][6])
    # Valid as a separately authorized safety probe, invalid as the normal policy.
    primary_accepted=checker.control(altered,p)
    try:control(altered,p)
    except ValueError as e:rejected=str(e)
    else:raise AssertionError('threshold mutation survived')
    result=dict(primary_control_checker_trusted_receipt_thresholds=primary_accepted,
                normal_policy_mutation_rejected=rejected,normal_controls_pass=6,
                explicitly_sealed_safety_probe_pass=True,
                scope='additional policy binding; does not replace or rewrite primary capture')
    (raw/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    for name in ['seal','results']:
        target=evidence/('policy_binding_'+name+'.json')
        with target.open('x') as f:f.write((raw/(name+'.json')).read_text())


if __name__=='__main__':main()
