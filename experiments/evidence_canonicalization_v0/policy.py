"""Sealed evidence policy. Pure file/JSON handling, no executor or numerical imports."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def raw_hash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def policy_hash(): return raw_hash(HERE/'protocol.json')


def check_policy():
    for name in ('protocol_seal.json','numeric_string_amendment_seal.json'):
        seal=json.loads((HERE/name).read_bytes())
        for relative,expected in seal['files'].items():
            if raw_hash(ROOT/relative)!=expected: raise ValueError('EVIDENCE_POLICY_INTEGRITY:'+relative)
    return json.loads((HERE/'protocol.json').read_bytes())
