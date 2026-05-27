DROP TABLE IF EXISTS transaction_events;

CREATE TABLE transaction_events (
    status STRING,
    id STRING,
    ts_ms BIGINT,
    event_count BIGINT,
    data_collections ARRAY<ROW<data_collection STRING, event_count BIGINT>>
) WITH (
    'connector' = 'kafka',
    'topic' = 'mt.transaction',
    'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
    'properties.group.id' = 'mt-spanout-tx',
    'scan.startup.mode' = 'earliest-offset',
    'value.format' = 'json',
    'value.json.ignore-parse-errors' = 'true'
);
