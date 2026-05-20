-- Source: unified telemetry topic (train + test + inference on one topic).
-- Key: device_id. Value: JSON matching reefer_pm_kafka generator schema.

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
    'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
    'properties.group.id' = 'reefer-pm-flink-features',
    'scan.startup.mode' = 'earliest-offset',
    'value.format' = 'json',
    'value.json.ignore-parse-errors' = 'true'
);
