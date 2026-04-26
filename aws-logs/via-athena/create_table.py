#!/usr/bin/env python3
"""
Creates the Athena/Glue table for jayflaunts S3 access logs.
Bypasses Athena DDL (which varies by engine version) and writes
the table definition directly to the AWS Glue Data Catalog.

Usage: python3 create_table.py [--region us-east-1]
"""

import argparse
import boto3
from botocore.exceptions import ClientError

DATABASE = "jayflaunts_logs"
TABLE    = "access_logs"
LOCATION = "s3://jayflaunts.jays.net/logs/"

# The Java regex the RegexSerDe applies to each log line.
# Groups map to columns in declaration order.
REGEX = (
    r'([^ ]*) ([^ ]*) \[(.*?)\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) '
    r'("[^"]*"|-) (-|[0-9]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) '
    r'("[^"]*"|-) ("[^"]*"|-) ([^ ]*)'
    r'(?: ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*))?.*$'
)

COLUMNS = [
    "bucketowner", "bucket", "requestdatetime", "remoteip", "requester",
    "requestid", "operation", "key", "requesturi", "httpstatus", "errorcode",
    "bytessent", "objectsize", "totaltime", "turnaroundtime", "referrer",
    "useragent", "versionid", "hostid", "sigv", "ciphersuite", "authtype",
    "endpoint", "tlsversion",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="us-east-1")
    args = ap.parse_args()

    glue = boto3.client("glue", region_name=args.region)

    # Create database (idempotent)
    try:
        glue.create_database(DatabaseInput={"Name": DATABASE})
        print(f"Created database: {DATABASE}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "AlreadyExistsException":
            print(f"Database already exists: {DATABASE}")
        else:
            raise

    # Drop existing table so we can recreate cleanly
    try:
        glue.delete_table(DatabaseName=DATABASE, Name=TABLE)
        print(f"Dropped existing table: {TABLE}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "EntityNotFoundException":
            raise

    glue.create_table(
        DatabaseName=DATABASE,
        TableInput={
            "Name": TABLE,
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {"EXTERNAL": "TRUE"},
            "StorageDescriptor": {
                "Columns": [{"Name": c, "Type": "string"} for c in COLUMNS],
                "Location": LOCATION,
                "InputFormat":  "org.apache.hadoop.mapred.TextInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                "Compressed": False,
                "SerdeInfo": {
                    "SerializationLibrary": "org.apache.hadoop.hive.serde2.RegexSerDe",
                    "Parameters": {"input.regex": REGEX},
                },
            },
        },
    )
    print(f"Created table: {DATABASE}.{TABLE}")
    print(f"Location: {LOCATION}")
    print(f"\nRun export.sql in the Athena Query Editor to extract downloads.")


if __name__ == "__main__":
    main()
