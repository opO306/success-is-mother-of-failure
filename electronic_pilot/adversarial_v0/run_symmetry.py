"""Seal the saved-state measurement inputs immediately before execution."""
from pathlib import Path
from electronic_pilot.frontend_reference_v0.audit import sha,write,read
from .symmetry import inspect

def main():
    original=Path('/mnt/c/Users/zun24/성공은 실패의 어머니/runs/h2_qz44_sealed_v1/curve/R_0.4.npz')
    definitions=Path('runs/h2_adversarial_v0/definitions_v1/basis_definitions.json')
    inputs=[original,definitions,Path(__file__),Path('electronic_pilot/adversarial_v0/symmetry.py'),
            Path('electronic_pilot/adversarial_v0/protocol.json'),
            Path('docs/active/h2_ground_state_audit_v0/evidence/v_direct_reproduced.npy'),
            Path('docs/active/h2_ground_state_audit_v0/evidence/direct_state_order.npy')]
    bindings={str(p):sha(p) for p in inputs}
    dest=Path('runs/h2_adversarial_v0/seals/symmetry_input_seal.json')
    if dest.exists():raise ValueError('preserve existing seal')
    write(dest,dict(phase='before_saved_state_symmetry',bindings=bindings))
    inspect(definitions,original,'runs/h2_adversarial_v0/symmetry_v0')
    assert bindings=={str(p):sha(p) for p in inputs}
    write(dest.with_name('symmetry_input_postcheck.json'),dict(unchanged=True,bindings=bindings))

if __name__=='__main__':main()
