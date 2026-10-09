"""Load the unchanged sealed guardian with a state-checked CLI boundary; no new approval authority."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from state_contract import CheckedCli

def load_guardian(path):
    spec=importlib.util.spec_from_file_location('sealed_original_guardian',path)
    guardian=importlib.util.module_from_spec(spec);spec.loader.exec_module(guardian)
    return guardian

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--guardian',type=Path,required=True)
    parser.add_argument('--authorization',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--marker',type=Path,required=True)
    parser.add_argument('--cli',required=True)
    args=parser.parse_args(argv)
    auth=json.loads(args.authorization.read_bytes())
    if hashlib.sha256(args.guardian.read_bytes()).hexdigest()!=auth['guardian_sha256']:
        raise ValueError('ORIGINAL_GUARDIAN_RAW_PIN')
    if str(args.guardian.parent) not in sys.path:sys.path.insert(0,str(args.guardian.parent))
    guardian=load_guardian(args.guardian)
    guardian.Cli=lambda path,instance:CheckedCli(path,instance,auth,initial_role='guardian_initial')
    sys.argv=[str(args.guardian),'--authorization',str(args.authorization),'--out',str(args.out),
              '--marker',str(args.marker),'--cli',args.cli]
    return guardian.main()

if __name__=='__main__':raise SystemExit(main())
