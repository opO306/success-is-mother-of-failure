"""CPU topology of this Windows machine: which logical CPUs belong to which physical core
(GetLogicalProcessorInformationEx, RelationProcessorCore)."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt


def cores():
    """List of {'smt': bool, 'group_cpus': [[group, [logical cpu ...]], ...]} per physical core."""
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    n = wt.DWORD(0)
    k.GetLogicalProcessorInformationEx(0, None, ctypes.byref(n))     # RelationProcessorCore = 0; sizes the buffer
    buf = ctypes.create_string_buffer(n.value)
    if not k.GetLogicalProcessorInformationEx(0, buf, ctypes.byref(n)):
        raise OSError(ctypes.get_last_error())
    raw, out, off = buf.raw, [], 0
    while off < n.value:
        size = int.from_bytes(raw[off + 4:off + 8], "little")
        flags = raw[off + 8]
        gcount = int.from_bytes(raw[off + 30:off + 32], "little")
        masks = []
        for g in range(gcount):
            base = off + 32 + g * 16
            mask = int.from_bytes(raw[base:base + 8], "little")
            group = int.from_bytes(raw[base + 8:base + 10], "little")
            masks.append([group, [i for i in range(64) if mask >> i & 1]])
        out.append({"smt": bool(flags & 1), "group_cpus": masks})
        off += size
    return out


def summary():
    import psutil
    c = cores()
    return {"logical": psutil.cpu_count(True), "physical": psutil.cpu_count(False), "cores": c,
            "core_of_cpu": {cpu: i for i, x in enumerate(c) for _, cpus in x["group_cpus"] for cpu in cpus}}
