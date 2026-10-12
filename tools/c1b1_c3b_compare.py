"""C3b-1 replay comparison (survey_only; plan docs/active/C1B1_C3B_NATIVE_KERNEL_SPEED_PLAN_V0.md section 4 R).

  python tools/c1b1_c3b_compare.py C3A4_ROWS NEW_NATIVE_ROWS OUT.json

C3A4_ROWS: the C3a-4 rows, either the committed compact copy docs/active/C1B1_C3A4_PANEL_V0.jsonl or the full
original on the remote PC (/root/c3a4pkg/c3a4_panel.jsonl); in both, the Python rows carry the whole world, and C3a-4
showed the C3a native track equal to them on all 14 inputs. NEW_NATIVE_ROWS: rows of tools/c1b1_native_panel.py run with ENGINES=native and
the C3b-1 source. Each new native world is compared with the C3a-4 Python world by the panel tool's own classify
(no tolerance; kick counts too). Needs no project import.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C3A4_SHA256 = {'3c2864396bc9b1aa': 'compact copy', '4c984b7da73fa78d': 'full original'}


def _panel_tool():
    spec = importlib.util.spec_from_file_location('native_panel', ROOT / 'tools/c1b1_native_panel.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def compare(c3a4_path, new_path, out_path):
    P = _panel_tool()
    raw = Path(c3a4_path).read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest()[:16] not in C3A4_SHA256:
        raise ValueError('C3a-4 rows file hash mismatch')
    py = {r['id']: r for r in map(json.loads, raw.decode('utf-8').splitlines()) if r['engine'] == 'py'}
    new = {}
    for line in open(new_path, encoding='utf-8'):
        r = json.loads(line)
        if r['engine'] != 'native' or r['id'] in new:
            raise ValueError(f'unexpected or duplicate row {r["id"]} {r["engine"]}')
        new[r['id']] = r
    per, counts = {}, {}
    for i in P.PANEL_IDS:
        v = P.classify(py.get(i), new.get(i))
        if i in new and new[i]['kind'] == 'ok':
            v['native_pen_cpu_s'] = new[i]['pen_cpu_s']
        per[i] = v
        counts[v['verdict']] = counts.get(v['verdict'], 0) + 1
    res = dict(c3a4_rows_sha256=hashlib.sha256(raw).hexdigest(),
               new_rows_sha256=hashlib.sha256(Path(new_path).read_bytes()).hexdigest(), counts=counts, per_input=per,
               unexpected=sorted(set(new) - set(P.PANEL_IDS)))
    Path(out_path).write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(counts), flush=True)
    return res


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    compare(*sys.argv[1:])
