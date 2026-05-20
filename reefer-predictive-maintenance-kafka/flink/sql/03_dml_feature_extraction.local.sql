-- Local variant: 10-second tumbling windows (matches .env WINDOW_SECONDS=10).

SET 'execution.runtime-mode' = 'streaming';

INSERT INTO reefer_features
SELECT
    t.device_id,
    window_start,
    window_end,
    LAST_VALUE(`meta`.`split`) AS meta_split,
    LAST_VALUE(`label`.failure_class) AS failure_class,
    AVG(return_air_temp_c) AS avg_return_air_temp_c,
    STDDEV_POP(return_air_temp_c) AS std_return_air_temp_c,
    AVG(supply_air_temp_c - return_air_temp_c) AS delta_supply_return_c,
    CASE
        WHEN TIMESTAMPDIFF(SECOND, MIN(event_ts), MAX(event_ts)) > 0
        THEN (
            MAX(return_air_temp_c) - MIN(return_air_temp_c)
        ) * 60.0 / CAST(TIMESTAMPDIFF(SECOND, MIN(event_ts), MAX(event_ts)) AS DOUBLE)
        ELSE 0
    END AS slope_return_air_per_min,
    AVG(power_draw_kw) AS avg_power_draw_kw,
    CAST(MAX(door_open_count) AS DOUBLE) AS max_door_open_count,
    AVG(vibration_rms) AS avg_vibration_rms
FROM reefer_telemetry AS t,
TABLE(
    TUMBLE(TABLE t, DESCRIPTOR(event_ts), INTERVAL '10' SECOND)
) AS w
GROUP BY t.device_id, window_start, window_end;
