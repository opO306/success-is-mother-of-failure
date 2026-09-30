"""Read-only command-line verdict, without evidence/history auto-promotion."""
import argparse
from dataclasses import asdict
import json
from .types import Limits, Verdict
from .verify import verify

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('witness')
    parser.add_argument('--full',action='store_true')
    parser.add_argument('--max-steps',type=int,default=2_000_000)
    parser.add_argument('--max-bytes',type=int,default=128_000_000)
    parser.add_argument('--max-bits',type=int,default=16384)
    parser.add_argument('--seconds',type=float,default=3600)
    args=parser.parse_args()
    try:
        limits=Limits(max_steps=args.max_steps,max_bytes=args.max_bytes,max_bits=args.max_bits,seconds=args.seconds)
    except ValueError as e:
        parser.error(str(e))
    result=verify(args.witness,limits,materialize=args.full)
    value=asdict(result)
    if result.last_state is not None:
        value['last_state']=[str(v) for v in result.last_state]
    print(json.dumps(value,indent=2))
    return {Verdict.VALID:0,Verdict.INVALID:1,Verdict.REFUSED:2}[result.verdict]

if __name__=='__main__':
    raise SystemExit(main())
