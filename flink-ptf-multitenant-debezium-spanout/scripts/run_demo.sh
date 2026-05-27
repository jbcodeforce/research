#!/usr/bin/env bash
# Build PTF JAR, start Docker stack, publish mock Debezium data, run filesystem SQL demo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Maven package"
mvn -f ptf/pom.xml -q package

echo "==> Docker build & up"
docker compose build
docker compose up -d broker
echo "Waiting for Kafka..."
sleep 15
docker compose up -d jobmanager taskmanager

echo "==> Python mock producer (host -> broker:9092)"
if command -v uv >/dev/null 2>&1; then
  uv sync
  KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092 uv run debezium-mock-produce
else
  echo "uv not found; skip producer or install uv"
fi

echo "==> Filesystem SQL demo (batch)"
docker compose exec -T sql-client bin/sql-client.sh -f /opt/flink/sql/07_filesystem_demo.sql

echo ""
echo "Done. For Kafka streaming job, exec sql-client and run 00_run_all.local.sql then 06_dml_span_out.sql"
echo "Verify sink: docker compose exec broker kafka-console-consumer --bootstrap-server broker:29092 --topic mt.span_out.v1 --from-beginning --max-messages 20"
