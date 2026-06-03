-- Snapshot table: reads v1 sink topic as upsert changelog (bootstrap state).
-- Replays from earliest to materialize latest total per device_id in operator state.

CREATE TABLE IF NOT EXISTS agg_snapshot (
    device_id STRING NOT NULL,
    total_amount BIGINT,
    last_event_time TIMESTAMP(3),
    PRIMARY KEY (device_id) NOT ENFORCED
) WITH (
    'connector' = 'kafka',
    'topic' = 'agg-state-v1',
    'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
    'changelog.mode' = 'upsert',
    'kafka.cleanup-policy' = 'compact',
    'scan.startup.mode' = 'earliest-offset',
    'key.format' = 'json',
    'value.format' = 'json',
    'value.fields-include' = 'all',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";'
);
