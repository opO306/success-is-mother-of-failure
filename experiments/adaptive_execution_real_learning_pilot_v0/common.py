from pathlib import Path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from experiments.adaptive_execution_learning_v1.core import canonical, digest, read, write_new, raw_hash, Ledger

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def code_manifest_path():
    # Explicit new source version; no inference or fallback to the historical seal.
    return ROOT/'experiments/adaptive_execution_real_learning_pilot_a_resume_v1/code_seal.json'


def public(key):
    return key.public_bytes(Encoding.Raw,PublicFormat.Raw).hex()


def verify(key,domain,envelope):
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(bytes.fromhex(envelope['signature']),domain+canonical(envelope['body']))
    except (ValueError,KeyError,TypeError,InvalidSignature) as error:
        raise ValueError('SIGNATURE_REFUSED') from error


def check_seals():
    from experiments.adaptive_execution_real_learning_pilot_a_resume_v1.policy import check_protocol
    check_protocol()
    from experiments.evidence_canonicalization_v0.policy import check_policy
    check_policy()
    from .a_safety import policy
    policy()
    for relative,expected in read(HERE/'protocol_seal.json')['files'].items():
        if raw_hash(ROOT/relative)!=expected: raise ValueError('PROTOCOL_INTEGRITY:'+relative)
    for relative,expected in read(HERE/'protected_manifest.json')['files'].items():
        if raw_hash(ROOT/relative)!=expected: raise ValueError('PROTECTED_INTEGRITY:'+relative)
    for relative,expected in read(HERE/'offline_budget_amendment_seal.json')['files'].items():
        if raw_hash(ROOT/relative)!=expected: raise ValueError('OFFLINE_AMENDMENT_INTEGRITY:'+relative)


def ns(value):
    from decimal import Decimal,ROUND_HALF_EVEN
    d=Decimal(str(value))
    if not d.is_finite() or d<0: raise ValueError('COST_INVALID')
    return int((d*10**9).to_integral_value(rounding=ROUND_HALF_EVEN))
