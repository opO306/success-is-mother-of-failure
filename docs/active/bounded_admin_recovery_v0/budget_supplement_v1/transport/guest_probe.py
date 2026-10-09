"""Remote-only administrative identity probe; receives argv, never project imports."""
import json
import os
from pathlib import Path
import sys


def actual_instance():
    values = [part.split(b'=', 1)[1].decode('ascii')
              for part in Path('/proc/1/environ').read_bytes().split(bytes([0]))
              if part.startswith(b'CONTAINER_ID=')]
    if len(values) != 1 or not values[0].isdigit():
        raise ValueError('PID1_CONTAINER_ID_MISSING_DUPLICATE_OR_INVALID')
    return values[0]


if __name__ == '__main__':
    expected, runtime, guest = sys.argv[1:]
    actual = actual_instance()
    if sys.platform != 'linux' or actual != expected:
        raise ValueError('ACTUAL_INSTANCE_MISMATCH')
    if not Path(runtime).is_file() or not os.sched_getaffinity(0):
        raise ValueError('PRESERVED_RUNTIME_OR_AFFINITY_MISSING')
    root = Path(guest)
    if root.parent != Path('/workspace') or not root.name.startswith('tablet_v0_'):
        raise ValueError('GUEST_ROOT_SCOPE')
    root.mkdir(exist_ok=False)
    print(json.dumps(dict(actual_container_id=actual, guest_root=str(root),
                         runtime=runtime, affinity=sorted(os.sched_getaffinity(0)))))
