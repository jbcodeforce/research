-- Kafka sink for perf-testing (Confluent Cloud).

CREATE TABLE IF NOT EXISTS perf_sink (
    id BIGINT,
    event_time STRING,
    value DOUBLE,
    payload STRING
) WITH (
    'connector' = 'kafka',
    'topic' = 'perf-output',
    'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
    'value.format' = 'json',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";'
);
