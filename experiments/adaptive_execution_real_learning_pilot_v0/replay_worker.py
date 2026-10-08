"""Separate CPU replayer. Own KDK/readout, disclosed shared RwForce; never GPU or producer."""
import argparse
from pathlib import Path
from experiments.adaptive_execution_v1 import checker as CK
from .common import read,write_new,digest,check_seals,raw_hash,HERE,ROOT,code_manifest_path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('directory'); args=parser.parse_args(); path=Path(args.directory)
    check_seals(); s=read(path/'session.json')
    if s['origin']!='OBSERVED_REAL' or s['code_manifest_sha256']!=raw_hash(code_manifest_path()):
        raise ValueError('REPLAY_LIVE_SOURCE_REFUSED')
    for relative,expected in read(code_manifest_path())['files'].items():
        if raw_hash(ROOT/relative)!=expected: raise ValueError('SOURCE_INTEGRITY')
    result=CK.own_pass(s['N'],s['T'],163)
    write_new(path/'replay.json',{f'{s["N"]}/{s["T"]}/163':dict(origin='INDEPENDENT_REPLAY',session_sha256=digest(s),
                 code_manifest_sha256=s['code_manifest_sha256'],result=result)})


if __name__=='__main__': main()
