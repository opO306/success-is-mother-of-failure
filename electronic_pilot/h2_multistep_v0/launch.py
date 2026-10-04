"""Snapshot-only Python entry point; run with Python -I."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
stage=sys.argv.pop(1)
if stage=='execute':
    from electronic_pilot.h2_multistep_v0.campaign import execute
    execute(sys.argv[1])
elif stage=='worker':
    from electronic_pilot.h2_multistep_v0.worker import main
    main()
else:raise ValueError('unsupported stage')
