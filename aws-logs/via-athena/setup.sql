-- Run once in the Athena console (or via AWS CLI) before anything else.
-- Replaces the need to sync log files locally — Athena reads directly from S3.

CREATE DATABASE IF NOT EXISTS jayflaunts_logs;

CREATE EXTERNAL TABLE IF NOT EXISTS jayflaunts_logs.access_logs (
  bucketowner    STRING,
  bucket         STRING,
  requestdatetime STRING,
  remoteip       STRING,
  requester      STRING,
  requestid      STRING,
  operation      STRING,
  key            STRING,
  requesturi     STRING,
  httpstatus     STRING,
  errorcode      STRING,
  bytessent      STRING,
  objectsize     STRING,
  totaltime      STRING,
  turnaroundtime STRING,
  referrer       STRING,
  useragent      STRING,
  versionid      STRING,
  hostid         STRING,
  sigv           STRING,
  ciphersuite    STRING,
  authtype       STRING,
  endpoint       STRING,
  tlsversion     STRING
)
ROW FORMAT REGEX
'([^ ]*) ([^ ]*) \\[(.*?)\\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) (\"[^\"]*\"|-) (-|[0-9]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) (\"[^\"]*\"|-) (\"[^\"]*\"|-) ([^ ]*)(?: ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*))?.*$'
LOCATION 's3://jayflaunts.jays.net/logs/';
