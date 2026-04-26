# jayflaunts-logs

Consolidates S3 access logs for the **jayflaunts.jays.net** podcast bucket into a
single SQLite database for download analytics (2017 → present).

## What this repo is

The S3 bucket `jayflaunts.jays.net` stores `.mp3` files for Jay's podcast and has
had S3 server access logging enabled since 2017. Each listener request generates one
tiny log file in `s3://jayflaunts.jays.net/logs/`. There are hundreds of thousands
of these files. Most are S3stat housekeeping traffic; the ones we care about are
`REST.GET.OBJECT` on `.mp3` keys with HTTP 200 or 206.

## Files

| File | Purpose |
|------|---------|
| `import_logs.py` | Parses log files → SQLite. Idempotent/incremental. |
| `stats.py` | Query and print download stats from the DB. |
| `downloads.db` | SQLite database (not committed). |
| `logs/` | Local mirror of `s3://jayflaunts.jays.net/logs/` (not committed). |

## Workflow

### 1. Sync log files from S3 (run in chunks — there are hundreds of thousands)

Sync a single month (recommended — each month is ~30k files):

```bash
aws s3 sync s3://jayflaunts.jays.net/logs/ ./logs/ --exclude "*" --include "2018-01-*"
```

Or sync everything (slow, use only when catching up in bulk):

```bash
aws s3 sync s3://jayflaunts.jays.net/logs/ ./logs/
```

As of April 2026, only Oct–Dec 2017 has been pulled down (~80k files).

### 2. Import into SQLite

```bash
python3 import_logs.py
```

Already-processed files are tracked in the `processed_files` table and skipped on
subsequent runs. Safe to re-run after each incremental sync.

### 3. Query stats

```bash
python3 stats.py                  # full report
python3 stats.py --monthly        # downloads per month
python3 stats.py --episodes       # all-time per episode
python3 stats.py --year 2018      # one year detail
python3 stats.py --episode earl4  # history for one episode (partial match)
```

## Database schema

```sql
CREATE TABLE downloads (
    id          INTEGER PRIMARY KEY,
    timestamp   TEXT,      -- ISO 8601 UTC
    remote_ip   TEXT,
    operation   TEXT,      -- always REST.GET.OBJECT
    key         TEXT,      -- e.g. "021.mp3"
    http_status INTEGER,   -- 200 or 206
    bytes_sent  INTEGER,   -- bytes sent in this request (< object_size for range reqs)
    object_size INTEGER,   -- total file size
    referer     TEXT,
    user_agent  TEXT,
    log_file    TEXT       -- source log filename
);

CREATE TABLE processed_files (
    filename     TEXT PRIMARY KEY,
    processed_at TEXT
);
```

## Notes

- HTTP 206 = range/partial request, common from podcast clients. Counted as a download.
- HTTP 200 = full download.
- `bytes_sent` < `object_size` is normal for 206 responses (seeked/skipped).
- The S3 log format has a timestamp in the log file name *and* inside the log lines.
  We use the timestamp inside the line (field 3, bracketed) as it reflects actual
  request time, normalized to UTC ISO 8601.
- Most log files contain only S3stat bucket-listing requests, not real downloads.
  Signal density is low (~567 downloads across 80k log files for late 2017).
