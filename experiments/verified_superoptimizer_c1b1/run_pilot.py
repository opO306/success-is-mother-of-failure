"""Execute fresh, bound gates. Summarization only validates existing evidence."""
import argparse
import json
from pathlib import Path
from . import evidence as E


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--inputs', type=Path, default=E.HERE / 'promotion_inputs.json')
    p.add_argument('--stage', choices=['closure', 'summarize', *E.PROMOTION], default='closure')
    p.add_argument('--promotion', action='store_true')
    a = p.parse_args()
    if a.stage == 'closure':
        E.create_run(a.run, a.inputs)
        for name in E.CLOSURE:
            print('RUN', name, flush=True)
            if E.run_stage(a.run, name):
                break
    elif a.stage != 'summarize':
        E.run_stage(a.run, a.stage)
    required = E.PROMOTION if a.promotion else E.CLOSURE
    if a.stage not in ('closure','summarize') and a.stage not in required:
        required = (*required,a.stage)
    result = E.check_run(a.run, required=required)
    E.write(a.run / 'closure.json', result)
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
