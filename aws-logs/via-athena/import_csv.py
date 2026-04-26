#!/usr/bin/env python3
"""
Import an Athena-exported download CSV into SQLite.
Run after run_export.sh has produced downloads.csv.

Replaces all rows in ../downloads.db (same DB stats.py uses).
Also repopulates processed_months so stats.py full report works correctly.

Usage:
  python3 import_csv.py                   # default paths
  python3 import_csv.py --csv foo.csv     # different CSV
  python3 import_csv.py --db /path/to.db  # different DB
"""

import argparse
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT_CSV = HERE / "downloads.csv"
DEFAULT_DB  = HERE.parent / "downloads.db"


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS downloads (
            id           INTEGER PRIMARY KEY,
            timestamp    TEXT NOT NULL,
            remote_ip    TEXT,
            operation    TEXT,
            key          TEXT,
            http_status  INTEGER,
            bytes_sent   INTEGER,
            object_size  INTEGER,
            referer      TEXT,
            user_agent   TEXT,
            log_file     TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_timestamp ON downloads(timestamp);
        CREATE INDEX IF NOT EXISTS idx_key       ON downloads(key);

        CREATE TABLE IF NOT EXISTS processed_months (
            month        TEXT PRIMARY KEY,
            processed_at TEXT NOT NULL
        );
    """)
    conn.commit()


def parse_ts(s):
    try:
        return datetime.strptime(s, "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def nullable_int(s):
    return int(s) if s not in ("", "-", None) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--db",  type=Path, default=DEFAULT_DB)
    args = ap.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}\nRun run_export.sh first.")

    conn = sqlite3.connect(args.db)
    init_db(conn)

    print(f"Replacing downloads in {args.db} ...")
    conn.execute("DELETE FROM downloads")
    conn.execute("DELETE FROM processed_months")

    rows = []
    skipped = 0
    with open(args.csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts = parse_ts(row["requestdatetime"])
            if not ts:
                skipped += 1
                continue
            rows.append((
                ts,
                row["remoteip"]   or None,
                row["operation"],
                row["key"],
                int(row["httpstatus"]),
                nullable_int(row["bytes_sent"]),
                nullable_int(row["object_size"]),
                row["referrer"]   or None,
                row["useragent"]  or None,
                row["log_file"]   or None,
            ))

    conn.executemany(
        "INSERT INTO downloads "
        "(timestamp, remote_ip, operation, key, http_status, bytes_sent, object_size, referer, user_agent, log_file) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )

    now = datetime.now(timezone.utc).isoformat()
    months = conn.execute(
        "SELECT DISTINCT strftime('%Y-%m', timestamp) FROM downloads ORDER BY 1"
    ).fetchall()
    conn.executemany(
        "INSERT OR IGNORE INTO processed_months (month, processed_at) VALUES (?, ?)",
        [(r[0], now) for r in months],
    )

    conn.commit()
    conn.close()

    print(f"Imported  : {len(rows):,} rows")
    print(f"Skipped   : {skipped:,} unparseable timestamps")
    print(f"Months    : {len(months):,}")
    print(f"Database  : {args.db}")
    print(f"\nRun stats: python3 {HERE.parent / 'stats.py'}")


if __name__ == "__main__":
    main()
