#!/usr/bin/env python3
"""
Geo-locate all remote_ip values in downloads.db using a local MaxMind GeoLite2
database. Incremental — skips IPs already in the geo table.

Setup:
  1. Register free at https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
  2. Download GeoLite2-City.mmdb and place it alongside this script
  3. pip install geoip2

Usage:
  python3 geolocate.py
  python3 geolocate.py --mmdb /path/to/GeoLite2-City.mmdb
  python3 geolocate.py --db /path/to/downloads.db
"""

import argparse
import sqlite3
from pathlib import Path

HERE        = Path(__file__).parent
DEFAULT_DB  = HERE / "downloads.db"
DEFAULT_MMDB = HERE / "GeoLite2-City.mmdb"


def init_geo_table(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS geo (
            remote_ip   TEXT PRIMARY KEY,
            country     TEXT,
            subdivision TEXT,
            city        TEXT,
            latitude    REAL,
            longitude   REAL
        );
    """)
    conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db",   type=Path, default=DEFAULT_DB)
    ap.add_argument("--mmdb", type=Path, default=DEFAULT_MMDB)
    args = ap.parse_args()

    if not args.mmdb.exists():
        raise SystemExit(
            f"GeoLite2 database not found: {args.mmdb}\n"
            "Download GeoLite2-City.mmdb free from:\n"
            "  https://dev.maxmind.com/geoip/geolite2-free-geolocation-data"
        )

    try:
        import geoip2.database
        import geoip2.errors
    except ImportError:
        raise SystemExit("Missing dependency: pip install geoip2")

    conn = sqlite3.connect(args.db)
    init_geo_table(conn)

    pending = [
        r[0] for r in conn.execute("""
            SELECT DISTINCT remote_ip FROM downloads
            WHERE  remote_ip IS NOT NULL
              AND  remote_ip NOT IN (SELECT remote_ip FROM geo)
            ORDER  BY remote_ip
        """)
    ]

    print(f"IPs to look up: {len(pending):,}")
    if not pending:
        print("Nothing to do.")
        conn.close()
        return

    rows = []
    unresolved = 0
    with geoip2.database.Reader(args.mmdb) as reader:
        for i, ip in enumerate(pending, 1):
            if i % 1000 == 0:
                print(f"  {i:,} / {len(pending):,} ...")
            try:
                r = reader.city(ip)
                rows.append((
                    ip,
                    r.country.name or None,
                    r.subdivisions.most_specific.name or None,
                    r.city.name or None,
                    r.location.latitude,
                    r.location.longitude,
                ))
            except (geoip2.errors.AddressNotFoundError, ValueError):
                rows.append((ip, None, None, None, None, None))
                unresolved += 1

    conn.executemany(
        "INSERT OR IGNORE INTO geo "
        "(remote_ip, country, subdivision, city, latitude, longitude) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()

    print(f"Looked up  : {len(rows):,} IPs")
    print(f"Unresolved : {unresolved:,}  (private or unknown addresses)")
    print(f"\nRun: python3 stats.py --geo")


if __name__ == "__main__":
    main()
