#!/bin/bash
# EXPERIENCE_START_P_V2 job on the Vast node (protocol 'platform'). Launch detached:
#   (setsid nohup /workspace/esp2/repo/experiments/experience_start_p_v2/vast_job.sh > /workspace/esp2/job.out 2>&1 < /dev/null &)
# Campaign -> analysis -> checker on the node; then a grace period for fetching the evidence; then the instance stops
# itself unless a process not belonging to this job uses >= 25 % CPU (then it is left on and the log says why).
set -u
W=/workspace/esp2
OUT=$W/run
LOG=$W/job.log
GRACE=${ESP2_GRACE_S:-1800}
cd $W/repo
export ESP2_LINUX_CLOCK=1
export PYTHONPATH=$W/repo/experiments/experience_start_p_v2/linux_shim:$W/repo
PY=$W/venv/bin/python
finish() {
  rc=$?
  echo "CAMPAIGN_EXIT rc=$rc $(date -u +%FT%TZ)" >> $LOG
  $PY -m experiments.experience_start_p_v2.analyze $OUT >> $LOG 2>&1
  $PY -m experiments.experience_start_p_v2.checker $OUT >> $LOG 2>&1
  echo "DONE_MARKER $(date -u +%FT%TZ) grace ${GRACE}s" >> $LOG
  sleep $GRACE
  others=$(ps -eo pid,pcpu,comm --no-headers | awk '$2 >= 25 {print}')
  if [ -z "$others" ]; then
    echo "STOPPING_INSTANCE $(date -u +%FT%TZ)" >> $LOG
    $W/venv/bin/vastai stop instance "$CONTAINER_ID" --api-key "$CONTAINER_API_KEY" >> $LOG 2>&1
  else
    echo "NOT_STOPPING other busy processes: $others" >> $LOG
  fi
}
trap finish EXIT
echo "JOB_START $(date -u +%FT%TZ) head $(git rev-parse HEAD)" >> $LOG
$PY -m experiments.experience_start_p_v2.campaign --out $OUT >> $W/campaign.stdout 2>&1
