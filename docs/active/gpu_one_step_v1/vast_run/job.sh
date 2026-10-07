#!/bin/bash
# GPU_ONE_STEP_V1 job on Vast 52763629 (launcher, not sealed code): Linux tests -> campaign -> checker -> analysis,
# /proc/loadavg every 10 s, grace period, then the instance stops itself unless another process is busy.
set -u
W=/workspace/os1; R=$W/repo; OUT=$W/run; LOG=$W/job.log; PY=/workspace/esp2/venv/bin/python
export PATH=/usr/local/cuda/bin:$PATH
export ESP2_LINUX_CLOCK=1
export PYTHONPATH=$R/experiments/experience_start_p_v2/linux_shim:$R
cd $R
( while true; do echo "$(date -u +%T) $(cat /proc/loadavg)" >> $W/loadavg.log; sleep 10; done ) &
LP=$!
finish() {
  rc=$?
  kill $LP 2>/dev/null
  echo "CAMPAIGN_EXIT rc=$rc $(date -u +%FT%TZ)" >> $LOG
  $PY -m experiments.gpu_one_step_v1.checker $OUT >> $LOG 2>&1
  $PY -m experiments.gpu_one_step_v1.analyze $OUT >> $LOG 2>&1
  echo "DONE_MARKER $(date -u +%FT%TZ) grace 1800s" >> $LOG
  sleep 1800
  others=$(ps -eo pid,pcpu,comm --no-headers | awk '$2 >= 25 {print}')
  if [ -z "$others" ]; then
    echo "STOPPING_INSTANCE $(date -u +%FT%TZ)" >> $LOG
    /workspace/esp2/venv/bin/vastai stop instance "$CONTAINER_ID" --api-key "$CONTAINER_API_KEY" >> $LOG 2>&1
  else
    echo "NOT_STOPPING busy: $others" >> $LOG
  fi
}
trap finish EXIT
echo "JOB_START $(date -u +%FT%TZ) head $(git rev-parse HEAD)" >> $LOG
echo "== pytest (REMOTE LINUX related set)" >> $LOG
$PY -m pytest tests/test_gpu_one_step_v1.py -q -p no:cacheprovider 2>&1 | tail -3 >> $LOG
$PY -m experiments.gpu_one_step_v1.campaign --out $OUT >> $W/campaign.stdout 2>&1
