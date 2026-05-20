#!/usr/bin/env bash
# Stop the streams_output CSAS persistent query (does not drop streams/topics).
#
# Usage: same env vars as deploy.sh — ./ksqldb/scripts/terminate.sh

set -euo pipefail

: "${KSQLDB_ENDPOINT:?Set KSQLDB_ENDPOINT}"
: "${KSQLDB_API_KEY:?Set KSQLDB_API_KEY}"
: "${KSQLDB_API_SECRET:?Set KSQLDB_API_SECRET}"

if ! command -v ksql >/dev/null 2>&1; then
  echo "ksql CLI not found on PATH." >&2
  exit 1
fi

ksql \
  -u "${KSQLDB_API_KEY}" \
  -p "${KSQLDB_API_SECRET}" \
  "${KSQLDB_ENDPOINT}" \
  <<'EOF'
SHOW QUERIES;
-- Replace CSAS_STREAMS_OUTPUT_0 with the id from SHOW QUERIES if different:
TERMINATE CSAS_STREAMS_OUTPUT_0;
EOF
