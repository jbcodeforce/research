-- Kafka source for perf-testing (Confluent Cloud).
-- Substitute bootstrap and SASL credentials before submit.
-- Source: flink-studies/e2e-demos/perf-testing/flink-jobs/flink-sql/ddl_source.sql

CREATE TABLE IF NOT EXISTS perf_source (
    id BIGINT,
    event_time STRING,
    value DOUBLE,
    payload STRING
) WITH (
    'connector' = 'kafka',
    'topic' = 'perf-input',
    'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
    'scan.startup.mode' = 'earliest-offset',
    'value.format' = 'json',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";'
);
