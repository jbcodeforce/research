-- Persistent query: same transform as research.kstream.StreamsPipelineApp
--   - JSON object with non-null $.value → uppercase value only, re-serialize JSON
--   - else → processed: + UCASE(full payload)  (null payload → [null])
--
-- Sink topic `streams-output` (String key, String value).

CREATE STREAM IF NOT EXISTS streams_output
WITH (
  KAFKA_TOPIC='streams-output',
  KEY_FORMAT='KAFKA',
  VALUE_FORMAT='KAFKA'
) AS
SELECT
  key,
  CASE
    WHEN msg IS NULL THEN '[null]'
    WHEN TRIM(msg) NOT LIKE '{%' THEN CONCAT('processed:', UCASE(msg))
    WHEN EXTRACTJSONFIELD(msg, '$.value') IS NULL THEN CONCAT('processed:', UCASE(msg))
    ELSE AS_JSON(
      STRUCT(
        device_id := EXTRACTJSONFIELD(msg, '$.device_id'),
        value := UCASE(EXTRACTJSONFIELD(msg, '$.value'))
      )
    )
  END AS msg
FROM streams_input
EMIT CHANGES;
