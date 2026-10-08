"""Immutable A resume bounds; no execution or approval authority."""
import json
from pathlib import Path
from experiments.adaptive_execution_real_learning_pilot_v0.common import ROOT, raw_hash

HERE=Path(__file__).resolve().parent


def protocol_hash(): return raw_hash(HERE/'protocol.json')


def check_protocol():
    for name in ('protocol_seal.json','protected_history.json'):
        for relative,expected in json.loads((HERE/name).read_bytes())['files'].items():
            if raw_hash(ROOT/relative)!=expected: raise ValueError('A_RESUME_PROTECTED_INTEGRITY:'+relative)
    return True


def protocol():
    check_protocol()
    return json.loads((HERE/'protocol.json').read_bytes())
