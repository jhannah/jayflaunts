#!/usr/bin/env python3
"""
Import S3 access logs for jayflaunts.jays.net into SQLite.
Run repeatedly as you sync more log files — already-processed files are skipped.

Usage: python3 import_logs.py
"""

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path(__file__).parent / "logs"
DB_PATH = Path(__file__).parent / "downloads.db"

# S3 server access log format:
# bucket_owner bucket [time] remote_ip requester request_id operation key "request_uri"
# http_status error_code bytes_sent object_size total_time turn_around_time "referer" "user_agent" version_id
S3_LOG_RE = re.compile(
    r'\S+'              # bucket_owner
    r' \S+'             # bucket
    r' \[([^\]]+)\]'    # [time]
    r' (\S+)'           # remote_ip
    r' \S+'             # requester
    r' \S+'             # request_id
    r' (\S+)'           # operation
    r' (\S+)'           # key
    r' "[^"]*"'         # "request_uri"
    r' (\d+)'           # http_status
    r' \S+'             # error_code
    r' (\S+)'           # bytes_sent
    r' (\S+)'           # object_size
    r' \S+'             # total_time
    r' \S+'             # turn_around_time
    r' "([^"]*)"'       # "referer"
    r' "([^"]*)"'       # "user_agent"
)


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

        CREATE TABLE IF NOT EXISTS processed_files (
            filename     TEXT PRIMARY KEY,
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
    return int(s) if s != "-" else None


def process_file(conn, path):
    rows = []
    with open(path, errors="replace") as f:
        for line in f:
            m = S3_LOG_RE.match(line)
            if not m:
                continue
            time_str, remote_ip, operation, key, http_status, bytes_sent, object_size, referer, user_agent = m.groups()

            if not key.endswith(".mp3"):
                continue
            if operation != "REST.GET.OBJECT":
                continue
            if http_status not in ("200", "206"):
                continue

            ts = parse_ts(time_str)
            if not ts:
                continue

            rows.append((
                ts,
                remote_ip,
                operation,
                key,
                int(http_status),
                nullable_int(bytes_sent),
                nullable_int(object_size),
                referer if referer != "-" else None,
                user_agent if user_agent != "-" else None,
                path.name,
            ))

    conn.executemany(
        "INSERT INTO downloads "
        "(timestamp, remote_ip, operation, key, http_status, bytes_sent, object_size, referer, user_agent, log_file) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.execute(
        "INSERT INTO processed_files (filename, processed_at) VALUES (?, ?)",
        (path.name, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return len(rows)


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    already_done = {r[0] for r in conn.execute("SELECT filename FROM processed_files")}
    all_files = sorted(LOGS_DIR.iterdir())
    pending = [f for f in all_files if f.is_file() and f.name not in already_done]

    print(f"Already processed : {len(already_done):,} files")
    print(f"New files to import: {len(pending):,} files")

    total_rows = 0
    for i, path in enumerate(pending, 1):
        total_rows += process_file(conn, path)
        if i % 5000 == 0:
            print(f"  {i:,}/{len(pending):,} files … {total_rows:,} download rows so far")

    db_total = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
    print(f"\nInserted {total_rows:,} new rows. Total in DB: {db_total:,}")

    print("\nQuick breakdown by episode:")
    for row in conn.execute(
        "SELECT key, COUNT(*) AS downloads FROM downloads GROUP BY key ORDER BY downloads DESC LIMIT 20"
    ):
        print(f"  {row[0]:30s}  {row[1]:>6,}")

    conn.close()


if __name__ == "__main__":
    main()
