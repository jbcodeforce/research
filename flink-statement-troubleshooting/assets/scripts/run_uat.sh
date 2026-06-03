#!/usr/bin/env bash
# UAT: dry-run triage (no CC credentials) + optional live triage when .env is configured.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> uv sync"
uv sync --extra dev

echo "==> pytest"
uv run pytest tests/ -v

echo "==> flink-triage tools list"
uv run flink-triage tools list

echo "==> dry-run triage"
uv run flink-triage run \
  --statement perf-dml-passthrough \
  --pool lfcp-example \
  --dry-run \
  --output examples/sample_triage_report.md

if [[ -f .env ]] && grep -q 'FLINK_API_KEY=.\+' .env 2>/dev/null; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  if [[ -n "${FLINK_COMPUTE_POOL_ID:-}" ]]; then
    echo "==> live triage (CC credentials detected)"
    uv run flink-triage run \
      --statement "${STATEMENT_DML_PASSTHROUGH:-perf-dml-passthrough}" \
      --pool "$FLINK_COMPUTE_POOL_ID" \
      --output examples/live_report.md || echo "Live triage failed — check credentials and deployed statement"
  fi
else
  echo "Skipping live triage (no .env with FLINK_API_KEY)"
fi

echo "UAT complete."
