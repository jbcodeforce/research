#!/usr/bin/env bash
# End-to-end demo: generate → train → evaluate → score
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "==> sync dependencies"
uv sync

echo "==> waiting for Kafka (docker compose)"
docker compose up -d
for i in $(seq 1 30); do
  if docker compose exec -T broker kafka-broker-api-versions --bootstrap-server broker:29092 >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "==> create topics"
uv run reefer-pm-create-topics

echo "==> generate telemetry (train + test + inference on one topic)"
uv run reefer-pm-generate

echo "==> train"
uv run reefer-pm-train

echo "==> evaluate"
uv run reefer-pm-evaluate

echo "==> score inference"
uv run reefer-pm-score

echo "==> done. Inspect reefer.ml.metrics.v1 and reefer.ml.predictions.v1"
