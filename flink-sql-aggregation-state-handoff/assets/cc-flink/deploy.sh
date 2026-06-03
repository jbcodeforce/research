#!/usr/bin/env bash
# Deploy Flink SQL statements for aggregation state handoff on Confluent Cloud.
# Usage:
#   ./assets/cc-flink/deploy.sh v1          # DDL source + sink v1 + DML v1
#   ./assets/cc-flink/deploy.sh v2          # DDL snapshot + sink v2 + DML v2 (needs SPECIFIC_OFFSETS)
#   ./assets/cc-flink/deploy.sh stop-v1     # Stop v1 DML via confluent CLI
#   ./assets/cc-flink/deploy.sh offsets     # Print specific-offsets hint from stopped v1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ASSETS="$ROOT/assets/cc-flink"
ENV_FILE="$ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

: "${FLINK_COMPUTE_POOL_ID:?Set FLINK_COMPUTE_POOL_ID in .env}"
: "${CC_ENV_ID:?Set CC_ENV_ID in .env}"
: "${BOOTSTRAP_SERVERS:?Set BOOTSTRAP_SERVERS in .env}"
: "${KAFKA_API_KEY:?Set KAFKA_API_KEY in .env}"
: "${KAFKA_API_SECRET:?Set KAFKA_API_SECRET in .env}"

STATEMENT_DDL_SOURCE="${STATEMENT_DDL_SOURCE:-handoff-ddl-source}"
STATEMENT_DDL_SINK_V1="${STATEMENT_DDL_SINK_V1:-handoff-ddl-sink-v1}"
STATEMENT_DML_V1="${STATEMENT_DML_V1:-handoff-dml-v1}"
STATEMENT_DDL_SNAPSHOT="${STATEMENT_DDL_SNAPSHOT:-handoff-ddl-snapshot}"
STATEMENT_DDL_SINK_V2="${STATEMENT_DDL_SINK_V2:-handoff-ddl-sink-v2}"
STATEMENT_DML_V2="${STATEMENT_DML_V2:-handoff-dml-v2}"

SOURCE_TOPIC="${SOURCE_TOPIC:-device-events}"
SINK_V1_TOPIC="${SINK_V1_TOPIC:-agg-state-v1}"
SINK_V2_TOPIC="${SINK_V2_TOPIC:-agg-state-v2}"

if ! command -v confluent >/dev/null; then
  echo "confluent CLI required" >&2
  exit 1
fi

if ! command -v envsubst >/dev/null; then
  echo "envsubst required (gettext package)" >&2
  exit 1
fi

prep_sql() {
  local src="$1"
  local dst
  dst="$(mktemp)"
  envsubst '${BOOTSTRAP_SERVERS} ${KAFKA_API_KEY} ${KAFKA_API_SECRET} ${SPECIFIC_OFFSETS}' < "$src" > "$dst"
  echo "$dst"
}

submit_sql() {
  local name="$1"
  local file="$2"
  echo "Submitting statement: $name"
  confluent flink statement create "$name" \
    --compute-pool "$FLINK_COMPUTE_POOL_ID" \
    --environment "$CC_ENV_ID" \
    --sql-file "$file"
}

create_topics() {
  confluent kafka topic create "$SOURCE_TOPIC" --if-not-exists || true
  confluent kafka topic create "$SINK_V1_TOPIC" --if-not-exists || true
  confluent kafka topic create "$SINK_V2_TOPIC" --if-not-exists || true
}

deploy_v1() {
  create_topics
  local f1 f2 f3
  f1="$(prep_sql "$ASSETS/01_ddl_source.sql")"
  f2="$(prep_sql "$ASSETS/02_ddl_sink_v1.sql")"
  f3="$(prep_sql "$ASSETS/03_dml_v1_aggregate.sql")"
  trap 'rm -f "$f1" "$f2" "$f3"' RETURN
  submit_sql "$STATEMENT_DDL_SOURCE" "$f1"
  submit_sql "$STATEMENT_DDL_SINK_V1" "$f2"
  submit_sql "$STATEMENT_DML_V1" "$f3"
  echo "v1 deployed. Produce events: uv run state-handoff-produce --count 100 --keys 5"
}

deploy_v2() {
  if [[ -z "${SPECIFIC_OFFSETS:-}" ]]; then
    echo "SPECIFIC_OFFSETS is required for v2 deploy." >&2
    echo "Run: SPECIFIC_OFFSETS=\$(./assets/cc-flink/deploy.sh offsets) ./assets/cc-flink/deploy.sh v2" >&2
    exit 1
  fi
  local f4 f5 f6
  f4="$(prep_sql "$ASSETS/04_ddl_snapshot.sql")"
  f5="$(prep_sql "$ASSETS/05_ddl_sink_v2.sql")"
  f6="$(prep_sql "$ASSETS/06_dml_v2_handoff.sql")"
  trap 'rm -f "$f4" "$f5" "$f6"' RETURN
  submit_sql "$STATEMENT_DDL_SNAPSHOT" "$f4"
  submit_sql "$STATEMENT_DDL_SINK_V2" "$f5"
  submit_sql "$STATEMENT_DML_V2" "$f6"
  echo "v2 deployed with SPECIFIC_OFFSETS=$SPECIFIC_OFFSETS"
}

stop_v1() {
  echo "Stopping statement $STATEMENT_DML_V1 (capture latest_offsets after STOPPED)..."
  confluent flink statement stop "$STATEMENT_DML_V1" \
    --environment "$CC_ENV_ID" \
    --compute-pool "$FLINK_COMPUTE_POOL_ID"
  echo "Wait until phase STOPPED, then run: ./assets/cc-flink/deploy.sh offsets"
}

print_offsets() {
  cd "$ROOT"
  uv run state-handoff-capture-offsets --statement "$STATEMENT_DML_V1" --table device_events
}

cmd="${1:-v1}"
case "$cmd" in
  v1) deploy_v1 ;;
  v2) deploy_v2 ;;
  stop-v1) stop_v1 ;;
  offsets) print_offsets ;;
  topics) create_topics ;;
  *)
    echo "Usage: $0 {v1|v2|stop-v1|offsets|topics}" >&2
    exit 1
    ;;
esac
