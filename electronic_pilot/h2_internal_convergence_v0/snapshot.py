"""Read address-free native MPFR snapshots as exact dyadics, without MPFUN."""
from collections import Counter
from pathlib import Path
import hashlib
import struct

from mpmath import mp

DPS = 160
HS_MAGIC = 0x4832534155445630
EV_MAGIC = 0x4832564155445630
ZERO_EXP = -(1 << 63) + 1


def context():
    ctx = mp.clone()
    ctx.dps = DPS
    return ctx


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode_word(words, ctx):
    bits, raw_sign, exponent, *limbs = words
    if not (64 <= bits <= 384 and bits % 64 == 0 and len(limbs) == 6):
        raise ValueError("invalid MPFR precision/layout")
    sign32 = raw_sign & 0xFFFFFFFF
    sign = sign32 if sign32 < (1 << 31) else sign32 - (1 << 32)
    if sign not in (-1, 1):
        raise ValueError("invalid MPFR sign")
    active = bits // 64
    if any(limbs[active:]):
        raise ValueError("unused limbs must be zero")
    if exponent == ZERO_EXP:
        # MPFR does not specify the content of active limbs for zero.
        return ctx.mpf(0), bits
    if not (-100000 < exponent < 100000):
        raise ValueError("nonfinite or unsupported MPFR exponent")
    mantissa = sum((limbs[i] & ((1 << 64) - 1)) << (64 * i)
                   for i in range(active))
    if mantissa.bit_length() != bits:
        raise ValueError("unnormalized MPFR significand")
    # At 160 digits, all <=384-bit input significands are represented exactly.
    return ctx.ldexp(ctx.mpf(sign * mantissa), exponent - bits), bits


def read_hs(path, ctx):
    data = Path(path).read_bytes()
    if len(data) < 72:
        raise ValueError("truncated matrix header")
    magic, version, n, ln, limbs, nd, nmax, omega, maxit = struct.unpack_from("<9q", data)
    if (magic, version, limbs) != (HS_MAGIC, 1, 6) or ln != n * (n + 1) // 2:
        raise ValueError("invalid matrix header")
    if not 1 <= n <= 1000 or len(data) != 72 + 2 * ln * 72:
        raise ValueError("matrix dimension/length mismatch")
    values, precision = [], Counter()
    for row in struct.iter_unpack("<9q", data[72:]):
        value, bits = decode_word(row, ctx)
        values.append(value)
        precision[bits] += 1
    meta = dict(n=n, packed_length=ln, NDIGITS=nd, NMAX=nmax, OMEGA=omega,
                ITMAX=maxit, precision_bits_counts=dict(precision),
                format="little_endian_int64_MPFR_dyadic_lower_row_v1",
                sha256=sha(path), bytes=len(data))
    return values[:ln], values[ln:], meta


def read_ev(path, ctx):
    data = Path(path).read_bytes()
    if len(data) < 32:
        raise ValueError("truncated vector header")
    magic, version, n, limbs = struct.unpack_from("<4q", data)
    if (magic, version, limbs) != (EV_MAGIC, 1, 6) or not 1 <= n <= 1000:
        raise ValueError("invalid vector header")
    if len(data) != 32 + (n + 1) * 72:
        raise ValueError("vector dimension/length mismatch")
    values, precision = [], Counter()
    for row in struct.iter_unpack("<9q", data[32:]):
        value, bits = decode_word(row, ctx)
        values.append(value)
        precision[bits] += 1
    return values[0], values[1:], dict(n=n, precision_bits_counts=dict(precision),
                                      sha256=sha(path), bytes=len(data))


def calibration(path):
    ctx = context()
    expected = [ctx.mpf(0), -ctx.mpf(3) / 2, 1 + ctx.ldexp(ctx.mpf(1), -100),
                -ctx.ldexp(ctx.mpf(1), 100), ctx.ldexp(ctx.mpf(1), -300),
                ctx.mpf(25) / 8]
    rows = list(struct.iter_unpack("<9q", Path(path).read_bytes()))
    if len(rows) != len(expected):
        raise ValueError("calibration record count mismatch")
    for row, target in zip(rows, expected):
        assert decode_word(row, ctx)[0] == target, "native export calibration mismatch"
    assert [row[0] for row in rows] == [384] * 5 + [320]
    return {"status": "NATIVE_DYADIC_EXPORT_CALIBRATION_PASS", "records": 6,
            "sha256": sha(path), "precision_bits": [row[0] for row in rows]}
