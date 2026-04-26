-- Extracts all real podcast downloads from the full S3 access log history.
-- Run via run_export.sh (not directly) — it handles execution and CSV download.
--
-- Filters: REST.GET.OBJECT on .mp3 keys, HTTP 200 or 206 only.
-- referrer/useragent: strips the surrounding quotes that S3 logs embed.
-- bytes_sent/object_size: TRY_CAST handles the "-" placeholder S3 uses for nulls.

SELECT
    requestdatetime,
    remoteip,
    operation,
    key,
    httpstatus,
    TRY_CAST(bytessent   AS BIGINT)                          AS bytes_sent,
    TRY_CAST(objectsize  AS BIGINT)                          AS object_size,
    NULLIF(regexp_extract(referrer,  '^"(.*)"$', 1), '')     AS referrer,
    NULLIF(regexp_extract(useragent, '^"(.*)"$', 1), '')     AS useragent,
    "$path"                                                  AS log_file
FROM jayflaunts_logs.access_logs
WHERE operation  = 'REST.GET.OBJECT'
  AND key        LIKE '%.mp3'
  AND httpstatus IN ('200', '206')
ORDER BY requestdatetime
