"""S3b pre-run probe: compare the same panels at two quadref precisions.  python ... A.jsonl B.jsonl"""
import json
import sys

import mpmath as mm


def main():
    mm.mp.dps = 40
    A = {tuple(r['job']): r for r in map(json.loads, open(sys.argv[1]))}
    B = {tuple(r['job']): r for r in map(json.loads, open(sys.argv[2]))}
    for k in sorted(A):
        a, b = A[k], B.get(k, {})
        print(k, a['status'], b.get('status'), f"wall {a['wall_s']:.0f} s / {b.get('wall_s', 0):.0f} s",
              a.get('error', '')[:120], b.get('error', '')[:120])
        if a['status'] == b.get('status') == 'ok':
            d = max(max([abs(mm.mpf(x['sin2_true']) - mm.mpf(y['sin2_true']))] +
                        [abs(mm.mpf(x['sin2'][h]) - mm.mpf(y['sin2'][h])) for h in ('40', '20')])
                    for x, y in zip(a['nodes'], b['nodes']))
            print('   max abs sin2 difference', mm.nstr(d, 3), ' b from', a['nodes'][0]['b'][:14],
                  'to', a['nodes'][-1]['b'][:14])


if __name__ == '__main__':
    main()
