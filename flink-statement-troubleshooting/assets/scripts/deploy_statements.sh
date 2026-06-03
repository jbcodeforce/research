#!/usr/bin/env bash
# Submit perf-testing Flink SQL statements to Confluent Cloud.
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

STATEMENT_DDL_SOURCE="${STATEMENT_DDL_SOURCE:-perf-ddl-source}"
STATEMENT_DDL_SINK="${STATEMENT_DDL_SINK:-perf-ddl-sink}"
STATEMENT_DML_PASSTHROUGH="${STATEMENT_DML_PASSTHROUGH:-perf-dml-passthrough}"

submit_sql() {
  local name="$1"
  local file="$2"
  echo "Submitting statement: $name from $file"
  confluent flink statement create "$name" \
    --compute-pool "$FLINK_COMPUTE_POOL_ID" \
    --environment "$CC_ENV_ID" \
    --sql-file "$file"
}

# Substitute env vars into temp SQL files
prep_sql() {
  local src="$1"
  local dst
  dst="$(mktemp)"
  envsubst '${BOOTSTRAP_SERVERS} ${KAFKA_API_KEY} ${KAFKA_API_SECRET}' < "$src" > "$dst"
  echo "$dst"
}

if ! command -v confluent >/dev/null; then
  echo "confluent CLI required" >&2
  exit 1
fi

if ! command -v envsubst >/dev/null; then
  echo "envsubst required (gettext package)" >&2
  exit 1
fi

: "${BOOTSTRAP_SERVERS:?Set BOOTSTRAP_SERVERS in .env}"
: "${KAFKA_API_KEY:?Set KAFKA_API_KEY in .env}"
: "${KAFKA_API_SECRET:?Set KAFKA_API_SECRET in .env}"

f1="$(prep_sql "$ASSETS/01_ddl_perf_source.sql")"
f2="$(prep_sql "$ASSETS/02_ddl_perf_sink.sql")"
f3="$(prep_sql "$ASSETS/03_dml_passthrough.sql")"

trap 'rm -f "$f1" "$f2" "$f3"' EXIT

submit_sql "$STATEMENT_DDL_SOURCE" "$f1"
submit_sql "$STATEMENT_DDL_SINK" "$f2"
submit_sql "$STATEMENT_DML_PASSTHROUGH" "$f3"

echo "Deployed: $STATEMENT_DDL_SOURCE, $STATEMENT_DDL_SINK, $STATEMENT_DML_PASSTHROUGH"
echo "Run triage: uv run flink-triage run -s $STATEMENT_DML_PASSTHROUGH -p $FLINK_COMPUTE_POOL_ID"
