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
INSERT INTO `streams-output`
WITH parsed AS (
  SELECT 
   key AS key,
   CAST(val AS STRING) AS json
  from `streams-input`  /*+ OPTIONS('scan.startup.mode'='specific-offsets', 'scan.startup.specific-offsets' = 'partition:1,offset:1;partition:2,offset:1;partition:4,offset:1;partition:5,offset:2;') */ 
)
select 
  key,
  CAST(CONCAT('"device_id":' , JSON_VALUE(json, '$.device_id'), '"value":',UPPER(JSON_VALUE(json, '$.value'))) AS BYTES)
FROM parsed