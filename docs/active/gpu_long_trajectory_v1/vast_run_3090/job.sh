#!/bin/bash
# GPU_LONG_TRAJECTORY_V1 job on the official Vast GPU node (launcher): Linux tests -> gate P -> checker (gate, writes
# gpu_support.json) -> fixed-p T1000 -> checker (gate) -> P2 services -> checker (gate) -> performance -> analysis;
# the related tests are a gate too; /proc/loadavg every 10 s; a grace period, then the instance stops itself unless
# another process is busy.
set -u
W=${W:-/workspace/lt1}; R=$W/repo; OUT=$W/run; LOG=$W/job.log; PY=${PY:-$W/venv/bin/python}
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
  $PY -m experiments.gpu_long_trajectory_v1.analyze $OUT >> $LOG 2>&1
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
C="$PY -m experiments.gpu_long_trajectory_v1"
echo "JOB_START $(date -u +%FT%TZ) head $(git rev-parse HEAD)" >> $LOG
echo "== pytest (REMOTE LINUX related set) $(date -u +%T)" >> $LOG
$PY -m pytest tests/test_gpu_long_trajectory_v1.py -q -p no:cacheprovider --durations=8 > $W/pytest.log 2>&1
TRC=$?
tail -12 $W/pytest.log >> $LOG
[ $TRC -eq 0 ] || { echo "TESTS_FAILED rc=$TRC" >> $LOG; exit 10; }
echo "== GATE P $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase gateP >> $W/campaign.stdout 2>&1 || exit 11
$C.checker $OUT --phase gateP --workers 1 >> $LOG 2>&1 || { echo "GATE_P_FAILED" >> $LOG; exit 12; }
echo "== FIXED $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase fixed >> $W/campaign.stdout 2>&1 || exit 13
$C.checker $OUT --phase fixed --workers 12 >> $LOG 2>&1 || { echo "FIXED_GATE_FAILED" >> $LOG; exit 14; }
echo "== SERVICE $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase service >> $W/campaign.stdout 2>&1 || exit 15
$C.checker $OUT --phase service --workers 12 >> $LOG 2>&1 || { echo "SERVICE_GATE_FAILED" >> $LOG; exit 16; }
echo "== PERF $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase perf >> $W/campaign.stdout 2>&1 || exit 17
echo "== FINISHED $(date -u +%T)" >> $LOG
