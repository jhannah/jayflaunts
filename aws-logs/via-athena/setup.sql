-- Athena only runs ONE statement per execution.
-- Use setup.sh to run both via CLI, or paste them one at a time in the console.

-- Statement 1 of 2:
-- CREATE SCHEMA IF NOT EXISTS jayflaunts_logs

-- Statement 2 of 2 (the table — run this one after the schema exists):
CREATE TABLE IF NOT EXISTS jayflaunts_logs.access_logs (
  bucketowner     varchar,
  bucket          varchar,
  requestdatetime varchar,
  remoteip        varchar,
  requester       varchar,
  requestid       varchar,
  operation       varchar,
  key             varchar,
  requesturi      varchar,
  httpstatus      varchar,
  errorcode       varchar,
  bytessent       varchar,
  objectsize      varchar,
  totaltime       varchar,
  turnaroundtime  varchar,
  referrer        varchar,
  useragent       varchar,
  versionid       varchar,
  hostid          varchar,
  sigv            varchar,
  ciphersuite     varchar,
  authtype        varchar,
  endpoint        varchar,
  tlsversion      varchar
)
WITH (
  external_location = 's3://jayflaunts.jays.net/logs/',
  format            = 'TEXTFILE',
  serde_lib         = 'org.apache.hadoop.hive.serde2.RegexSerDe',
  serde_properties  = '{"input.regex": "([^ ]*) ([^ ]*) \\[(.*?)\\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) (\"[^\"]*\"|-) (-|[0-9]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) (\"[^\"]*\"|-) (\"[^\"]*\"|-) ([^ ]*)(?: ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*))?.*$"}'
)
