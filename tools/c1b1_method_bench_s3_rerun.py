"""Re-run single S3 jobs lost to a dead pool worker (survey_only).  One job per process, same one() as the study.
  python tools/c1b1_method_bench_s3_rerun.py OUT.jsonl JOBS.jsonl     (JOBS: one JSON job list per line)
Each job must be in c1b1_method_bench_s3.jobs(); the row gets rerun tag and peak RSS. Original rows are untouched.
"""
import json
import resource
import sys

sys.path.insert(0, 'tools')
import c1b1_method_bench_s3 as s3  # noqa: E402


def main():
    out, spec = sys.argv[1], sys.argv[2]
    known = set(s3.jobs())
    for line in open(spec, encoding='utf-8'):
        if not line.strip():
            continue
        job = tuple(json.loads(line))
        if job not in known:
            raise SystemExit(f'not an S3 job: {job}')
        row = s3.one(job)
        row['rerun'] = 'oom_rerun_v1'
        row['maxrss_kb'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        with open(out, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')
        print(job, row.get('status'), row.get('err_sweep'), f"{row['wall_s']:.0f}s", row['maxrss_kb'], 'kB', flush=True)


if __name__ == '__main__':
    main()
