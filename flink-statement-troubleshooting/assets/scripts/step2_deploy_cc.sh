#!/usr/bin/env bash
# Step 2 — Deploy perf-testing SQL statements to Confluent Cloud for Flink.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/deploy_statements.sh" "$@"
