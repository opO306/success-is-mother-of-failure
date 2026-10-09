import sys,time
from pathlib import Path
root,instance,job_id=sys.argv[1:]
sys.path.insert(0,root)
from guest_job import launch
print(launch(Path(root)/'job',instance,job_id),flush=True)
time.sleep(40)
