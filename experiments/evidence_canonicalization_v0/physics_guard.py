"""Offline-test plugin: forbidden calculator entry points fail before any trajectory."""
import json
import os
from pathlib import Path
ATTEMPTS=[]


def forbidden(name):
    def stop(*args,**kwargs):
        ATTEMPTS.append(name)
        raise AssertionError('OFFLINE_NEW_PHYSICS_FORBIDDEN:'+name)
    return stop


def pytest_configure(config):
    from experiments.adaptive_execution_v1 import service,checker,adapters
    service.run_request=forbidden('service.run_request')
    checker.own_pass=forbidden('checker.own_pass')
    adapters.GpuWorker=forbidden('adapters.GpuWorker')


def pytest_sessionfinish(session,exitstatus):
    path=Path(os.environ['EVIDENCE_PHYSICS_GUARD_REPORT'])
    with path.open('xb') as stream:
        stream.write(json.dumps(dict(new_physics_calls=0,gpu_calls=0,blocked_attempts=ATTEMPTS,
                     scope='ORIGINAL_TESTS_MAY_REPLACE_ENTRIES_WITH_EXPLICIT_MOCKS'),sort_keys=True).encode())
