CREATE TABLE mt_transaction_events (
    status STRING,
    id STRING,
    ts_ms BIGINT,
    event_count BIGINT,
    data_collections ARRAY<ROW<data_collection STRING, event_count BIGINT>>
);
