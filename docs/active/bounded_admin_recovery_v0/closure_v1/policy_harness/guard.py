"""TEST_ONLY admin fixture guard. Import/audit evidence, not OS isolation."""
import importlib.abc
import json
import os
from pathlib import Path
import sys

BLOCKED = ('a_reference', 'a_numeric', 'a_numeric_native', 'audit.independent_physics',
           'engine', 'electronic_pilot', 'torch', 'cupy', 'cuda', 'pycuda', 'numba')
attempts = []


def stop(reason):
    attempts.append(reason)
    raise RuntimeError('ADMIN_POLICY_FORBIDDEN_OPERATION:' + reason)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + '.') for name in BLOCKED):
            stop('IMPORT:' + fullname)
        return None


def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.fork',
                 'socket.__new__', 'socket.connect', 'socket.bind', 'ctypes.dlopen'):
        stop('AUDIT:' + event)


def pytest_configure(config):
    sys.meta_path.insert(0, Guard())
    sys.addaudithook(audit)


def pytest_sessionfinish(session, exitstatus):
    target = Path(os.environ['ADMIN_POLICY_GUARD_REPORT'])
    with target.open('xb') as f:
        f.write(json.dumps(dict(scope='IMPORT_AND_PYTHON_AUDIT_HOOK_ONLY; NOT_OS_AUTHORITY_ISOLATION',
             blocked_attempts=attempts, new_physics_calls=0, gpu_calls=0,
             pytest_exitstatus=exitstatus), sort_keys=True).encode())
