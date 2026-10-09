"""Pure administrative disconnect probe, no project/test/calculator import."""
from pathlib import Path
import json,os,sys,time
root=Path(sys.argv[1]);time.sleep(4)
with (root/'probe_written.json').open('xb') as f:
    f.write(json.dumps(dict(probe='ADMIN_SSH_DISCONNECT_ONLY',pid=os.getpid())).encode());f.flush();os.fsync(f.fileno())
