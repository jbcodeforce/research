-- Continue reading `streams-input` in Flink after stopping Kafka Streams.
-- Message format (from `streams-demo-producer`): JSON value
--   {"device_id":"device-1","value":"hello_1"}
-- Keys: set `scan.startup.specific-offsets` from committed offsets of group
--   `kstream-eos-demo` on topic `streams-input` (see ../README.md).
--
-- Flink 2.2+ Kafka connector: specific-offsets use semicolon-separated
--   partition:0,offset:<n>;partition:1,offset:<m>
-- (see https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/table/kafka/)
-- Placeholder below assumes partition 0 only; replace <NEXT_OFFSET> with the
-- committed offset for that partition (the next record to read).

-- SET is optional depending on your SQL client session
-- 'table.sql-dialect' = 'default';

CREATE TABLE streams_input (
  device_id STRING,
  `value` STRING
) WITH (
  'connector' = 'kafka',
  'topic' = 'streams-input',
  'properties.bootstrap.servers' = 'localhost:9092',
  'properties.group.id' = 'flink-handoff-demo',
  'format' = 'json',
  'json.fail-on-missing-field' = 'false',
  'json.ignore-parse-errors' = 'false',
  'scan.startup.mode' = 'specific-offsets',
  'scan.startup.specific-offsets' = 'partition:0,offset:<NEXT_OFFSET>'
);

-- Mirror the kstream transform (processed: + UPPER) for illustration
CREATE TABLE print_upper (
  device_id STRING,
  out_val STRING
) WITH (
  'connector' = 'print'
);

INSERT INTO print_upper
SELECT
  device_id,
  CONCAT('processed:', UPPER(`value`)) AS out_val
FROM streams_input;
