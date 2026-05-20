#!/usr/bin/env bash
# Deploy ksqlDB SQL to Confluent Cloud (or any ksqlDB endpoint).
#
# Prerequisites:
#   - ksqlDB CLI on PATH (from Confluent Platform or Confluent CLI bundle)
#   - KSQLDB_ENDPOINT, KSQLDB_API_KEY, KSQLDB_API_SECRET exported
#   - Topics streams-input / streams-output exist on the linked Kafka cluster
#
# Usage (from repo root kafka-topic-consumer-offsets/):
#   export KSQLDB_ENDPOINT='https://pksqlc-xxxx.region.aws.confluent.cloud:443'
#   export KSQLDB_API_KEY='...'
#   export KSQLDB_API_SECRET='...'
#   ./ksqldb/scripts/deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL_DIR="${ROOT}/sql"

: "${KSQLDB_ENDPOINT:?Set KSQLDB_ENDPOINT (ksqlDB cluster https endpoint)}"
: "${KSQLDB_API_KEY:?Set KSQLDB_API_KEY}"
: "${KSQLDB_API_SECRET:?Set KSQLDB_API_SECRET}"

if ! command -v ksql >/dev/null 2>&1; then
  echo "ksql CLI not found on PATH. Install Confluent CLI / Platform ksqlDB client." >&2
  exit 1
fi

run_sql() {
  local file="$1"
  echo "==> ${file}"
  ksql \
    --headers \
    -u "${KSQLDB_API_KEY}" \
    -p "${KSQLDB_API_SECRET}" \
    "${KSQLDB_ENDPOINT}" \
    <"${file}"
}

run_sql "${SQL_DIR}/00_session.sql"
run_sql "${SQL_DIR}/01_input_stream.sql"
run_sql "${SQL_DIR}/02_output_pipeline.sql"

echo "Done. Verify with: SHOW STREAMS; SHOW QUERIES;"
