"""Use actual Windows telemetry, rather than invented Linux memory values."""
import os
import sys
import pytest


@pytest.mark.skipif(sys.platform!='win32',reason='Windows platform adapter')
def test_native_affinity_roundtrip_and_memory_are_real():
    from tools.c1b1_cost_local import windows_affinity,windows_set_affinity,windows_memory
    original=windows_affinity(0)
    assert original
    try:
        selected=max(original);windows_set_affinity(0,{selected})
        assert windows_affinity(0)=={selected}
        assert windows_memory(0).ru_maxrss>0
    finally:
        windows_set_affinity(0,original)


def test_adapter_rejects_wrong_execution_seal(tmp_path):
    from tools.c1b1_cost_local import validate
    with pytest.raises(ValueError,match='local adapter'):
        validate({'adapter_sha256':'fault','snapshot':'missing'},tmp_path)
