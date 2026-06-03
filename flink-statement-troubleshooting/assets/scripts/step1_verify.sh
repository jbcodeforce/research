#!/usr/bin/env bash
# Step 1 — Verify flink-triage tooling offline (no Flink cluster; Confluent Cloud not required).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/run_uat.sh" "$@"
