"""Approved remote archive preparation and sealed offline runner only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

base = Path('/workspace/aev0_6bca97f4')
archive = base / 'input.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '782f99624c227ae4d589c831ef5cf3df01ad76d2cf6e480009d0bb355d06f570'
repo = base / 'repo'
repo.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as bundle:
    for member in bundle.infolist():
        target = (repo / member.filename).resolve()
        assert target.is_relative_to(repo.resolve())
    bundle.extractall(repo)
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
completed = subprocess.run([
    sys.executable, '-m', 'experiments.adaptive_execution_verification_v0.offline',
    '--authorization', str(base / 'offline_authorization.json'),
    '--code-seal-sha256', '1a97ba798de27913d227a8b800386b3d030e5e082e0076390f584ae5be891ceb',
    '--out', str(base / 'output_attempt1'),
], cwd=repo, env=environment, timeout=125)
(base / 'bootstrap_exit.json').write_text(json.dumps({'exit': completed.returncode, 'new_trajectories': 0, 'gpu_calls': 0}))
raise SystemExit(completed.returncode)
