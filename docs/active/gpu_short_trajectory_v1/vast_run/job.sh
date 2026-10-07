#!/bin/bash
# GPU_SHORT_TRAJECTORY_V1 job on a Vast RTX 3090 node (launcher): Linux tests -> S10 -> checker (gate) -> S100 ->
# checker (gate) -> performance -> analysis; /proc/loadavg every 10 s; a grace period, then the instance stops itself
# unless another process is busy. Set W (work dir) and PY (python of the venv) before running.
set -u
W=${W:-/workspace/st1}; R=$W/repo; OUT=$W/run; LOG=$W/job.log; PY=${PY:-/workspace/esp2/venv/bin/python}
VASTAI=${VASTAI:-$(dirname $PY)/vastai}
export PATH=/usr/local/cuda/bin:$PATH
export ESP2_LINUX_CLOCK=1
export PYTHONPATH=$R/experiments/experience_start_p_v2/linux_shim:$R
cd $R
( while true; do echo "$(date -u +%T) $(cat /proc/loadavg)" >> $W/loadavg.log; sleep 10; done ) &
LP=$!
finish() {
  rc=$?
  kill $LP 2>/dev/null
  echo "JOB_EXIT rc=$rc $(date -u +%FT%TZ)" >> $LOG
  $PY -m experiments.gpu_short_trajectory_v1.analyze $OUT >> $LOG 2>&1
  echo "DONE_MARKER $(date -u +%FT%TZ) grace 1800s" >> $LOG
  sleep 1800
  others=$(ps -eo pid,pcpu,comm --no-headers | awk '$2 >= 25 {print}')
  if [ -z "$others" ]; then
    echo "STOPPING_INSTANCE $(date -u +%FT%TZ)" >> $LOG
    $VASTAI stop instance "$CONTAINER_ID" --api-key "$CONTAINER_API_KEY" >> $LOG 2>&1
  else
    echo "NOT_STOPPING busy: $others" >> $LOG
  fi
}
trap finish EXIT
echo "JOB_START $(date -u +%FT%TZ) head $(git rev-parse HEAD)" >> $LOG
echo "== pytest (REMOTE LINUX related set)" >> $LOG
$PY -m pytest tests/test_gpu_short_trajectory_v1.py -q -p no:cacheprovider 2>&1 | tail -3 >> $LOG
echo "== S10 $(date -u +%T)" >> $LOG
$PY -m experiments.gpu_short_trajectory_v1.campaign --out $OUT --phase s10 >> $W/campaign.stdout 2>&1 || exit 11
$PY -m experiments.gpu_short_trajectory_v1.checker $OUT --phase s10 --workers 12 >> $LOG 2>&1 || { echo "S10_GATE_FAILED" >> $LOG; exit 12; }
echo "== S100 $(date -u +%T)" >> $LOG
$PY -m experiments.gpu_short_trajectory_v1.campaign --out $OUT --phase s100 >> $W/campaign.stdout 2>&1 || exit 13
$PY -m experiments.gpu_short_trajectory_v1.checker $OUT --phase s100 --workers 12 >> $LOG 2>&1 || { echo "S100_GATE_FAILED" >> $LOG; exit 14; }
echo "== PERF $(date -u +%T)" >> $LOG
$PY -m experiments.gpu_short_trajectory_v1.campaign --out $OUT --phase perf >> $W/campaign.stdout 2>&1 || exit 15
echo "== FINISHED $(date -u +%T)" >> $LOG
