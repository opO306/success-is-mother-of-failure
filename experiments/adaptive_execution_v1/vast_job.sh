#!/bin/bash
# ADAPTIVE_EXECUTION_V1 job on the official Vast node (protocol 'official_host').
#   JOB=calibrate : related tests -> env -> gate100 -> calibrate (performance profile of this env_id)
#   JOB=evaluate  : related tests -> env (must have a sealed profile) -> gate100 -> evaluate repeat 1 -> checker gate
#                   (own replay) -> evaluate repeats 2..5 -> checker final -> analysis
# /proc/loadavg every 10 s; after a grace period the instance stops itself unless another process is busy.
set -u
JOB=${JOB:?JOB=calibrate|evaluate}
W=${W:-/workspace/ae1}; R=$W/repo; OUT=$W/run_$JOB; LOG=$W/job_$JOB.log; PY=${PY:-$W/venv/bin/python}
VASTAI=${VASTAI:-$(dirname $PY)/vastai}
GRACE=${GRACE:-1800}
export PATH=/usr/local/cuda/bin:$PATH
export ESP2_LINUX_CLOCK=1
export PYTHONPATH=$R/experiments/experience_start_p_v2/linux_shim:$R
cd $R
( while true; do echo "$(date -u +%T) $(cat /proc/loadavg)" >> $W/loadavg_$JOB.log; sleep 10; done ) &
LP=$!
finish() {
  rc=$?
  kill $LP 2>/dev/null
  echo "JOB_EXIT rc=$rc $(date -u +%FT%TZ)" >> $LOG
  echo "DONE_MARKER $(date -u +%FT%TZ) grace ${GRACE}s" >> $LOG
  sleep $GRACE
  others=$(ps -eo pid,pcpu,comm --no-headers | awk '$2 >= 25 {print}')
  if [ -z "$others" ]; then
    echo "STOPPING_INSTANCE $(date -u +%FT%TZ)" >> $LOG
    $VASTAI stop instance "$CONTAINER_ID" --api-key "$CONTAINER_API_KEY" >> $LOG 2>&1
  else
    echo "NOT_STOPPING busy: $others" >> $LOG
  fi
}
trap finish EXIT
C="$PY -m experiments.adaptive_execution_v1"
echo "JOB_START $JOB $(date -u +%FT%TZ) head $(git rev-parse HEAD) dirty=[$(git status --porcelain | head -5)]" >> $LOG
echo "== pytest (REMOTE LINUX related set) $(date -u +%T)" >> $LOG
$PY -m pytest tests/test_adaptive_execution_v1.py -q -p no:cacheprovider --durations=8 > $W/pytest_$JOB.log 2>&1
TRC=$?
tail -12 $W/pytest_$JOB.log >> $LOG
[ $TRC -eq 0 ] || { echo "TESTS_FAILED rc=$TRC" >> $LOG; exit 10; }
echo "== ENV $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase env >> $W/campaign_$JOB.stdout 2>&1 || exit 11
echo "== GATE100 $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase gate100 >> $W/campaign_$JOB.stdout 2>&1 || exit 12
grep -E "GATE100" $W/campaign_$JOB.stdout | tail -7 >> $LOG
if [ "$JOB" = "calibrate" ]; then
  echo "== CALIBRATE $(date -u +%T)" >> $LOG
  $C.campaign --out $OUT --phase calibrate >> $W/campaign_$JOB.stdout 2>&1 || exit 13
  grep -E "PERF_PROFILE" $W/campaign_$JOB.stdout >> $LOG
  echo "== FINISHED $(date -u +%T)" >> $LOG
  exit 0
fi
PROFILE=$($PY -c "import json;from experiments.adaptive_execution_v1 import profiles as P;e=json.load(open('$OUT/env.json'))['env']['env_id'];print(P.PROFILE_DIR/('perf_'+e[:16]+'.json'))")
[ -f "$PROFILE" ] || { echo "ENV_NOT_SEALED $PROFILE" >> $LOG; exit 20; }
echo "== EVALUATE r1 $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase evaluate --repeats 1 >> $W/campaign_$JOB.stdout 2>&1 || exit 21
echo "== CHECKER GATE (replay) $(date -u +%T)" >> $LOG
$C.checker $OUT --phase gate --profile "$PROFILE" --workers 12 >> $LOG 2>&1 || { echo "CHECKER_GATE_FAILED" >> $LOG; exit 22; }
echo "== EVALUATE r2-5 $(date -u +%T)" >> $LOG
$C.campaign --out $OUT --phase evaluate --repeats 2-5 >> $W/campaign_$JOB.stdout 2>&1 || exit 23
echo "== CHECKER FINAL $(date -u +%T)" >> $LOG
$C.checker $OUT --phase final --profile "$PROFILE" --workers 12 --expect-repeats 1-5 >> $LOG 2>&1
CRC=$?
$C.analyze $OUT --profile "$PROFILE" >> $LOG 2>&1
echo "== FINISHED checker_rc=$CRC $(date -u +%T)" >> $LOG
exit $CRC
