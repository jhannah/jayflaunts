#!/usr/bin/env bash
# One-time setup: creates the Athena database and external table.
# Edit ATHENA_OUTPUT and REGION below, then: bash setup.sh
set -euo pipefail

# --- Configure these (same values as run_export.sh) ---
ATHENA_OUTPUT="s3://YOUR-BUCKET/athena-results/"
REGION="us-east-1"
# ------------------------------------------------------

run_query() {
  local desc="$1"
  local sql="$2"
  echo "Running: $desc"
  local id
  id=$(aws athena start-query-execution \
    --region "$REGION" \
    --query-string "$sql" \
    --result-configuration "OutputLocation=$ATHENA_OUTPUT" \
    --output text \
    --query 'QueryExecutionId')
  while true; do
    local state
    state=$(aws athena get-query-execution \
      --region             "$REGION" \
      --query-execution-id "$id" \
      --output text \
      --query 'QueryExecution.Status.State')
    case "$state" in
      SUCCEEDED) echo "  OK"; return ;;
      FAILED|CANCELLED)
        aws athena get-query-execution \
          --region             "$REGION" \
          --query-execution-id "$id" \
          --query 'QueryExecution.Status.StateChangeReason' \
          --output text
        exit 1 ;;
      *) sleep 3 ;;
    esac
  done
}

run_query "CREATE SCHEMA" \
  "CREATE SCHEMA IF NOT EXISTS jayflaunts_logs"

run_query "CREATE TABLE" \
  "$(grep -v '^--' "$(dirname "$0")/setup.sql" | tr -s '\n')"

echo ""
echo "Setup complete. Run: bash run_export.sh"
