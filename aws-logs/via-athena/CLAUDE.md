# via-athena

Faster alternative to the local sync workflow in the parent directory.
Instead of downloading 15M log files, Athena queries them directly in S3
and returns only the ~50k–100k rows that are actual podcast downloads.
You download one small CSV; the local sync never happens.

## Why

The `aws-logs/` workflow requires syncing ~30k files per month, one month
at a time, before importing. With 15M total log files across 8.5 years
that is impractical. Athena scans all files in parallel on AWS infrastructure
and returns only the signal rows.

## Prerequisites

- AWS CLI configured with credentials that have:
  - `s3:GetObject` + `s3:ListBucket` on `s3://jayflaunts.jays.net/logs/`
  - `s3:PutObject` on your Athena output bucket
  - `athena:StartQueryExecution`, `athena:GetQueryExecution`, `athena:GetQueryResults`
- An S3 bucket (or prefix) for Athena to write results to

## One-time setup

Run `setup.sql` in the Athena console (Query Editor) or via CLI:

```bash
aws athena start-query-execution \
  --query-string "$(cat setup.sql)" \
  --result-configuration OutputLocation=s3://YOUR-BUCKET/athena-setup/
```

This creates the `jayflaunts_logs` database and `access_logs` external table
pointing at `s3://jayflaunts.jays.net/logs/`. Run it once; the table is permanent.

## Workflow

### 1. Edit run_export.sh

Set `ATHENA_OUTPUT` to your S3 output bucket and `REGION` to match your bucket.

### 2. Run the export

```bash
bash run_export.sh
```

Starts the Athena query, polls until done (typically 1–5 minutes for the full
8.5-year history), then downloads the result as `downloads.csv` here.

### 3. Import into SQLite

```bash
python3 import_csv.py
```

Replaces all rows in `../downloads.db` (the same database `stats.py` uses)
and repopulates `processed_months` from the actual timestamps in the data.

### 4. Query stats

```bash
python3 ../stats.py
python3 ../stats.py --monthly
python3 ../stats.py --episodes
python3 ../stats.py --year 2018
python3 ../stats.py --episode earl4
```

## Files

| File | Purpose |
|------|---------|
| `setup.sql` | Create Athena DB + external table (run once) |
| `export.sql` | Extraction query used by run_export.sh |
| `run_export.sh` | Run the query and download results CSV |
| `import_csv.py` | CSV → `../downloads.db` |
| `downloads.csv` | Athena output (not committed, produced by run_export.sh) |

## Cost

Athena charges ~$5 per TB scanned. S3 access log files are tiny (< 1 KB each).
15M files × ~500 bytes ≈ 7.5 GB → roughly **$0.04** for a full history scan.

## Notes

- `import_csv.py` does a full replace of the downloads table each run.
  Re-run it whenever you want to refresh with a new Athena export.
- The parent workflow (`import_logs.py`) and this one share `../downloads.db`.
  Using one will overwrite the other's data. Athena covers all years, so
  after a successful Athena import there is no reason to use the local workflow.
- `setup.sql` uses `CREATE ... IF NOT EXISTS` so it is safe to re-run.
