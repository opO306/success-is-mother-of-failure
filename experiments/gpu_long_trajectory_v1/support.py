"""GPU_LONG_TRAJECTORY_V1 precision support layer (protocol 'gate_P_gpu_precision_support'; the checker never imports it).

ExtPV is GPU_PAIR_VECTOR_V1's PV whose upload accepts p in SEALED_EXT_P. It calls the unchanged PV / G0 upload with
gpu_host.SUPPORTED_P widened by that one p for the duration of the call only (a runtime scope; gpu_host.py, the CUDA
code, rounding, limbs, the exp algorithm and the working precision are not changed). Any other p is refused.
"""

from __future__ import annotations

from experiments.gpu_force_feasibility_v1 import gpu_host as GH
from experiments.gpu_pair_vector_v1 import pv_host as PH

SEALED_EXT_P = (64, 73, 78, 109, 128, 161, 163, 166, 192)


class ExtPV(PH.PV):
    def upload(self, p):
        if p not in SEALED_EXT_P:
            raise GH.Refused(f"REFUSED_DEVICE_PRECISION: p {p} not in the sealed extended set")
        saved = GH.SUPPORTED_P
        GH.SUPPORTED_P = tuple(sorted(set(saved) | {p}))
        try:
            return super().upload(p)
        finally:
            GH.SUPPORTED_P = saved
