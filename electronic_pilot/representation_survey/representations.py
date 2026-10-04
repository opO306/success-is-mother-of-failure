"""Four small storage/execution prototypes. Dense bytes remain REF."""
import hashlib
import json
import math
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

import numpy as np

VERSION = "electronic-representation-survey-v1"
PHASE = "raw-complex-relative-phase-preserved"


def dump(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw(v):
    return np.asarray(v, dtype="<c16").tobytes()


def binding(v, contract):
    return dict(contract, source_state_digest=sha(raw(v)), representation_version=VERSION)


def require_binding(actual, expected):
    if actual != expected:
        raise ValueError("REFUSED: stale state/law/basis/sector/version binding")


def radius(v, center):
    return sum((abs(Fraction(float(a))-Fraction(float(b))) for a, b in
                zip(np.asarray(v).view(np.float64), np.asarray(center).view(np.float64))), Fraction())


def adaptive_encode(v, bind, hot_count=8):
    v = np.asarray(v, dtype="<c16")
    hot = np.sort(np.argsort(-np.abs(v), kind="stable")[:min(hot_count, len(v))])
    cold = np.setdiff1d(np.arange(len(v)), hot)
    center = v[cold].astype("<c8").astype("<c16")
    if not np.all(np.isfinite(center)):
        raise ValueError("REFUSED: nonfinite adaptive center")
    residual = np.bitwise_xor(np.frombuffer(raw(v[cold]), dtype=np.uint8),
                             np.frombuffer(raw(center), dtype=np.uint8)).tobytes()
    cold_compressed = zlib.compress(residual, 9)
    r = radius(v[cold], center)
    certificate = {"kind": "exact-rational-L1-coordinate-error", "numerator": r.numerator,
                   "denominator": r.denominator, "scope": "stored binary64 coordinates, not continuum dynamics"}
    payload = raw(v[hot])+v[cold].astype("<c8").tobytes()+cold_compressed
    meta = dict(binding=bind, phase=PHASE, dimension=len(v), hot=hot.tolist(),
                hot_bytes=len(hot)*16, center_bytes=len(cold)*8,
                residual_bytes=len(cold_compressed), payload_hash=sha(payload),
                certificate=certificate)
    return meta, payload


def adaptive_decode(meta, payload, expected):
    require_binding(meta["binding"], expected)
    if meta.get("phase") != PHASE or sha(payload) != meta["payload_hash"]:
        raise ValueError("REFUSED: phase/content mismatch")
    n = meta["dimension"]
    hot = np.array(meta["hot"], dtype=int)
    if len(set(hot.tolist())) != len(hot) or np.any(hot < 0) or np.any(hot >= n):
        raise ValueError("REFUSED: adaptive index")
    cold = np.setdiff1d(np.arange(n), hot)
    a, b = meta["hot_bytes"], meta["center_bytes"]
    if a != len(hot)*16 or b != len(cold)*8 or len(payload) != a+b+meta["residual_bytes"]:
        raise ValueError("REFUSED: adaptive size")
    v = np.empty(n, dtype="<c16")
    v[hot] = np.frombuffer(payload[:a], dtype="<c16")
    center = np.frombuffer(payload[a:a+b], dtype="<c8").astype("<c16")
    residual = zlib.decompress(payload[a+b:])
    if len(residual) != len(cold)*16:
        raise ValueError("REFUSED: residual size")
    restored = np.bitwise_xor(np.frombuffer(raw(center), dtype=np.uint8),
                             np.frombuffer(residual, dtype=np.uint8)).tobytes()
    v[cold] = np.frombuffer(restored, dtype="<c16")
    cert = meta["certificate"]
    r = Fraction(cert["numerator"], cert["denominator"])
    if r < radius(v[cold], center) or sha(raw(v)) != expected["source_state_digest"]:
        raise ValueError("REFUSED: false enclosure/source digest")
    return v


def adaptive_preview(meta, payload, operator, tolerance, expected):
    """Exact bound on exact quadratic forms of stored coordinate values.

    A numerical center expectation is not returned as a rigorous interval.
    All canonical observables/evolution restore original binary64 bytes.
    """
    # This prototype pays exact residual validation before trusting a bound.
    # It is an explicit correctness cost, not a cheap certified fast path.
    adaptive_decode(meta, payload, expected)
    n, hot = meta["dimension"], np.array(meta["hot"], dtype=int)
    cold = np.setdiff1d(np.arange(n), hot)
    a, b = meta["hot_bytes"], meta["center_bytes"]
    center = np.empty(n, dtype="<c16")
    center[hot] = np.frombuffer(payload[:a], dtype="<c16")
    center[cold] = np.frombuffer(payload[a:a+b], dtype="<c8").astype("<c16")
    r = Fraction(meta["certificate"]["numerator"], meta["certificate"]["denominator"])
    l1 = sum((abs(Fraction(float(x))) for x in center.view(np.float64)), Fraction())
    op_bound = max(abs(Fraction(float(x))) for x in np.asarray(operator).ravel())
    error = op_bound*(2*l1*r+r*r)
    return dict(decision="REFINE" if error > Fraction(tolerance) else "BOUND_WITHIN_TOLERANCE",
                error_bound=float(error), bound_numerator=error.numerator,
                bound_denominator=error.denominator,
                returned_approximate_physical_result=False)


def summary_encode(v, bind, observations, density, places=12):
    rounded = np.round(np.asarray(density, dtype="<f8"), places)
    # Normalize signed zero only in the explicitly lossy INDEX payload.
    rounded[rounded == 0] = 0.
    payload = dict(energy=round(observations["energy"], places),
                   density_fingerprint=sha(rounded.tobytes()),
                   dipole=[round(float(x), places) for x in observations["dipole"]],
                   dominant_magnitudes=sorted([round(float(x), places) for x in np.abs(v)], reverse=True)[:8])
    return dict(binding=bind, summary=payload, authoritative=False,
                role="OBSERVER/INDEX ONLY")


def summary_validate(meta, expected):
    require_binding(meta["binding"], expected)
    if meta.get("authoritative") is not False or meta.get("role") != "OBSERVER/INDEX ONLY":
        raise ValueError("REFUSED: summary collision/authority concealed")
    return meta["summary"]


def block_encode(v, bind, directory, block_size):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    blocks = []
    for k, lo in enumerate(range(0, len(v), block_size)):
        data = raw(v[lo:lo+block_size])
        content = sha(data)
        name = f"{k:06d}.bin"
        (directory/name).write_bytes(data)
        blocks.append(dict(id=k, start=lo, stop=min(lo+block_size, len(v)), dtype="<c16",
                           shape=[min(block_size, len(v)-lo)], content_hash=content,
                           file=name, state_binding=bind))
    meta = dict(binding=bind, phase=PHASE, dimension=len(v), blocks=blocks)
    (directory/"manifest.json").write_bytes(dump(meta))
    return meta


def validate_manifest(meta, expected):
    require_binding(meta["binding"], expected)
    if meta.get("phase") != PHASE:
        raise ValueError("REFUSED: phase metadata")
    cursor = 0
    for k, block in enumerate(meta["blocks"]):
        if (block["id"] != k or block["start"] != cursor or block["stop"] <= cursor or
            block["dtype"] != "<c16" or block["shape"] != [block["stop"]-cursor] or
            block["state_binding"] != expected or Path(block["file"]).name != block["file"]):
            raise ValueError("REFUSED: missing/reordered/unbound block")
        cursor = block["stop"]
    if cursor != meta["dimension"]:
        raise ValueError("REFUSED: incomplete full state")


def load_block(meta, directory, k, counters=None):
    block = meta["blocks"][k]
    data = (Path(directory)/block["file"]).read_bytes()
    if sha(data) != block["content_hash"] or len(data) != block["shape"][0]*16:
        raise ValueError("REFUSED: block content hash/length")
    if counters is not None:
        counters["read_bytes"] += len(data)
        counters["read_calls"] += 1
    return np.frombuffer(data, dtype="<c16")


def block_restore(meta, directory, expected, counters=None):
    validate_manifest(meta, expected)
    v = np.concatenate([load_block(meta, directory, k, counters) for k in range(len(meta["blocks"]))])
    if sha(raw(v)) != expected["source_state_digest"]:
        raise ValueError("REFUSED: source state mismatch")
    return v


def stream_quadratic(meta, directory, matrix, expected):
    """Dense coupling consumes all column blocks per row block."""
    validate_manifest(meta, expected)
    counts = dict(read_bytes=0, read_calls=0, peak_coefficient_working_bytes=0,
                  peak_operator_tile_bytes=0)
    parts = []
    for i, bi in enumerate(meta["blocks"]):
        left = load_block(meta, directory, i, counts)
        action = np.zeros(len(left), dtype=complex)
        for j, bj in enumerate(meta["blocks"]):
            right = load_block(meta, directory, j, counts)
            tile = np.asarray(matrix[bi["start"]:bi["stop"], bj["start"]:bj["stop"]])
            counts["peak_coefficient_working_bytes"] = max(counts["peak_coefficient_working_bytes"],
                                                          left.nbytes+action.nbytes+right.nbytes)
            counts["peak_operator_tile_bytes"] = max(counts["peak_operator_tile_bytes"], tile.nbytes)
            action += tile@right
        parts.append(float(np.vdot(left, action).real))
    return math.fsum(parts), counts


def cas_checkpoint(v, bind, store, block_size, parent=None):
    store = Path(store)
    objects = store/"objects"
    nodes = store/"nodes"
    objects.mkdir(parents=True, exist_ok=True)
    nodes.mkdir(exist_ok=True)
    items = []
    for k, lo in enumerate(range(0, len(v), block_size)):
        data = raw(v[lo:lo+block_size])
        digest = sha(data)
        path = objects/digest
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError("REFUSED: dedup merged different bytes")
        else:
            with path.open("xb") as f: f.write(data)
        items.append(dict(id=k, start=lo, stop=min(lo+block_size, len(v)), content_hash=digest))
    node = dict(binding=bind, phase=PHASE, dimension=len(v), parent=parent, blocks=items)
    identity = sha(dump(node))
    path = nodes/(identity+".json")
    if not path.exists(): path.write_bytes(dump(node))
    return identity


def cas_restore(identity, store, expected):
    store = Path(store)
    content = (store/"nodes"/(identity+".json")).read_bytes()
    if sha(content) != identity:
        raise ValueError("REFUSED: checkpoint manifest digest")
    node = json.loads(content)
    require_binding(node["binding"], expected)
    if node["parent"] is not None:
        parent_content = (store/"nodes"/(node["parent"]+".json")).read_bytes()
        if sha(parent_content) != node["parent"]:
            raise ValueError("REFUSED: checkpoint parent digest")
        parent = json.loads(parent_content)
        if any(parent["binding"][k] != expected[k] for k in expected if k != "source_state_digest"):
            raise ValueError("REFUSED: checkpoint law parent binding")
    meta = dict(node, blocks=[dict(x, dtype="<c16", shape=[x["stop"]-x["start"]],
                                          file=x["content_hash"], state_binding=expected) for x in node["blocks"]])
    return block_restore(meta, store/"objects", expected)


def parallel_checks(meta, directory, expected, workers=1):
    validate_manifest(meta, expected)
    def part(k):
        v = load_block(meta, directory, k)
        return k, float(np.vdot(v, v).real), sha(raw(v))
    started = time.perf_counter()
    if workers == 1:
        results = [part(k) for k in range(len(meta["blocks"]))]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(part, range(len(meta["blocks"]))))
    results.sort()
    return dict(norm=math.fsum(x[1] for x in results), hashes=[x[2] for x in results],
                wall_seconds=time.perf_counter()-started,
                rounding_contract="same block partials plus ordered math.fsum; numerical tolerance vs dense dot")
