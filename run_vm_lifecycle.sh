#!/usr/bin/env bash
set -euo pipefail

until_time="$1"
stamp="$2"
mkdir -p runs

for seed in $(seq 8000 8063); do
  base="runs/vm4h_lifecycle_${stamp}_seed${seed}"
  python3 run_nonliving_face_until.py \
    --seed "$seed" \
    --until "$until_time" \
    --output "${base}.json" \
    --checkpoint-events 1000 \
    >"${base}.stdout.log" 2>"${base}.stderr.log" &
done

wait
sha256sum runs/vm4h_lifecycle_${stamp}_seed*.json >"runs/vm4h_lifecycle_${stamp}.sha256"
date --iso-8601=seconds >"runs/vm4h_lifecycle_${stamp}.complete"
