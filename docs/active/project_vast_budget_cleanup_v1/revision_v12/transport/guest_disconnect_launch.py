"""Remote-only bounded fault injection: launched job survives this SSH session."""
from pathlib import Path
import json,sys,time
guest,expected,job_id=sys.argv[1:]
sys.path.insert(0,guest)
from guest_job import launch
print(json.dumps(launch(Path(guest)/'job',expected,job_id)),flush=True)
time.sleep(10)
