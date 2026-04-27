#!/usr/bin/env python3
"""
Query summary stats from the jayflaunts podcast download database.
Run with no args for the full report, or pass a flag to narrow it:

  python3 stats.py                  # full report
  python3 stats.py --monthly        # downloads per month
  python3 stats.py --episodes       # all-time per episode
  python3 stats.py --year 2018      # one year breakdown
  python3 stats.py --episode 021    # history for one episode (partial match)
  python3 stats.py --geo            # downloads by country
  python3 stats.py --geo-detail     # downloads by country / subdivision / city + lat/lon
  python3 stats.py --country Canada # monthly breakdown for one country
"""

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "downloads.db"


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def monthly(conn, year=None):
    where = f"WHERE strftime('%Y', timestamp) = '{year}'" if year else ""
    rows = conn.execute(f"""
        SELECT strftime('%Y-%m', timestamp) AS month,
               COUNT(*)                    AS downloads
        FROM   downloads
        {where}
        GROUP  BY month
        ORDER  BY month
    """).fetchall()
    print(f"\n{'Month':<10}  {'Downloads':>10}")
    print("-" * 23)
    for r in rows:
        print(f"{r['month']:<10}  {r['downloads']:>10,}")
    total = sum(r['downloads'] for r in rows)
    print("-" * 23)
    print(f"{'TOTAL':<10}  {total:>10,}")


def episodes(conn, year=None):
    where = f"WHERE strftime('%Y', timestamp) = '{year}'" if year else ""
    rows = conn.execute(f"""
        SELECT key,
               COUNT(*)                          AS downloads,
               MIN(strftime('%Y-%m', timestamp)) AS first_seen,
               MAX(strftime('%Y-%m', timestamp)) AS last_seen
        FROM   downloads
        {where}
        GROUP  BY key
        ORDER  BY downloads DESC
    """).fetchall()
    print(f"\n{'Episode':<35}  {'Downloads':>10}  {'First':>7}  {'Last':>7}")
    print("-" * 65)
    for r in rows:
        print(f"{r['key']:<35}  {r['downloads']:>10,}  {r['first_seen']:>7}  {r['last_seen']:>7}")


def episode_history(conn, name):
    rows = conn.execute("""
        SELECT strftime('%Y-%m', timestamp) AS month,
               COUNT(*)                    AS downloads
        FROM   downloads
        WHERE  key LIKE ?
        GROUP  BY month
        ORDER  BY month
    """, (f"%{name}%",)).fetchall()
    if not rows:
        print(f"No rows matching '{name}'")
        return
    matched_keys = conn.execute(
        "SELECT DISTINCT key FROM downloads WHERE key LIKE ?", (f"%{name}%",)
    ).fetchall()
    print(f"\nMatching episodes: {', '.join(r['key'] for r in matched_keys)}")
    print(f"\n{'Month':<10}  {'Downloads':>10}")
    print("-" * 23)
    for r in rows:
        print(f"{r['month']:<10}  {r['downloads']:>10,}")
    print(f"{'TOTAL':<10}  {sum(r['downloads'] for r in rows):>10,}")


def geo_report(conn):
    try:
        rows = conn.execute("""
            SELECT COALESCE(g.country, '(unknown)') AS country,
                   COUNT(*)                         AS downloads
            FROM   downloads d
            LEFT   JOIN geo g ON d.remote_ip = g.remote_ip
            GROUP  BY country
            ORDER  BY downloads DESC
        """).fetchall()
    except Exception:
        print("No geo data found. Run: python3 geolocate.py")
        return

    geo_total = conn.execute("SELECT COUNT(*) FROM geo WHERE country IS NOT NULL").fetchone()[0]
    ip_total  = conn.execute("SELECT COUNT(DISTINCT remote_ip) FROM downloads").fetchone()[0]

    print(f"\n{'Country':<35}  {'Downloads':>10}")
    print("-" * 48)
    for r in rows:
        print(f"{r['country']:<35}  {r['downloads']:>10,}")
    print("-" * 48)
    print(f"{'TOTAL':<35}  {sum(r['downloads'] for r in rows):>10,}")
    print(f"\nIPs geolocated: {geo_total:,} of {ip_total:,} unique  "
          f"(run geolocate.py to fill gaps)")


def geo_report_detailed(conn):
    try:
        rows = conn.execute("""
            SELECT COALESCE(g.country,     '(unknown)') AS country,
                   COALESCE(g.subdivision, '')          AS subdivision,
                   COALESCE(g.city,        '')          AS city,
                   COUNT(*)                             AS downloads
            FROM   downloads d
            LEFT   JOIN geo g ON d.remote_ip = g.remote_ip
            GROUP  BY country, subdivision, city
            ORDER  BY downloads DESC
        """).fetchall()
    except Exception:
        print("No geo data found. Run: python3 geolocate.py")
        return

    print(f"\n{'Country':<25}  {'Subdivision':<20}  {'City':<20}  {'Downloads':>10}")
    print("-" * 81)
    for r in rows:
        print(f"{r['country']:<25}  {r['subdivision']:<20}  {r['city']:<20}  {r['downloads']:>10,}")
    print("-" * 81)
    print(f"{'TOTAL':<69}  {sum(r['downloads'] for r in rows):>10,}")


def country_history(conn, name):
    try:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', d.timestamp) AS month,
                   COUNT(*)                       AS downloads
            FROM   downloads d
            LEFT   JOIN geo g ON d.remote_ip = g.remote_ip
            WHERE  g.country LIKE ?
            GROUP  BY month
            ORDER  BY month
        """, (f"%{name}%",)).fetchall()
    except Exception:
        print("No geo data found. Run: python3 geolocate.py")
        return

    if not rows:
        print(f"No downloads found for country matching '{name}'")
        return

    matched = conn.execute(
        "SELECT DISTINCT country FROM geo WHERE country LIKE ?", (f"%{name}%",)
    ).fetchall()
    print(f"\nMatching countries: {', '.join(r['country'] for r in matched)}")
    print(f"\n{'Month':<10}  {'Downloads':>10}")
    print("-" * 23)
    for r in rows:
        print(f"{r['month']:<10}  {r['downloads']:>10,}")
    print(f"{'TOTAL':<10}  {sum(r['downloads'] for r in rows):>10,}")


def full_report(conn):
    total = conn.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
    date_range = conn.execute(
        "SELECT MIN(timestamp), MAX(timestamp) FROM downloads"
    ).fetchone()
    months_processed = conn.execute(
        "SELECT COUNT(*) FROM processed_months"
    ).fetchone()[0]

    print(f"\n=== jayflaunts podcast download stats ===")
    print(f"Months processed    : {months_processed:,}")
    print(f"Total download rows : {total:,}")
    print(f"Date range          : {date_range[0][:10]}  →  {date_range[1][:10]}")

    monthly(conn)
    print()
    episodes(conn)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--monthly",  action="store_true")
    parser.add_argument("--episodes", action="store_true")
    parser.add_argument("--year",     metavar="YYYY")
    parser.add_argument("--episode",  metavar="NAME")
    parser.add_argument("--geo",        action="store_true")
    parser.add_argument("--geo-detail", action="store_true")
    parser.add_argument("--country",    metavar="NAME")
    args = parser.parse_args()

    conn = connect()

    if args.episode:
        episode_history(conn, args.episode)
    elif args.country:
        country_history(conn, args.country)
    elif args.geo_detail:
        geo_report_detailed(conn)
    elif args.geo:
        geo_report(conn)
    elif args.monthly or args.year:
        monthly(conn, year=args.year)
        if args.year:
            print()
            episodes(conn, year=args.year)
    elif args.episodes:
        episodes(conn)
    else:
        full_report(conn)

    conn.close()


if __name__ == "__main__":
    main()
