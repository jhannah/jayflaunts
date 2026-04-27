#!/usr/bin/env bash
# Runs the Athena export query and downloads the result CSV.
# Edit the two variables below, then: bash run_export.sh
set -euo pipefail

# --- Configure these ---
ATHENA_OUTPUT="s3://jayflaunts.jays.net/athena-results/"   # must end with /
REGION="us-east-1"
# -----------------------

HERE="$(cd "$(dirname "$0")" && pwd)"
DATABASE="jayflaunts_logs"

echo "Starting Athena query..."
EXECUTION_ID=$(aws athena start-query-execution \
  --region          "$REGION" \
  --query-string    "$(cat "$HERE/export.sql")" \
  --query-execution-context "Database=$DATABASE" \
  --result-configuration "OutputLocation=$ATHENA_OUTPUT" \
  --output text \
  --query 'QueryExecutionId')

echo "Execution ID: $EXECUTION_ID"
echo "Waiting for completion..."

while true; do
  STATE=$(aws athena get-query-execution \
    --region              "$REGION" \
    --query-execution-id  "$EXECUTION_ID" \
    --output text \
    --query 'QueryExecution.Status.State')
  echo "  $STATE"
  case "$STATE" in
    SUCCEEDED) break ;;
    FAILED|CANCELLED)
      aws athena get-query-execution \
        --region             "$REGION" \
        --query-execution-id "$EXECUTION_ID" \
        --query 'QueryExecution.Status.StateChangeReason' \
        --output text
      exit 1 ;;
    *) sleep 5 ;;
  esac
done

echo "Downloading results..."
aws s3 cp "${ATHENA_OUTPUT}${EXECUTION_ID}.csv" "$HERE/downloads.csv"
echo ""
echo "Done. Run: python3 $HERE/import_csv.py"
