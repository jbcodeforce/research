-- Source: append JSON events for keyed aggregation handoff study.
-- Topic: device-events (create before deploy).

CREATE TABLE IF NOT EXISTS device_events (
    device_id STRING,
    amount BIGINT,
    event_time TIMESTAMP(3),
    seq BIGINT
) WITH (
    'connector' = 'kafka',
    'topic' = 'device-events',
    'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
    'scan.startup.mode' = 'earliest-offset',
    'value.format' = 'json',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";'
);
