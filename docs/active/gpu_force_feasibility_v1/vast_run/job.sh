#!/bin/bash
# G0 job on Vast 52763685 (launcher, not part of the sealed code): Linux tests -> campaign -> checker -> analysis,
# /proc/loadavg every 10 s, grace period, then the instance stops itself unless another process is busy.
set -u
W=/workspace/g0; R=$W/repo; OUT=$W/run; LOG=$W/job.log; PY=/workspace/venv/bin/python
export PATH=/usr/local/cuda/bin:$PATH
cd $R
( while true; do echo "$(date -u +%T) $(cat /proc/loadavg)" >> $W/loadavg.log; sleep 10; done ) &
LP=$!
finish() {
  rc=$?
  kill $LP 2>/dev/null
  echo "CAMPAIGN_EXIT rc=$rc $(date -u +%FT%TZ)" >> $LOG
  $PY -m experiments.gpu_force_feasibility_v1.checker $OUT >> $LOG 2>&1
  $PY -m experiments.gpu_force_feasibility_v1.analyze $OUT >> $LOG 2>&1
  echo "DONE_MARKER $(date -u +%FT%TZ) grace 1800s" >> $LOG
  sleep 1800
  others=$(ps -eo pid,pcpu,comm --no-headers | awk '$2 >= 25 {print}')
  if [ -z "$others" ]; then
    echo "STOPPING_INSTANCE $(date -u +%FT%TZ)" >> $LOG
    /workspace/venv/bin/vastai stop instance "$CONTAINER_ID" --api-key "$CONTAINER_API_KEY" >> $LOG 2>&1
  else
    echo "NOT_STOPPING busy: $others" >> $LOG
  fi
}
trap finish EXIT
echo "JOB_START $(date -u +%FT%TZ) head $(git rev-parse HEAD)" >> $LOG
echo "== pytest (REMOTE LINUX related set)" >> $LOG
$PY -m pytest tests/test_gpu_force_feasibility_v1.py -q -p no:cacheprovider 2>&1 | tail -3 >> $LOG
$PY -m experiments.gpu_force_feasibility_v1.campaign --out $OUT >> $W/campaign.stdout 2>&1
