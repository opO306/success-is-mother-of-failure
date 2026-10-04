"""Independent decoders/algebra. Does not import representation or executor."""
import hashlib
import json
import zlib
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.linalg import eigh, expm


def adaptive(meta, payload, expected):
    if meta["binding"] != expected or meta["phase"] != "raw-complex-relative-phase-preserved":
        raise ValueError("REFUSED: binding/phase")
    if hashlib.sha256(payload).hexdigest() != meta["payload_hash"]:
        raise ValueError("REFUSED: content")
    n, hot = meta["dimension"], meta["hot"]
    if sorted(set(hot)) != hot or any(i < 0 or i >= n for i in hot):
        raise ValueError("REFUSED: hot index")
    cold = [i for i in range(n) if i not in hot]
    a, b = 16*len(hot), 8*len(cold)
    if meta["hot_bytes"] != a or meta["center_bytes"] != b or len(payload) != a+b+meta["residual_bytes"]:
        raise ValueError("REFUSED: layout")
    centers = np.frombuffer(payload[a:a+b], dtype="<c8").astype("<c16")
    residual = zlib.decompress(payload[a+b:])
    center_bytes = centers.tobytes()
    if len(center_bytes) != len(residual):
        raise ValueError("REFUSED: residual")
    original = bytes(x ^ y for x,y in zip(center_bytes, residual))
    out = np.empty(n, dtype="<c16")
    out[hot] = np.frombuffer(payload[:a], dtype="<c16")
    out[cold] = np.frombuffer(original, dtype="<c16")
    r = sum((abs(Fraction(float(x))-Fraction(float(y))) for x,y in
             zip(out[cold].view(np.float64), centers.view(np.float64))), Fraction())
    cert = meta["certificate"]
    if cert["kind"] != "exact-rational-L1-coordinate-error" or Fraction(cert["numerator"],cert["denominator"]) < r:
        raise ValueError("REFUSED: certificate radius")
    if hashlib.sha256(out.tobytes()).hexdigest() != expected["source_state_digest"]:
        raise ValueError("REFUSED: state digest")
    return out


def blocks(meta, directory, expected):
    if meta["binding"] != expected or meta["phase"] != "raw-complex-relative-phase-preserved":
        raise ValueError("REFUSED: binding/phase")
    data, cursor = [], 0
    for k,b in enumerate(meta["blocks"]):
        if (b["id"] != k or b["start"] != cursor or b["stop"] <= cursor or b["dtype"] != "<c16" or
            b["shape"] != [b["stop"]-cursor] or b["state_binding"] != expected or
            Path(b["file"]).name != b["file"]):
            raise ValueError("REFUSED: block order/shape/binding")
        value = (Path(directory)/b["file"]).read_bytes()
        if len(value) != 16*(b["stop"]-cursor) or hashlib.sha256(value).hexdigest() != b["content_hash"]:
            raise ValueError("REFUSED: block hash")
        data.append(value)
        cursor = b["stop"]
    full = b"".join(data)
    if cursor != meta["dimension"] or hashlib.sha256(full).hexdigest() != expected["source_state_digest"]:
        raise ValueError("REFUSED: incomplete state/source")
    return np.frombuffer(full, dtype="<c16").copy()


def independent_density(v, corpus):
    if corpus["electrons"] == 1:
        return (v[:,None]*v.conj()[None,:]).real
    m = len(corpus["c"])
    ordered = np.zeros((m,m), dtype=complex)
    k = 0
    for i in range(m):
        for j in range(i,m):
            if i == j: ordered[i,j] = v[k]
            else: ordered[i,j] = ordered[j,i] = v[k]/np.sqrt(2)
            k += 1
    # Explicit spectator-index contraction, distinct from matrix-product implementation.
    gamma = 2*np.einsum("ik,jk->ij", ordered, ordered.conj(), optimize=False)
    return np.einsum("ai,ij,bj->ab",corpus["c"],gamma,corpus["c"],optimize=False).real


def physical(ref, reconstructed, corpus, times, tolerance):
    s,h,mu = corpus["s"],corpus["h"],corpus["dipoles"]
    w,q = eigh(s)
    root, inverse = (q*np.sqrt(w))@q.T, (q/np.sqrt(w))@q.T
    a,b = root@ref,root@reconstructed
    out = dict(raw_bytes_equal=ref.astype("<c16").tobytes()==reconstructed.astype("<c16").tobytes(),
               norm_error=float(abs(np.vdot(reconstructed,s@reconstructed).real-1)),
               fidelity=float(abs(np.vdot(a,b))**2/(np.vdot(a,a).real*np.vdot(b,b).real)),
               projector_error=float(np.max(abs(np.outer(a,a.conj())-np.outer(b,b.conj())))),
               energy_error=float(abs(np.vdot(ref,h@ref)-np.vdot(reconstructed,h@reconstructed))),
               density_error=float(np.max(abs(independent_density(ref,corpus)-independent_density(reconstructed,corpus)))),
               dipole_error=float(max(abs(np.vdot(ref,x@ref)-np.vdot(reconstructed,x@reconstructed)) for x in mu)))
    out["PASS"] = all(out[k] <= tolerance for k in ["norm_error","projector_error","energy_error","density_error","dipole_error"])
    return out


def evolution_check(initial, waves, corpus, times):
    s,h = corpus["s"],corpus["h"]
    w,q = eigh(s)
    rt,ir = (q*np.sqrt(w))@q.T,(q/np.sqrt(w))@q.T
    H = ir@h@ir
    return max(float(np.max(abs(ir@expm(-1j*H*t)@rt@initial-v))) for t,v in zip(times,waves))


def collision(payload_a, payload_b, future_difference, difference_floor=1e-6):
    equal = payload_a == payload_b
    return dict(summary_payload_equal=equal, future_difference=float(future_difference),
                authoritative="REJECTED" if equal and future_difference > difference_floor else "UNRESOLVED",
                binding_digest_is_not_reconstructable_state=True)
