DROP TABLE IF EXISTS reefer_features;

CREATE TABLE reefer_features (
    device_id STRING,
    window_start TIMESTAMP_LTZ(3),
    window_end TIMESTAMP_LTZ(3),
    meta_split STRING,
    failure_class STRING,
    avg_return_air_temp_c DOUBLE,
    std_return_air_temp_c DOUBLE,
    delta_supply_return_c DOUBLE,
    slope_return_air_per_min DOUBLE,
    avg_power_draw_kw DOUBLE,
    max_door_open_count DOUBLE,
    avg_vibration_rms DOUBLE
) WITH (
    'connector' = 'kafka',
    'topic' = 'reefer.features.v1',
    'properties.bootstrap.servers' = '127.0.0.1:9092',
    'value.format' = 'json',
    'sink.partitioner' = 'default'
);
