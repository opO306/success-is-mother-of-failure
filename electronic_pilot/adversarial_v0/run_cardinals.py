"""Independent fresh processes for the four remaining authorized one-points."""
import subprocess,sys
from pathlib import Path
from electronic_pilot.frontend_reference_v0.audit import write,sha

def main():
    definitions='runs/h2_adversarial_v0/definitions_v1/basis_definitions.json'
    write('runs/h2_adversarial_v0/seals/cardinal_execution_inputs.json',dict(
        definitions_sha256=sha(definitions),runner_sha256=sha(__file__),worker_sha256=sha('electronic_pilot/adversarial_v0/cardinal.py'),
        grid=[.4],basis=['cc-pVTZ','cc-pVQZ','cc-pV5Z','uncontracted-cc-pVQZ']))
    for name,label in [('cc-pVTZ','TZ'),('cc-pVQZ','QZ'),('cc-pV5Z','V5Z'),('uncontracted-cc-pVQZ','uncontracted_QZ')]:
        with Path('runs/h2_adversarial_v0/cardinal_'+label+'.log').open('w') as log:
            subprocess.run([sys.executable,'-m','electronic_pilot.adversarial_v0.cardinal','--basis',name,
                 '--definitions',definitions,'--output','runs/h2_adversarial_v0/cardinal_v0/'+label],stdout=log,stderr=subprocess.STDOUT,check=True)
        print('FINISHED',label,flush=True)

if __name__=='__main__':main()
