-- Local Docker Kafka (PLAINTEXT). Use this file instead of 01_ddl_telemetry_source.sql
-- when ${BOOTSTRAP_SERVERS} substitution is not available in your SQL client.

DROP TABLE IF EXISTS reefer_telemetry;

CREATE TABLE reefer_telemetry (
    event_id STRING,
    device_id STRING,
    event_time STRING,
    return_air_temp_c DOUBLE,
    supply_air_temp_c DOUBLE,
    compressor_runtime_h DOUBLE,
    door_open_count INT,
    power_draw_kw DOUBLE,
    vibration_rms DOUBLE,
    `meta` ROW<`split` STRING, is_labeled BOOLEAN>,
    `label` ROW<failure_class STRING, horizon_hours INT>,
    event_ts AS TO_TIMESTAMP_LTZ(event_time, 3),
    WATERMARK FOR event_ts AS event_ts - INTERVAL '2' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'reefer.telemetry.v1',
    'properties.bootstrap.servers' = '127.0.0.1:9092',
    'properties.group.id' = 'reefer-pm-flink-features',
    'scan.startup.mode' = 'earliest-offset',
    'value.format' = 'json',
    'value.json.ignore-parse-errors' = 'true'
);
